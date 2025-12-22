from surya.detection import DetectionPredictor
import inspect

print("Methods of DetectionPredictor:")
for name, obj in inspect.getmembers(DetectionPredictor):
    if inspect.isfunction(obj) or inspect.ismethod(obj):
        print(f"Method: {name}")
