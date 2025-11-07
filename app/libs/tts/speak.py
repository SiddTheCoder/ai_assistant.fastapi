from gtts import gTTS
from pydub import AudioSegment
import pygame
import os
import threading

def speak(text, speed=1.5):
    tts = gTTS(text=text, lang='en')
    filename = "temp.mp3"
    tts.save(filename)

    sound = AudioSegment.from_file(filename)
    faster_sound = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    }).set_frame_rate(sound.frame_rate)

    faster_file = "temp_fast.mp3"
    faster_sound.export(faster_file, format="mp3")

    pygame.mixer.init()
    pygame.mixer.music.load(faster_file)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    pygame.mixer.quit()
    os.remove(filename)
    os.remove(faster_file)

def speak_background(text, speed=1.5):
    thread = threading.Thread(target=speak, args=(text, speed))
    thread.start()
    return thread  # optional, if you want to wait later

if __name__ == "__main__":
    speak("Hello, this is a test of the text to speech system.", speed=1.2)
