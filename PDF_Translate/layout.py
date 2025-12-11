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
            from surya.detection import batch_text_detection
            from surya.model.detection.model import load_model, load_processor
            from surya.settings import settings
            
            self.model = load_model(checkpoint=settings.DETECTOR_MODEL_CHECKPOINT)
            self.processor = load_processor(checkpoint=settings.DETECTOR_MODEL_CHECKPOINT)
            self.batch_text_detection = batch_text_detection
        except ImportError:
            raise ImportError("surya-ocr is not installed. Please run `pip install surya-ocr`.")
        except Exception as e:
            raise RuntimeError(f"Failed to load Surya model: {e}")

    def analyze_page(self, page_image: Image.Image) -> List[Tuple[float, float, float, float]]:
        """
        Returns list of bboxes [x0, y0, x1, y1] for detected text lines/regions.
        Surya detects *lines*. We might want to group them or just use lines.
        Actually, Surya has layout analysis (detection of columns/blocks) 
        but the primary `batch_text_detection` returns lines/polygons.
        
        To get high quality blocks, we can just return the lines and let our hybrid 
        heuristic merge them, OR we can rely on Surya's layout model if we used `surya_layout`.
        
        However, `surya-ocr` python API for layout is:
        `from surya.layout import batch_layout_detection`
        
        Let's try to support `batch_layout_detection` if available, checking imports.
        """
        try:
            from surya.layout import batch_layout_detection
            from surya.model.layout.model import load_model as load_layout_model
            from surya.model.layout.processor import load_processor as load_layout_processor
            from surya.settings import settings
            
            if not hasattr(self, 'layout_model'):
                self.layout_model = load_layout_model(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
                self.layout_processor = load_layout_processor(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
                self.batch_layout_detection = batch_layout_detection
                
            # Run layout detection
            results = self.batch_layout_detection([page_image], self.layout_model, self.layout_processor)
            res = results[0]
            
            # extract bboxes from layout results
            # res.bboxes is a list of LayoutBox objects usually
            output_boxes = []
            for item in res.bboxes:
                # item.bbox needs to be converted to list/tuple
                # Surya layout boxes are [x0, y0, x1, y1]
                bbox = item.bbox
                output_boxes.append(tuple(bbox))
                
            return output_boxes
            
        except ImportError:
            # Fallback to text detection if layout module missing (older surya?) 
            # or just fail. 
            # But wait, user asked for 'Surya (Layout)'. 
            # We assume modern surya-ocr installed which has layout.
            print("Surya layout module not found, falling back to text detection lines.")
            predictions = self.batch_text_detection([page_image], self.model, self.processor)
            res = predictions[0]
            
            boxes = []
            for polygon in res.bboxes:
                 # polygon is [x0,y0, x1,y0, x1,y1, x0,y1] usually for surya detection
                 # we want bbox
                 xs = [p[0] for p in polygon]
                 ys = [p[1] for p in polygon]
                 boxes.append((min(xs), min(ys), max(xs), max(ys)))
            return boxes

def get_layout_analyzer(method: str) -> LayoutAnalyzer:
    if method == "Surya":
        return SuryaLayoutAnalyzer()
    else:
        raise ValueError(f"Unknown layout method: {method}")
