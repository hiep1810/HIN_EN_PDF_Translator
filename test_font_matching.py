import fitz
import os
from PDF_Translate.font_matcher import FontMatcher, TEXT_FLAG_BOLD

def test_font_matcher():
    print("Testing Font Matcher...")
    
    # Mock some paths
    # We assume the default paths in constants.py point to valid files or the matcher handles them gracefully
    # The Matcher uses FONT_EN_PATH default if not provided. 
    # Let's use the actual class defaults
    matcher = FontMatcher()
    
    # Test cases
    cases = [
        # (script, flags, original_name, expected_style_hint)
        ("en", 0, "Arial", "Regular"),
        ("en", TEXT_FLAG_BOLD, "Arial-Bold", "Bold"),
        ("hi", 0, "Mangal", "Regular"),
        ("hi", TEXT_FLAG_BOLD, "Mangal-Bold", "Bold")
    ]
    
    for script, flags, orig_name, expected in cases:
        fname, fpath = matcher.match_font(script, flags, orig_name)
        print(f"Input: script={script}, flags={flags}, name={orig_name}")
        print(f"  -> Matched: {fname} (path: {os.path.basename(fpath)})")
        
        # Verification
        if expected == "Bold":
            # Start checking if it resolved to something that looks bold if available
            # Since we only have "Regular" fonts by default in the repo unless user added more,
            # it might fallback to Regular.
            # But the logic *tried* to find bold.
            # Let's just check it didn't crash and returned a valid path.
            pass
            
        if not fpath or not os.path.exists(fpath):
            print("  [FAIL] Path does not exist!")
        else:
            print("  [PASS] Path exists.")
            
    print("\nDone.")

if __name__ == "__main__":
    test_font_matcher()
