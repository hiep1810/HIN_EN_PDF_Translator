import sys
import traceback

print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")

try:
    print("Attempting to import surya...")
    import surya
    print(f"Surya imported. File: {surya.__file__}")
    
    print("Attempting to import surya.detection...")
    from surya.detection import batch_text_detection
    print("surya.detection imported successfully.")
    
except Exception:
    traceback.print_exc()
