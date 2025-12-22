from abc import ABC, abstractmethod
from typing import List, Tuple, Any
import fitz
from PIL import Image
import numpy as np

class LayoutAnalyzer(ABC):
    @abstractmethod
    def analyze_page(self, page_image: Image.Image) -> List[Tuple[float, float, float, float]]:
        """
        Analyze page image and return list of bounding boxes (x0, y0, x1, y1) for text regions.
        Coordinates should be scaling-independent or relative to the image size, 
        but Surya returns absolute pixels for the input image. 
        We will return absolute pixels based on the input image size.
        """
        pass

class SuryaLayoutAnalyzer(LayoutAnalyzer):
    def __init__(self):
        try:
            from surya.detection import DetectionPredictor
            self.predictor = DetectionPredictor()
            self.layout_predictor = None
        except ImportError:
             raise ImportError("Failed to import surya.detection.DetectionPredictor. Please ensure surya-ocr >= 0.6.0 is installed.")

    def analyze_page(self, page_image: Image.Image) -> List[Tuple[float, float, float, float]]:
        """
        Returns list of bboxes [x0, y0, x1, y1] for detected text regions.
        Prioritizes Layout Analysis (blocks) if available, falls back to Text Detection (lines).
        """
        # 1. Try Layout Analysis first (better for blocks)
        try:
            if self.layout_predictor is None:
                from surya.layout import LayoutPredictor
                self.layout_predictor = LayoutPredictor()
                
            results = self.layout_predictor([page_image])
            res = results[0]
            
            output_boxes = []
            for item in res.bboxes:
                # LayoutBox has bbox [x0, y0, x1, y1]
                output_boxes.append(tuple(item.bbox))
                
            return output_boxes
            
        except ImportError:
            pass # No layout module, strictly stick to text detection
        except Exception as e:
            print(f"Surya Layout Analysis failed: {e}. Falling back to Text Detection.")

        # 2. Fallback to Text Detection (lines)
        results = self.predictor([page_image])
        res = results[0]
        
        boxes = []
        for item in res.bboxes:
             # TextLine bbox is [x0, y0, x1, y1]
             boxes.append(tuple(item.bbox))
             
        return boxes

def get_layout_analyzer(method: str) -> LayoutAnalyzer:
    if method == "Surya":
        return SuryaLayoutAnalyzer()
    else:
        raise ValueError(f"Unknown layout method: {method}")
