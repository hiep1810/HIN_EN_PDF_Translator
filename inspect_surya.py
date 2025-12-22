import surya.detection
import inspect

print("Contents of surya.detection:")
print(dir(surya.detection))

print("\nTrying to find text detection functions...")
for name, obj in inspect.getmembers(surya.detection):
    if inspect.isfunction(obj):
        print(f"Function: {name}")
