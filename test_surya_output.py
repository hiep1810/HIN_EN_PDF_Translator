from surya.detection import DetectionPredictor
from PIL import Image

predictor = DetectionPredictor()
# Create dummy image
img = Image.new('RGB', (100, 100), color = 'white')
predictions = predictor([img])
print("Predictions type:", type(predictions))
print("First prediction type:", type(predictions[0]))
print("First prediction dir:", dir(predictions[0]))
if hasattr(predictions[0], 'bboxes'):
    print("Has bboxes attribute.")
