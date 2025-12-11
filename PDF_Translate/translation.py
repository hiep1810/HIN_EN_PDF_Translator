from abc import ABC, abstractmethod
from typing import Optional, List
import os
import asyncio
import nest_asyncio

# Apply nest_asyncio to support nested event loops if necessary
nest_asyncio.apply()

class Translator(ABC):
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text from source_lang to target_lang.
        source_lang and target_lang should be 2-letter codes (e.g., 'en', 'hi').
        """
        pass

class GoogleTranslator(Translator):
    def __init__(self):
        from googletrans import Translator as GTranslator
        self.service = GTranslator(timeout=10, service_urls=["translate.googleapis.com"])
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        try:
            # googletrans uses 'src' and 'dest'
            # Mapping 'auto' to None for googletrans might be needed, or it handles 'auto'
            src = source_lang if source_lang != "auto" else "auto"
            res = self.service.translate(text, src=src, dest=target_lang)
            
            # wrapper might return coroutine in some versions, handle it
            if asyncio.iscoroutine(res):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                res = loop.run_until_complete(res)
                
            return getattr(res, "text", text)
        except Exception as e:
            print(f"[GoogleTranslator] Error: {e}")
            return text

class DeepLTranslator(Translator):
    def __init__(self, api_key: str):
        import deepl
        self.translator = deepl.Translator(api_key)
        
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        try:
            # DeepL uses 'source_lang' and 'target_lang'
            # Note: DeepL Source lang is optional (auto-detect)
            # Target lang requires specific codes (EN-US or EN-GB for English target)
            
            target = target_lang.upper()
            if target == "EN":
                target = "EN-US" # Default to US English
                
            source = source_lang.upper() if source_lang != "auto" else None
            
            result = self.translator.translate_text(text, source_lang=source, target_lang=target)
            return result.text
        except Exception as e:
            print(f"[DeepLTranslator] Error: {e}")
            return text

class OpenAITranslator(Translator):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        try:
            prompt = f"Translate the following text from {source_lang} to {target_lang}. Return only the translated text, preserving original formatting and whitespace as much as possible:\n\n{text}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional translator. Translate the user input accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[OpenAITranslator] Error: {e}")
            return text

class OllamaTranslator(Translator):
    def __init__(self, model: str = "llama3"):
        # We assume local ollama instance
        self.model = model
        # Check if ollama python client is installed, or use requests
        try:
            import ollama
            self.has_client = True
        except ImportError:
            self.has_client = False
            import requests
            self.requests = requests
            self.base_url = "http://localhost:11434/api/generate"

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        prompt = f"Translate this text from {source_lang} to {target_lang}. Output ONLY the translation without any introduction or notes:\n\n{text}"
        
        try:
            if self.has_client:
                import ollama
                response = ollama.chat(model=self.model, messages=[
                  {'role': 'user', 'content': prompt},
                ])
                return response['message']['content']
            else:
                # Use requests fallback
                data = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
                resp = self.requests.post(self.base_url, json=data)
                if resp.status_code == 200:
                    return resp.json().get("response", "").strip()
                else:
                    print(f"[OllamaTranslator] API Error: {resp.text}")
                    return text
        except Exception as e:
             print(f"[OllamaTranslator] Error: {e}")
             return text

def get_translator(provider: str, **kwargs) -> Translator:
    if provider == "Google":
        return GoogleTranslator()
    elif provider == "DeepL":
        return DeepLTranslator(api_key=kwargs.get("api_key"))
    elif provider == "OpenAI":
        return OpenAITranslator(api_key=kwargs.get("api_key"), model=kwargs.get("model", "gpt-4o-mini"))
    elif provider == "Ollama":
        return OllamaTranslator(model=kwargs.get("model", "llama3"))
    else:
        raise ValueError(f"Unknown provider: {provider}")
