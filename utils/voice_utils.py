import time
from colorama import Fore, Style
import pygame

class VoiceAssistant:
    def __init__(self, sarvam_handler):
        self.sarvam = sarvam_handler
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)
        self.NUMBER_WORDS_TE = {
            "వన్": "1", "టూ": "2", "త్రి": "3",
            "ఒకటి": "1", "రెండు": "2", "మూడు": "3",
            "1": "1", "2": "2", "3": "3"
        }

    def speak(self, text):
        # print(f"{Fore.GREEN}🤖 Assistant:{Style.RESET_ALL} {text}")
        audio_path = self.sarvam.text_to_speech(text)
        if audio_path:
            sound = pygame.mixer.Sound(audio_path)
            channel = sound.play()
            while channel.get_busy():
                time.sleep(0.1)

    def get_voice_input(self):
        # Add a longer delay before listening to give the user more time to prepare
        time.sleep(2.5)
        return self.sarvam.speech_to_text()

    def confirm_choice(self, prompt="Say yes or no"):
        self.speak(prompt)
        reply = self.get_voice_input().lower()
        return any(word in reply for word in ["yes", "yeah", "sure", "okay", "ok", "y"])
