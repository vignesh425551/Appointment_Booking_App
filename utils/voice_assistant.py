import os
from typing import Optional, Dict
import pygame
import time

class VoiceAssistant:
    LANGUAGE_MAPPING = {
        "1": {"code": "en-IN", "speaker": "manisha", "name": "English"},
        "2": {"code": "hi-IN", "speaker": "manisha", "name": "Hindi"},
        "3": {"code": "te-IN", "speaker": "abhilash", "name": "Telugu"}
    }

    # Add number word mappings
    NUMBER_WORDS = {
        "one": "1", "1": "1", "first": "1",
        "two": "2", "2": "2", "second": "2",
        "three": "3", "3": "3", "third": "3"
    }

    # Add Telugu number word mappings for language selection
    TELUGU_NUMBER_WORDS = {
        "ఒకటి": "1",
        "రెండు": "2",
        "మూడు": "3",
        "1": "1",
        "2": "2",
        "3": "3"
    }

    # Add Hindi number word mappings for language selection
    HINDI_NUMBER_WORDS = {
        "एक": "1",
        "दो": "2",
        "तीन": "3",
        "1": "1",
        "2": "2",
        "3": "3"
    }

    def __init__(self, sarvam_handler):
        self.sarvam = sarvam_handler
        self.selected_language = None
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        pygame.mixer.set_num_channels(1)  # Use a single channel for voice

    def play_audio(self, audio_path: str) -> None:
        """
        Play the audio file using pygame
        """
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            # Wait for the audio to finish playing
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            # Clean up the audio file
            pygame.mixer.music.unload()
            os.remove(audio_path)
            # Add a small delay after speaking before listening
            time.sleep(1)
        except Exception as e:
            print(f"Error playing audio: {e}")

    def select_language(self) -> bool:
        """
        Handle language selection through voice, supporting Telugu number words and numerals
        """
        welcome_text = "Please select your language. Say one for English, two for Hindi, three for Telugu."
        # Use direct speak for language selection (not through logging system)
        print(f"🤖 Assistant: {welcome_text}")
        audio_path = self.sarvam.text_to_speech(welcome_text)
        if audio_path:
            self.play_audio(audio_path)
        
        while True:
            print("🎙️ Speak now...")
            response = self.sarvam.speech_to_text().strip().lower()
            print(f"You: {response}")
            # Clean the response to remove punctuation
            response_clean = response.replace('.', '').replace(',', '').replace('!', '').replace('?', '').strip()
            
            # Try to extract number from response (English or Telugu)
            number = None
            for word in response_clean.split():
                if word in self.NUMBER_WORDS:
                    number = self.NUMBER_WORDS[word]
                    break
                if word in self.TELUGU_NUMBER_WORDS:
                    number = self.TELUGU_NUMBER_WORDS[word]
                    break
                if word in self.HINDI_NUMBER_WORDS:
                    number = self.HINDI_NUMBER_WORDS[word]
                    break
            if number and number in self.LANGUAGE_MAPPING:
                self.selected_language = self.LANGUAGE_MAPPING[number]
                self.sarvam.language = self.selected_language
                # Only show confirmation once
                if number == "3":
                    confirmation = "ఎంచుకున్న భాష: తెలుగు"
                elif number == "2":
                    confirmation = "चयनित भाषा: हिंदी"
                else:
                    confirmation = f"Selected language: {self.selected_language['name']}"
                
                print(f"🤖 Assistant: {confirmation}")
                audio_path = self.sarvam.text_to_speech(confirmation)
                if audio_path:
                    self.play_audio(audio_path)
                return True
            else:
                error_msg = "I couldn't understand your language choice. Please say one, two, or three."
                print(f"🤖 Assistant: {error_msg}")
                audio_path = self.sarvam.text_to_speech(error_msg)
                if audio_path:
                    self.play_audio(audio_path)

    def speak(self, text: str) -> Optional[str]:
        """
        Convert text to speech using Sarvam TTS and play it
        """
        try:
            # Don't print here - let log_and_speak handle the printing
            audio_path = self.sarvam.text_to_speech(text)
            if audio_path:
                self.play_audio(audio_path)
                return audio_path
            return None
        except Exception as e:
            print(f"Error in text-to-speech: {e}")
            return None

    def listen(self) -> str:
        """
        Convert speech to text using Sarvam STT
        """
        try:
            print("🎙️ Speak now...")
            text = self.sarvam.speech_to_text()
            # Don't print user input here - let log_and_get_voice_input handle that
            return text
        except Exception as e:
            print(f"Error in speech-to-text: {e}")
            return "[ERROR: Could not process speech]"

    def get_voice_input(self, prompt: str = None) -> str:
        """
        Get voice input with optional prompt
        """
        if prompt:
            self.speak(prompt)
        return self.listen()

    def __del__(self):
        """
        Cleanup pygame mixer when the object is destroyed
        """
        try:
            pygame.mixer.quit()
        except:
            pass 