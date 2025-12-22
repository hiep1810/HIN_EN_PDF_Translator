from typing import List, Tuple, Dict, Optional, Any
import fitz, os, zipfile, statistics
from .utils import Span, pick_redact_fill_for_color, insert_text_fit, _dominant_script
from .constants import _DEV
from .textlayer import extract_blocks_from_textlayer, extract_lines_from_textlayer, extract_spans_from_textlayer, derive_line_styles_from_spans, derive_block_styles_from_spans, transfer_style_from_original, translate_text, batch_translate_text
from .overlay import overlay_choose_fontfile_for_text, overlay_draw_text_as_image, overlay_transform_rect, dominant_text_fill_for_rect
from .hybrid import extract_blocks_with_segments, is_table_like, build_columns, extract_blocks_from_layout
from .font_matcher import FontMatcher

def erase_original_text(out_doc: fitz.Document, spans: List[Span], mode: str, erase_mode: str, _unused_fill):
    """
    Dynamic per-span fill:
      - if span text color is light -> redact black
      - else -> redact white
    """
    if erase_mode not in ("mask", "redact"):
        return

    spans_by_page: Dict[int, List[Span]] = {}
    for sp in spans:
        spans_by_page.setdefault(sp.page, []).append(sp)

    for pno, sps in spans_by_page.items():
        page = out_doc[pno]
        if erase_mode == "mask":
            for sp in sps:
                pad = max(1.0, 0.18 * sp.fontsize)
                r = fitz.Rect(*sp.rect)
                r = fitz.Rect(r.x0 - pad, r.y0 - pad, r.x1 + pad, r.y1 + pad) & page.rect
                if r.is_empty:
                    continue
                fill = pick_redact_fill_for_color(sp.color)
                page.draw_rect(r, color=None, fill=fill, overlay=True, width=0)
        else:
            added_any = False
            for sp in sps:
                pad = max(1.0, 0.18 * sp.fontsize)
                r = fitz.Rect(*sp.rect)
                r = fitz.Rect(r.x0 - pad, r.y0 - pad, r.x1 + pad, r.y1 + pad) & page.rect
                if r.is_empty:
                    continue
                fill = pick_redact_fill_for_color(sp.color)
                page.add_redact_annot(r, fill=fill)
                added_any = True
            if added_any:
                try:
                    page.apply_redactions()
                except Exception as e:
                    print(f"[page {pno}] apply_redactions error: {e}")

def run_mode(mode: str, src: fitz.Document, out: fitz.Document,
             orig_index: Dict[int, List[Dict[str, Any]]],
             translate_dir: str,
             erase_mode: str, redact_color: Tuple[float,...],
             font_en_name: str, font_en_file: Optional[str],
             font_hi_name: str, font_hi_file: Optional[str],
             font_vn_name: str, font_vn_file: Optional[str],
             output_pdf: str,
             # ----- overlay parameters -----
             overlay_items: Optional[List[Dict[str, Any]]] = None,
             overlay_render: str = "image",     # "image" | "textbox"
             overlay_align: int = 0,
             overlay_line_spacing: float = 1.10,
             overlay_margin_px: float = 0.1,
             overlay_target_dpi: int = 600,
             overlay_scale_x: float = 1.0, overlay_scale_y: float = 1.0,
             overlay_off_x: float = 0.0, overlay_off_y: float = 0.0,
             # ----- translator -----
             translator = None,
             # ----- layout -----
             use_ai_layout: bool = False,
             layout_analyzer = None,
             # ----- UX -----
             progress_callback = None) -> None:
    """
    - span/line/block/hybrid: style-preserving translation and draw.
    - overlay: paint from prebuilt JSON items.
    - all: run span, line, block, hybrid, and (if provided) overlay; zip results.
    """


    # Initialize Font Matcher
    # We use provided regular fonts as base
    matcher = FontMatcher(
        en_regular_path=font_en_file, 
        hi_regular_path=font_hi_file,
        vn_regular_path=font_vn_file
    )

    # ======================= "ALL" MODE =======================
    if mode == "all":
        src_path = getattr(src, "name", None)
        if not src_path or not os.path.exists(src_path):
            raise ValueError("all mode requires 'src' to come from a real file (src.name must exist).")

        try:
            out.close()
        except Exception:
            pass
        try:
            src.close()
        except Exception:
            pass

        base, ext = os.path.splitext(output_pdf)
        out_files: List[Tuple[str, str]] = []

        def _make_output(label: str) -> str:
            return f"{base}.{label}{ext}"

        def _fresh_src_out() -> Tuple[fitz.Document, fitz.Document]:
            s = fitz.open(src_path)
            o = fitz.open()
            for p in range(len(s)):
                po = o.new_page(width=s[p].rect.width, height=s[p].rect.height)
                po.show_pdf_page(po.rect, s, p)
            return s, o

        for sub_mode in ("span", "line", "block", "hybrid"):
            try:
                s, o = _fresh_src_out()
                run_mode(
                    mode=sub_mode, src=s, out=o,
                    orig_index=orig_index, translate_dir=translate_dir,
                    erase_mode=erase_mode, redact_color=redact_color,
                    font_en_name=font_en_name, font_en_file=font_en_file,
                    font_hi_name=font_hi_name, font_hi_file=font_hi_file,
                    font_vn_name=font_vn_name, font_vn_file=font_vn_file,
                    output_pdf=_make_output(sub_mode),
                    translator=translator,
                    use_ai_layout=use_ai_layout if sub_mode == "hybrid" else False,
                    layout_analyzer=layout_analyzer,
                )
                out_files.append((sub_mode, _make_output(sub_mode)))
            except Exception as e:
                print(f"[WARN] {sub_mode} failed: {e}")

        if overlay_items:
            try:
                s, o = _fresh_src_out()
                run_mode(
                    mode="overlay", src=s, out=o,
                    orig_index=orig_index, translate_dir=translate_dir,
                    erase_mode=erase_mode, redact_color=redact_color,
                    font_en_name=font_en_name, font_en_file=font_en_file,
                    font_hi_name=font_hi_name, font_hi_file=font_hi_file,
                    font_vn_name=font_vn_name, font_vn_file=font_vn_file,
                    output_pdf=_make_output("overlay"),
                    overlay_items=overlay_items, overlay_render=overlay_render,
                    overlay_align=overlay_align, overlay_line_spacing=overlay_line_spacing,
                    overlay_margin_px=overlay_margin_px, overlay_target_dpi=overlay_target_dpi,
                    overlay_scale_x=overlay_scale_x, overlay_scale_y=overlay_scale_y,
                    overlay_off_x=overlay_off_x, overlay_off_y=overlay_off_y,
                    translator=translator,
                )
                out_files.append(("overlay", _make_output("overlay")))
            except Exception as e:
                print(f"[WARN] overlay failed: {e}")
        else:
            print("[info] overlay skipped in 'all' mode (no overlay_items provided).")

        zip_path = f"{base}_all_methods.zip"
        os.makedirs(os.path.dirname(zip_path) or ".", exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for label, path in out_files:
                if os.path.exists(path):
                    arc = os.path.basename(path)
                    zf.write(path, arcname=arc)
                else:
                    print(f"[WARN] missing output for {label}: {path}")

        print(f"[OK] Wrote {len(out_files)} PDFs and zipped -> {zip_path}")
        return

    # --------- Shared: spans (for style/erase in non-overlay modes) ----------
    spans = extract_spans_from_textlayer(src)
    transfer_style_from_original(spans, orig_index)

    # ======================= OVERLAY MODE =======================
    if mode == "overlay":
        if not overlay_items:
            raise ValueError("overlay mode requires overlay_items (use overlay_load_items on your JSON).")

        if erase_mode in ("mask", "redact"):
            spans_by_page: Dict[int, List[Span]] = {}
            for sp in spans:
                spans_by_page.setdefault(sp.page, []).append(sp)

            redacted_pages = set()
            for it in overlay_items:
                pno = int(it["page"])
                if pno < 0 or pno >= len(out):
                    continue
                page = out[pno]
                r = overlay_transform_rect(
                    it["bbox"], scale_x=overlay_scale_x, scale_y=overlay_scale_y,
                    off_x=overlay_off_x, off_y=overlay_off_y
                ) & page.rect
                if r.is_empty:
                    continue

                fill = dominant_text_fill_for_rect(pno, r, spans_by_page)

                if erase_mode == "mask":
                    page.draw_rect(r, color=None, fill=fill, overlay=True, width=0)
                else:
                    page.add_redact_annot(r, fill=fill)
                    redacted_pages.add(pno)

            if erase_mode == "redact":
                for pno in redacted_pages:
                    try:
                        out[pno].apply_redactions()
                    except Exception as e:
                        print(f"[page {pno}] apply_redactions error: {e}")

        # Prepare batch items
        # overlay_items is List[Dict]
        # We need to translate 'text' if not already done.
        
        # 1. Collect translation requests
        # We'll store index to map back
        requests = [] 
        indices = []
        
        for i, it in enumerate(overlay_items):
            pno = int(it["page"])
            if pno < 0 or pno >= len(out): continue
            
            raw_text = it.get("text", "")
            if not raw_text: continue
            
            # Determine direction (overlay logic is simpler, usually en->hi or explicit)
            # Default auto logic from build_overlay_items usually sets it?
            # Let's assume global translate_dir logic or simple detect.
            if translate_dir == "hi->en": s, d = "hi", "en"
            elif translate_dir == "en->hi": s, d = "en", "hi"
            elif translate_dir == "en->vi": s, d = "en", "vi"
            else:
                sl_detect = _dominant_script(raw_text)
                if sl_detect == "hi": d = "en"
                elif sl_detect == "en": d = "vi" # default to vi if auto and en detected? Or hi? Let's stick to safe defaults or expand logic.
                else: d = "en"
                s = sl_detect
                if s not in ("hi", "en"): s, d = "hi", "en"
            
            requests.append((raw_text, s, d))
            indices.append(i)
            
        # 2. Batch translate
        print(f"[overlay] Batch translating {len(requests)} items...")
        if progress_callback: progress_callback(f"Translating {len(requests)} text items (Overlay)...")
        
        # Googletrans hangs on concurrency > 1
        mw = 1 if (translator and translator.__class__.__name__ == "GoogleTranslator") else 5
        translated_texts = batch_translate_text(requests, translator, max_workers=mw)
        
        # 3. Apply translations back to items (temporarily or permanently)
        for idx, trans_text in zip(indices, translated_texts):
             overlay_items[idx]["translated_text"] = trans_text

        # 4. Render
        if progress_callback: progress_callback(f"Rendering {len(out)} pages (Overlay)...")
        for it in overlay_items:
            pno = int(it["page"])
            if pno < 0 or pno >= len(out):
                continue
            page = out[pno]
            rect = overlay_transform_rect(
                it["bbox"], scale_x=overlay_scale_x, scale_y=overlay_scale_y,
                off_x=overlay_off_x, off_y=overlay_off_y
            )
            if rect.is_empty:
                continue
            
            # Prefer translated text if we just made it, else existing
            text = it.get("translated_text", "") or it.get("text", "")
            base_fs = float(it.get("fontsize", 11.5))

            fontfile = overlay_choose_fontfile_for_text(text, font_en_file, font_hi_file)

            if overlay_render == "image":
                overlay_draw_text_as_image(
                    page, rect, text, base_fs, fontfile,
                    target_dpi=overlay_target_dpi,
                    line_spacing=overlay_line_spacing,
                    align=overlay_align,
                    margin_px=overlay_margin_px,
                )
            else:
                # Real text (keeps text layer). Choose fontname logically by script, but feed fontfile.
                if _DEV.search(text or ""):
                    fname, ffile = font_hi_name, font_hi_file
                else:
                    fname, ffile = font_en_name, font_en_file
                
                # Check for styles in item? Overlay usually doesn't have flags unless we carried them over.
                # Use standard matching just in case we have metadata.
                # But item is a dict from JSON. Let's stick to basic logic or enhance Overlay item schema later.
                # For now, simplistic is fine for Overlay.
                
                insert_text_fit(
                    page, (rect.x0, rect.y0, rect.x1, rect.y1),
                    text, fname, base_fs, (0.0,), fontfile=ffile
                )

        # Save & close
        os.makedirs(os.path.dirname(output_pdf) or ".", exist_ok=True)
        out.save(output_pdf); out.close(); src.close()
        print(f"[OK] Wrote translated PDF to: {output_pdf}")
        return

    if mode == "hybrid":
        if use_ai_layout and layout_analyzer:
            print("[hybrid] Using AI Layout Analysis...")
            hblocks = extract_blocks_from_layout(src, layout_analyzer)
        else:
            hblocks = extract_blocks_with_segments(src)
            
        derive_block_styles_from_spans(hblocks, spans)

        # ---- ERASE: dynamic fill, supports both overlay_items and block fallback ----
        if erase_mode in ("mask", "redact"):
            spans_by_page: Dict[int, List[Span]] = {}
            for sp in spans:
                spans_by_page.setdefault(sp.page, []).append(sp)

            redacted_pages = set()

            def _erase_rect(pno: int, r: fitz.Rect, pad_pt: float):
                page = out[pno]
                rr = fitz.Rect(r.x0 - pad_pt, r.y0 - pad_pt, r.x1 + pad_pt, r.y1 + pad_pt) & page.rect
                if rr.is_empty:
                    return
                fill = dominant_text_fill_for_rect(pno, rr, spans_by_page)
                if erase_mode == "mask":
                    page.draw_rect(rr, color=None, fill=fill, overlay=True, width=0)
                else:
                    page.add_redact_annot(rr, fill=fill)
                    redacted_pages.add(pno)

            if overlay_items:
                for it in overlay_items:
                    pno = int(it["page"])
                    if not (0 <= pno < len(out)):
                        continue
                    rect = overlay_transform_rect(
                        it["bbox"],
                        scale_x=overlay_scale_x, scale_y=overlay_scale_y,
                        off_x=overlay_off_x, off_y=overlay_off_y
                    )
                    base_fs = float(it.get("fontsize", 11.5))
                    pad = max(1.0, 0.18 * base_fs)
                    _erase_rect(pno, rect, pad)
            else:
                for bl in hblocks:
                    pno = bl.page
                    rect = fitz.Rect(*bl.rect)
                    pad = max(1.0, 0.18 * (bl.fontsize or 11.5))
                    _erase_rect(pno, rect, pad)

            if erase_mode == "redact":
                for pno in redacted_pages:
                    try:
                        out[pno].apply_redactions()
                    except Exception as e:
                        print(f"[page {pno}] apply_redactions error: {e}")

        # 1. Collect requests (Hybrid is complex: segments inside lines vs block text)
        requests = []
        # Store metadata to map back: (block_idx, line_idx, seg_idx) or (block_idx, None, None)
        map_back = [] 
        
        for b_i, bl in enumerate(hblocks):
            if translate_dir == "hi->en":
                 sl_def, dl_def = "hi", "en"
            elif translate_dir == "en->hi":
                 sl_def, dl_def = "en", "hi"
            elif translate_dir == "en->vi":
                 sl_def, dl_def = "en", "vi"
            else:
                 sl_def = _dominant_script(bl.text)
                 # Auto logic: if hi -> en. If en -> vi (if user wants vi). But "auto" is ambiguous.
                 # Let's keep existing "auto" as en<->hi for backward compat unless we improve it.
                 dl_def = "en" if sl_def == "hi" else "hi"
                 if sl_def not in ("hi","en"): sl_def, dl_def = "hi", "en"
            
            if is_table_like(bl):
                 cols = build_columns(bl)
                 # We need to translate segments
                 for l_i, ln in enumerate(bl.lines):
                     for s_i, seg in enumerate(ln.segments):
                         requests.append((seg.text, sl_def, dl_def))
                         map_back.append({'type': 'seg', 'b': b_i, 'l': l_i, 's': s_i, 'cols': cols})
            else:
                 # Translate full block
                 requests.append((bl.text, sl_def, dl_def))
                 map_back.append({'type': 'block', 'b': b_i})

        # 2. Batch Translate
        print(f"[hybrid] Batch translating {len(requests)} items...")
        if progress_callback: progress_callback(f"Translating {len(requests)} text blocks (hybrid mode)...")
        
        # Googletrans hangs on concurrency > 1
        mw = 1 if (translator and translator.__class__.__name__ == "GoogleTranslator") else 5
        results = batch_translate_text(requests, translator, max_workers=mw)
        
        # 3. Render
        print(f"[{mode}] Rendering {len(src)} pages...")
        if progress_callback: progress_callback(f"Rendering {len(src)} pages ({mode} mode)...")
        
        # We need to map translations back.
        # requests order: loop over blocks (which are per page usually? No, hblocks is flat list?):
        # We iterate map_back and results together
        for info, res_text in zip(map_back, results):
            text_out = res_text or ""
            bl = hblocks[info['b']]
            page = out[bl.page]
            
            if info['type'] == 'seg':
                 ln = bl.lines[info['l']]
                 seg = ln.segments[info['s']]
                 cols = info['cols']
                 y0, y1 = ln.rect[1], ln.rect[3]
                 
                 # Font matching
                 if text_out and _DEV.search(text_out): tgt = "hi"
                 else: tgt = "en"
                 fname, ffile = matcher.match_font(tgt, ln.flags, ln.font)

                 try: base_size = statistics.median(seg.sizes)
                 except: base_size = bl.fontsize
                 
                 best_col = max(cols, key=lambda c: max(0.0, min(seg.rect[2], c[1]) - max(seg.rect[0], c[0])))
                 cell_rect = (best_col[0], y0, best_col[1], y1)
                 insert_text_fit(page, cell_rect, text_out, fname, base_size, bl.color, fontfile=ffile)
            else:
                 # block
                 if text_out and _DEV.search(text_out): tgt = "hi"
                 else: tgt = "en"
                 fname, ffile = matcher.match_font(tgt, bl.flags, bl.font)
                 insert_text_fit(page, bl.rect, text_out, fname, bl.fontsize, bl.color, fontfile=ffile)

        os.makedirs(os.path.dirname(output_pdf) or ".", exist_ok=True)
        out.save(output_pdf); out.close(); src.close()
        print(f"[OK] Wrote translated PDF to: {output_pdf}")
        return

    erase_original_text(out, spans, mode, erase_mode, redact_color)

    if mode == "span":
        requests = []
        for sp in spans:
            if translate_dir == "hi->en": sl, dl = "hi","en"
            elif translate_dir == "en->hi": sl, dl = "en","hi"
            elif translate_dir == "en->vi": sl, dl = "en","vi"
            else:
                sl = _dominant_script(sp.text); dl = "en" if sl=="hi" else "hi"
                if sl not in ("hi","en"): sl, dl = "hi","en"
            requests.append((sp.text, sl, dl))
            
        print(f"[span] Batch translating {len(requests)} items...")
        results = batch_translate_text(requests, translator)
        
        for sp, text_out in zip(spans, results):
            page = out[sp.page]
            if text_out and _DEV.search(text_out): tgt_script = "hi"
            else:                                   tgt_script = "en"
            fname, ffile = matcher.match_font(tgt_script, sp.flags, sp.font)
            insert_text_fit(page, sp.rect, text_out, fname, sp.fontsize, sp.color, fontfile=ffile)

    elif mode == "line":
        lines = extract_lines_from_textlayer(src)
        derive_line_styles_from_spans(lines, spans)
        
        requests = []
        for ln in lines:
            if translate_dir == "hi->en": sl, dl = "hi","en"
            elif translate_dir == "en->hi": sl, dl = "en","hi"
            elif translate_dir == "en->vi": sl, dl = "en","vi"
            else:
                sl = _dominant_script(ln.text); dl = "en" if sl=="hi" else "hi"
                if sl not in ("hi","en"): sl, dl = "hi","en"
            requests.append((ln.text, sl, dl))
            
        print(f"[line] Batch translating {len(requests)} items...")
        results = batch_translate_text(requests, translator)

        for ln, text_out in zip(lines, results):
            page = out[ln.page]
            if text_out and _DEV.search(text_out): tgt_script = "hi"
            else:                                   tgt_script = "en"
            fname, ffile = matcher.match_font(tgt_script, ln.flags, ln.font)
            base_size = ln.fontsize if ln.fontsize else 11.5
            color     = ln.color if ln.color else (0.0,)
            insert_text_fit(page, ln.rect, text_out, fname, base_size, color, fontfile=ffile)

    elif mode == "block":
        blocks = extract_blocks_from_textlayer(src)
        derive_block_styles_from_spans(blocks, spans)
        
        requests = []
        for bl in blocks:
            if translate_dir == "hi->en": sl, dl = "hi","en"
            elif translate_dir == "en->hi": sl, dl = "en","hi"
            elif translate_dir == "en->vi": sl, dl = "en","vi"
            else:
                sl = _dominant_script(bl.text); dl = "en" if sl=="hi" else "hi"
                if sl not in ("hi","en"): sl, dl = "hi","en"
            requests.append((bl.text, sl, dl))

        print(f"[block] Batch translating {len(requests)} items...")
        results = batch_translate_text(requests, translator)

        for bl, text_out in zip(blocks, results):
            page = out[bl.page]
            if text_out and _DEV.search(text_out): tgt_script = "hi"
            else:                                   tgt_script = "en"
            fname, ffile = matcher.match_font(tgt_script, bl.flags, bl.font)
            
            base_size = bl.fontsize if bl.fontsize else 11.5
            color     = bl.color if bl.color else (0.0,)
            insert_text_fit(page, bl.rect, text_out, fname, base_size, color, fontfile=ffile)

    else:
        raise ValueError(f"Unknown mode: {mode}")

    os.makedirs(os.path.dirname(output_pdf) or ".", exist_ok=True)
    out.save(output_pdf); out.close(); src.close()
    print(f"[OK] Wrote translated PDF to: {output_pdf}")