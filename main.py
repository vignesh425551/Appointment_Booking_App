from flows.appointment_bot_flow import AppointmentFlow
from utils.voice_utils import VoiceAssistant
from utils.sarvam_integration import SarvamHandler
import os
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_LANGUAGES = {
    "1": {"name": "English", "code": "en-IN", "system_prompt": "You are a concise and helpful assistant.", "speaker": "manisha"},
    "2": {"name": "Hindi", "code": "hi-IN", "system_prompt": "आप एक संक्षिप्त और सहायक सहायक हैं।", "speaker": "manisha"},
    "3": {"name": "Telugu", "code": "te-IN", "system_prompt": "మీరు సహాయకుడు. ఊహా సమాధానాలు ఇవ్వవద్దు.", "speaker": "abhilash"},
}

def select_language_by_voice():
    sarvam = SarvamHandler()
    voice = VoiceAssistant(sarvam_handler=sarvam)
    voice.speak("Please select your language. Say one for English, two for Hindi, three for Telugu.")
    choice = voice.get_voice_input()
    for key, value in SUPPORTED_LANGUAGES.items():
        if key in choice or value['name'].lower() in choice.lower():
            return value
    return SUPPORTED_LANGUAGES["1"]

if __name__ == "__main__":
    # Only start the flow; do not select language here
    flow = AppointmentFlow()
    flow.kickoff()
