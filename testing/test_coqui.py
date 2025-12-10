# # test_coqui.py
# from TTS.api import TTS
# import time

# def test_coqui():
#     print("🎙️  Coqui TTS Test\n")
    
#     # Initialize TTS
#     print("1. Loading model (this may take a moment)...")
#     start = time.time()
    
#     # Using a fast, good quality English model
#     tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=True)
    
#     print(f"   ✅ Model loaded in {time.time() - start:.2f}s\n")
    
#     # Test 1: English
#     print("2. Generating English speech...")
#     text_en = "Hello! This is a test of Coqui TTS. How does it sound?"
#     tts.tts_to_file(text=text_en, file_path="test_english.wav")
#     print("   ✅ Saved: test_english.wav\n")
    
#     print("✅ Test complete! Check the audio files.")

# if __name__ == "__main__":
#     test_coqui()