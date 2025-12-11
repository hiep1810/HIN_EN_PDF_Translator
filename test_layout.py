import sys
import fitz
from unittest.mock import MagicMock
from PDF_Translate.layout import get_layout_analyzer, SuryaLayoutAnalyzer
from PDF_Translate.hybrid import extract_blocks_from_layout

def test_layout_loading():
    print("Testing Surya Layout Analyzer loading...")
    try:
        # We mock surya modules to avoid needing actual model weights/install for this simple logic test
        sys.modules["surya.detection"] = MagicMock()
        sys.modules["surya.model.detection.model"] = MagicMock()
        sys.modules["surya.settings"] = MagicMock()
        sys.modules["surya.layout"] = MagicMock()
        sys.modules["surya.model.layout.model"] = MagicMock()
        sys.modules["surya.model.layout.processor"] = MagicMock()
        
        analyzer = get_layout_analyzer("Surya")
        print("[PASS] SuryaLayoutAnalyzer instantiated (with mocks).")
        return analyzer
    except Exception as e:
        print(f"[FAIL] Instantiation failed: {e}")
        return None

def test_block_extraction():
    print("\nTesting extract_blocks_from_layout logic...")
    # Create a dummy PDF
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    page.insert_text((10, 10), "Block 1 Line 1")
    page.insert_text((10, 20), "Block 1 Line 2")
    page.insert_text((60, 10), "Block 2 Line 1") # Right column
    
    # Mock analyzer returning two distinct boxes
    analyzer = MagicMock()
    # mocked return: list of [x0, y0, x1, y1] in pixels
    # Assume 100x100 image for 100x100 pdf (scale 1)
    analyzer.analyze_page.return_value = [
         (5, 5, 50, 50),   # Left block
         (55, 5, 95, 50)   # Right block
    ]
    
    try:
        blocks = extract_blocks_from_layout(doc, analyzer)
        print(f"Extracted {len(blocks)} blocks.")
        if len(blocks) == 2:
             print("[PASS] Correctly extracted 2 blocks from AI regions.")
             print(f"Block 1 text: {blocks[0].text.replace('\n', ' ')}")
             print(f"Block 2 text: {blocks[1].text.replace('\n', ' ')}")
        else:
             print(f"[FAIL] Expected 2 blocks, got {len(blocks)}")
             for i, b in enumerate(blocks):
                 print(f"  Block {i}: {b.text}")
                 
    except Exception as e:
        print(f"[FAIL] Extraction logic failed: {e}")

if __name__ == "__main__":
    analyzer = test_layout_loading()
    test_block_extraction()
