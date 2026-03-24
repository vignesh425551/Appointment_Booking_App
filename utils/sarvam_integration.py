import os
import requests
import uuid
import tempfile
from sarvamai import SarvamAI
from sarvamai.play import save
from dotenv import load_dotenv
import time

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
sarvam_client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

class SarvamHandler:
    def __init__(self, language_config=None):
        self.language = language_config or {
            "code": "en-IN",
            "speaker": "manisha"
        }
        # Only English, Hindi, Telugu supported
        if self.language["code"] not in ["en-IN", "hi-IN", "te-IN"]:
            self.language = {"code": "en-IN", "speaker": "manisha"}

    def speech_to_text(self):
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("🎙️ Speak now...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                # Increased timeout and phrase_time_limit for longer user input
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=8)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    f.write(audio.get_wav_data())
                    audio_path = f.name

                with open(audio_path, 'rb') as f:
                    files = {'file': ('audio.wav', f, 'audio/wav')}
                    data = {
                        'language_code': self.language['code'],
                        'model': 'saarika:v2',
                        'with_timestamps': 'false'
                    }
                    headers = {
                        "api-subscription-key": SARVAM_API_KEY,
                        "Accept": "application/json"
                    }
                    response = requests.post("https://api.sarvam.ai/speech-to-text", headers=headers, files=files, data=data)
                os.unlink(audio_path)
                if response.status_code == 200:
                    return response.json().get("transcript", "")
                else:
                    return "[ERROR: STT Failed]"
            except Exception as e:
                return f"[ERROR: {e}]"

    def text_to_speech(self, text):
        try:
            response = sarvam_client.text_to_speech.convert(
                text=text,
                target_language_code=self.language['code'],
                speaker=self.language['speaker'],
                pitch=0.0,
                pace=1.0,
                loudness=1.0,
                speech_sample_rate=22050,
                enable_preprocessing=False
            )
            temp_path = os.path.join(tempfile.gettempdir(), f"sarvam_tts_{uuid.uuid4().hex}.wav")
            save(response, temp_path)
            return temp_path
        except Exception as e:
            print(f"TTS Exception: {e}")
            # Return a static Telugu error message or None
            if self.language['code'] == "te-IN":
                return None  # Optionally, you could play a static error audio here
            return None

    def get_medical_advice(self, symptoms):
        return f"Based on the symptoms you described: '{symptoms}', it's advised to consult a specialist."

    def process_medical_query(self, text):
        return f"Thank you for sharing. Based on your input: '{text}', I recommend monitoring your symptoms closely."

    def validate_medical_condition(self, symptoms):
        if any(word in symptoms.lower() for word in ["chest pain", "shortness of breath", "fainting"]):
            return "This may require emergency attention. Please visit a nearby hospital immediately."
        return "This does not appear to be an emergency. Let's proceed with diagnosis."

    def infer_department(self, symptoms):
        if "eye" in symptoms.lower():
            return "Ophthalmology"
        elif "heart" in symptoms.lower():
            return "Cardiology"
        elif "skin" in symptoms.lower():
            return "Dermatology"
        return "General Medicine"

    def get_voice_input(self, prompt=None):
        if prompt:
            self.speak(prompt)
            time.sleep(0.5)  # Small delay after speaking
        return self.listen()

    def translate_to_telugu(self, text, source_language_code="en-IN"):
        """
        Translate the given text from the source language to Telugu using SarvamAI API.
        Always returns a string.
        """
        try:
            response = sarvam_client.text.translate(
                input=text,
                source_language_code=source_language_code,
                target_language_code="te-IN",
                model="sarvam-translate:v1"
            )
            
            # Try to extract the translated text directly
            translated_text = None
            
            # Method 1: Check if response has attributes
            if hasattr(response, 'translated_text'):
                translated_text = response.translated_text
            elif hasattr(response, 'output'):
                translated_text = response.output
            elif hasattr(response, 'text'):
                translated_text = response.text
            elif hasattr(response, 'content'):
                translated_text = response.content
            elif hasattr(response, 'result'):
                translated_text = response.result
            
            # Method 2: If it's a dict-like object
            if translated_text is None and isinstance(response, dict):
                translated_text = response.get('translated_text') or response.get('output') or response.get('text') or response.get('content') or response.get('result')
            
            # Method 3: If it's a string representation with metadata, extract only the text
            if translated_text is None:
                response_str = str(response)
                # Look for the actual translated text in the string representation
                if "translated_text='" in response_str:
                    start = response_str.find("translated_text='") + 16
                    end = response_str.find("'", start)
                    if end > start:
                        translated_text = response_str[start:end]
                elif "output='" in response_str:
                    start = response_str.find("output='") + 8
                    end = response_str.find("'", start)
                    if end > start:
                        translated_text = response_str[start:end]
            
            # Method 4: If it's already a string
            if translated_text is None and isinstance(response, str):
                translated_text = response
            
            # Return the extracted text or a fallback
            if translated_text:
                return str(translated_text)
            else:
                # If we can't extract the text, return a fallback message
                return "క్షమించండి, అనువాదంలో లోపం జరిగింది."
                
        except Exception as e:
            print(f"Translation Exception: {e}")
            return "క్షమించండి, అనువాదంలో లోపం జరిగింది."  # Sorry, there was a translation error.

    def translate_to_english(self, text, source_language_code="te-IN"):
        """
        Translate the given text from Telugu to English using SarvamAI API.
        Always returns a string.
        """
        try:
            response = sarvam_client.text.translate(
                input=text,
                source_language_code=source_language_code,
                target_language_code="en-IN",
                model="sarvam-translate:v1"
            )
            
            # Try to extract the translated text directly
            translated_text = None
            
            # Method 1: Check if response has attributes
            if hasattr(response, 'translated_text'):
                translated_text = response.translated_text
            elif hasattr(response, 'output'):
                translated_text = response.output
            elif hasattr(response, 'text'):
                translated_text = response.text
            elif hasattr(response, 'content'):
                translated_text = response.content
            elif hasattr(response, 'result'):
                translated_text = response.result
            
            # Method 2: If it's a dict-like object
            if translated_text is None and isinstance(response, dict):
                translated_text = response.get('translated_text') or response.get('output') or response.get('text') or response.get('content') or response.get('result')
            
            # Method 3: If it's a string representation with metadata, extract only the text
            if translated_text is None:
                response_str = str(response)
                # Look for the actual translated text in the string representation
                if "translated_text='" in response_str:
                    start = response_str.find("translated_text='") + 16
                    end = response_str.find("'", start)
                    if end > start:
                        translated_text = response_str[start:end]
                elif "output='" in response_str:
                    start = response_str.find("output='") + 8
                    end = response_str.find("'", start)
                    if end > start:
                        translated_text = response_str[start:end]
            
            # Method 4: If it's already a string
            if translated_text is None and isinstance(response, str):
                translated_text = response
            
            # Return the extracted text or a fallback
            if translated_text:
                return str(translated_text)
            else:
                # If we can't extract the text, return a fallback message
                return "Sorry, there was a translation error."
                
        except Exception as e:
            print(f"Translation Exception: {e}")
            return "Sorry, there was a translation error."

    def translate_to_hindi(self, text, source_language_code="en-IN"):
        """
        Translate the given text from the source language to Hindi using SarvamAI API.
        Always returns a string.
        """
        try:
            response = sarvam_client.text.translate(
                input=text,
                source_language_code=source_language_code,
                target_language_code="hi-IN",
                model="sarvam-translate:v1"
            )
            
            # Try to extract the translated text directly
            translated_text = None
            
            # Method 1: Check if response has attributes
            if hasattr(response, 'translated_text'):
                translated_text = response.translated_text
            elif hasattr(response, 'output'):
                translated_text = response.output
            elif hasattr(response, 'text'):
                translated_text = response.text
            elif hasattr(response, 'content'):
                translated_text = response.content
            elif hasattr(response, 'result'):
                translated_text = response.result
            
            # Method 2: If it's a dict-like object
            if translated_text is None and isinstance(response, dict):
                translated_text = response.get('translated_text') or response.get('output') or response.get('text') or response.get('content') or response.get('result')
            
            # Method 3: If it's a string representation with metadata, extract only the text
            if translated_text is None:
                response_str = str(response)
                # Look for the actual translated text in the string representation
                if "translated_text='" in response_str:
                    start = response_str.find("translated_text='") + 16
                    end = response_str.find("'", start)
                    if end > start:
                        translated_text = response_str[start:end]
                elif "output='" in response_str:
                    start = response_str.find("output='") + 8
                    end = response_str.find("'", start)
                    if end > start:
                        translated_text = response_str[start:end]
            
            # Method 4: If it's already a string
            if translated_text is None and isinstance(response, str):
                translated_text = response
            
            # Return the extracted text or a fallback
            if translated_text:
                return str(translated_text)
            else:
                # If we can't extract the text, return a fallback message
                return "क्षमा करें, अनुवाद में त्रुटि हुई।"
                
        except Exception as e:
            print(f"Translation Exception: {e}")
            return "क्षमा करें, अनुवाद में त्रुटि हुई।"  # Sorry, there was a translation error.
