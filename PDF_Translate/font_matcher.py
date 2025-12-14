import fitz
import os
from typing import Tuple, Optional
from .constants import (
    FONT_EN_LOGICAL, FONT_EN_PATH,
    FONT_HI_LOGICAL, FONT_HI_PATH,
    FONT_HI_LOGICAL_2, FONT_HI_PATH_2
)

# PyMuPDF text flags (usually not exported in top-level fitz)
TEXT_FLAG_SUPERSCRIPT = 1
TEXT_FLAG_ITALIC = 2
TEXT_FLAG_SERIF = 4
TEXT_FLAG_MONOSPACE = 8
TEXT_FLAG_BOLD = 16

class FontMatcher:
    def __init__(self, 
                 en_regular_path: str = FONT_EN_PATH,
                 hi_regular_path: str = FONT_HI_PATH_2):
        
        self.en_regular = en_regular_path
        self.hi_regular = hi_regular_path
        
        # We can expand this registry later or introspect the assets folder
        self.registry = {
            "en": {
                "regular": self.en_regular,
                "bold": self.en_regular, # Fallback if no specific bold
                "serif": self.en_regular, # Fallback
                "serif_bold": self.en_regular, # Fallback
            },
            "hi": {
                "regular": self.hi_regular,
                "bold": self.hi_regular,
            }
        }
        
        # Try to find better matches in the same dir if possible
        self._auto_discover_variants("en", en_regular_path)
        self._auto_discover_variants("hi", hi_regular_path)

    def _auto_discover_variants(self, lang: str, base_path: Optional[str]):
        if not base_path or not os.path.exists(base_path):
            return
            
        dirname = os.path.dirname(base_path)
        basename = os.path.basename(base_path)
        name_root, ext = os.path.splitext(basename)
        
        # Simple heuristic to find Bold, Italic, etc.
        # e.g. NotoSans-Regular -> NotoSans-Bold
        
        # Strip "Regular"
        prefix = name_root.replace("-Regular", "").replace("Regular", "")
        
        candidates = {
            "bold": ["-Bold", "Bold"],
            "italic": ["-Italic", "Italic"],
            "bold_italic": ["-BoldItalic", "BoldItalic"],
        }
        
        for key, suffixes in candidates.items():
            for suf in suffixes:
                p = os.path.join(dirname, f"{prefix}{suf}{ext}")
                if os.path.exists(p):
                    self.registry[lang][key] = p
                    break

    def match_font(self, script: str, original_flags: int, original_font_name: str = "") -> Tuple[str, str]:
        """
        Returns (font_name, font_file_path) based on script and style flags.
        """
        # Determine strict script
        lang = "hi" if script == "hi" else "en"
        
        # Determine style from flags
        is_bold = bool(original_flags & TEXT_FLAG_BOLD)
        is_serif = bool(original_flags & TEXT_FLAG_SERIF) or "Times" in original_font_name
        is_italic = bool(original_flags & TEXT_FLAG_ITALIC)
        
        # Select from registry
        # Current logic is simple: Regular or Bold.
        # We can add Serif support if we strictly have a Serif Font file.
        # Currently defaults (NotoSans, Tiro) are Sans/Serif respectively but we treat them as "standard".
        
        style_key = "regular"
        if is_bold:
            style_key = "bold"
        
        # If we had a serif registry, we'd check it here.
        
        font_path = self.registry[lang].get(style_key, self.registry[lang]["regular"])
        
        # Logical Name
        # If we used a custom path, derive a name
        font_name = os.path.splitext(os.path.basename(font_path))[0]
        
        return font_name, font_path
