
import asyncio
import nest_asyncio
import time
import random

nest_asyncio.apply()

class GoogleTranslator:
    def __init__(self):
        from googletrans import Translator as GTranslator
        self.service = GTranslator(timeout=10, service_urls=["translate.googleapis.com"])
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        try:
            # googletrans uses 'src' and 'dest'
            src = source_lang if source_lang != "auto" else "auto"
            
            # Rate limit protection: Sleep randomized 0.5 - 1.5s
            print("debug: sleeping...")
            time.sleep(random.uniform(0.1, 0.2)) # shorter for test
            
            print("debug: calling service.translate...")
            # Use asyncio.run if possible, else handle existing loop
            res = self.service.translate(text, src=src, dest=target_lang)
            print(f"debug: res type: {type(res)}")
            
            if asyncio.iscoroutine(res):
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                print(f"debug: loop running? {loop.is_running()}")
                if loop.is_running():
                    res = loop.run_until_complete(res)
                else:
                    res = loop.run_until_complete(res)
                
            return getattr(res, "text", text)
        except Exception as e:
            print(f"[GoogleTranslator] Error: {e}")
            return text



async def main():
    t = GoogleTranslator()
    try:
        # Test bulk
        # Bypass wrapper translate() and call service directly to see if library supports it
        inputs = ["Hello", "World", "This is a test"]
        res = t.service.translate(inputs, src='en', dest='vi')
        if asyncio.iscoroutine(res):
             res = await res
        
        print(f"Bulk Result Type: {type(res)}")
        if isinstance(res, list):
            for r in res:
                print(f" - {r.text}")
    except Exception as e:
        print(f"Bulk failed: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
