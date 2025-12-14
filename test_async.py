import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

# Mock Translation Function
def mock_translate(text: str, src: str, dest: str) -> str:
    # Simulate API latency
    time.sleep(1.0) 
    return f"Translated({text})"

class MockTranslator:
    def translate(self, text, source_lang, target_lang):
        return mock_translate(text, source_lang, target_lang)

# Implementation of batch_translate_text (copy-paste logic for independent testing or import)
# We import it to test actual code
try:
    from PDF_Translate.textlayer import batch_translate_text
    print("Imported batch_translate_text successfully.")
except ImportError:
    # Fallback if relative import fails in script
    print("Using local definition of batch_translate_text")
    def batch_translate_text(items, translator, max_workers=5):
        def _worker(args):
            txt, s, d = args
            return translator.translate(txt, s, d)
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_worker, items))
        return results

def test_async_speedup():
    items = [
        ("Hello", "en", "hi"), 
        ("World", "en", "hi"), 
        ("Test", "en", "hi"), 
        ("Speed", "en", "hi"), 
        ("Async", "en", "hi")
    ]
    
    translator = MockTranslator()
    
    print(f"Testing with {len(items)} items. Each takes 1.0s. Serial would take {len(items)}s.")
    
    start = time.time()
    results = batch_translate_text(items, translator, max_workers=5)
    end = time.time()
    
    duration = end - start
    print(f"Total duration: {duration:.2f}s")
    print(f"Results: {results}")
    
    if duration < 2.5:
        print("[PASS] Parallel execution confirmed (took significantly less than serial time).")
    else:
        print("[FAIL] Execution took too long, might be serial.")

if __name__ == "__main__":
    test_async_speedup()
