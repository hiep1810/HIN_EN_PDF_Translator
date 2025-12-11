import sys
import os
from PDF_Translate.translation import get_translator, GoogleTranslator

def test_google_translation():
    print("Testing Google Translator...")
    try:
        t = get_translator("Google")
        assert isinstance(t, GoogleTranslator)
        res = t.translate("Hello world", "en", "hi")
        print(f"Result (en->hi): {res}")
        if res == "Hello world": 
            print("[WARN] Translation returned same text (could be failure or identical).")
        else:
            print("[PASS] Translation changed text.")
    except Exception as e:
        print(f"[FAIL] Google Translator failed: {e}")

def test_providers_instantiation():
    print("\nTesting Provider Instantiation (Mock)...")
    try:
        t = get_translator("DeepL", api_key="test")
        print("[PASS] DeepL instantiated")
    except ImportError:
        print("[SKIP] DeepL lib not found")
    except Exception as e:
        print(f"[FAIL] DeepL instantiation: {e}")

    try:
        t = get_translator("OpenAI", api_key="test")
        print("[PASS] OpenAI instantiated")
    except ImportError:
        print("[SKIP] OpenAI lib not found")
    except Exception as e:
        print(f"[FAIL] OpenAI instantiation: {e}")

    try:
        t = get_translator("Ollama")
        print("[PASS] Ollama instantiated")
    except Exception as e:
        print(f"[FAIL] Ollama instantiation: {e}")

if __name__ == "__main__":
    test_google_translation()
    test_providers_instantiation()
