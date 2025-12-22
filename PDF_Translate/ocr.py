import fitz, subprocess, shutil, os

def rasterize_pdf_to_image_pdf(input_path: str, dpi: int = 300) -> str:
    doc = fitz.open(input_path); tmp_dir = "temp"; os.makedirs(tmp_dir, exist_ok=True)
    out_path = os.path.join(tmp_dir, "rasterized.pdf")
    out = fitz.open(); zoom = dpi/72.0; mat = fitz.Matrix(zoom, zoom)
    try:
        for pno in range(len(doc)):
            page = doc[pno]; pix = page.get_pixmap(matrix=mat, alpha=False)
            po = out.new_page(width=page.rect.width, height=page.rect.height)
            po.insert_image(po.rect, stream=pix.tobytes("png"))
        out.save(out_path)
    finally:
        out.close(); doc.close()
    return out_path

def ocr_fix_pdf(input_path: str, lang: str, dpi: str, optimize: str, progress_callback=None) -> str:
    if shutil.which("ocrmypdf") is None:
        print("[ocrmypdf] not found; using original.")
        return input_path
    
    out_dir = "temp"
    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, "ocr_fixed.pdf")
    
    cmd = [
        "ocrmypdf", "--language", lang, "--deskew", "--rotate-pages", "--force-ocr",
        "--image-dpi", dpi, "--oversample", dpi, "--optimize", optimize,
        os.fspath(input_path), os.fspath(output_path)
    ]
    print("[ocrmypdf]", " ".join(cmd))
    
    # Run with Popen to capture stderr (where ocrmypdf writes progress)
    with subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, bufsize=1, encoding="utf-8", errors="replace") as proc:
        for line in proc.stderr:
            line = line.strip()
            if line:
                # print(f"[OCR-LOG] {line}") # Debug
                if progress_callback:
                    progress_callback(f"OCR: {line}")
    
    if proc.returncode == 0:
        print("[ocrmypdf] success ->", output_path)
        return output_path
        
    print("[ocrmypdf] failed; fallback to rasterize.")
    
    # Fallback to rasterization
    try:
        if progress_callback: progress_callback("OCR failed, trying rasterization fallback...")
        image_pdf = rasterize_pdf_to_image_pdf(input_path, dpi=300)
    except Exception as e:
        print("[fallback] rasterize failed:", e)
        return input_path
        
    output_path2 = os.path.join(out_dir, "ocr_fixed_from_image.pdf")
    cmd2 = [
        "ocrmypdf", "--language", lang, "--deskew", "--rotate-pages",
        "--image-dpi", dpi, "--oversample", dpi, "--optimize", optimize,
        os.fspath(image_pdf), os.fspath(output_path2)
    ]
    print("[ocrmypdf fallback]", " ".join(cmd2))
    
    with subprocess.Popen(cmd2, stderr=subprocess.PIPE, text=True, bufsize=1, encoding="utf-8", errors="replace") as proc2:
        for line in proc2.stderr:
            line = line.strip()
            if line and progress_callback:
                progress_callback(f"OCR (Fallback): {line}")

    if proc2.returncode == 0:
        print("[ocrmypdf] success via rasterize ->", output_path2)
        return output_path2
        
    print("[ocrmypdf] fallback failed; using original.")
    return input_path