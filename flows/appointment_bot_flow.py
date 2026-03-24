from crewai.flow.flow import Flow, start
from dotenv import load_dotenv
import os
import litellm
import re
import json
from datetime import datetime
from utils.sarvam_integration import SarvamHandler
from utils.voice_assistant import VoiceAssistant
import time
import string
from db.models import User, Department, Doctor, Slot, Appointment
from db.session import SessionLocal
from utils.session_manager import create_session, log_message


class AppointmentFlow(Flow):
    def __init__(self, language_config=None):
        super().__init__()
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found.")
        self.messages = []
        self.language_config = language_config
        self.sarvam = SarvamHandler(language_config=self.language_config)
        self.voice = VoiceAssistant(sarvam_handler=self.sarvam)
        self.user_symptoms = ""
        self.session_data = {}  # Store session-specific data
        self.current_appointment = {}  # Store current appointment details
        litellm.api_key = self.api_key
        litellm.api_base = "https://api.groq.com/openai/v1"
        self.db = SessionLocal()  # Add DB session
        self.user_id = None  # Will be set after login
        self.NUMBER_WORDS = {
            "one": "1", "two": "2", "three": "3"
        }
        self.NUMBER_WORDS_TE = {
            "వన్": "1",
            "టూ": "2",
            "త్రి": "3",
            "ఒకటి": "1",
            "రెండు": "2",
            "మూడు": "3",
            "1": "1",
            "2": "2",
            "3": "3"
        }
        self.NUMBER_WORDS_HI = {
            "एक": "1",
            "दो": "2",
            "तीन": "3",
            "1": "1",
            "2": "2",
            "3": "3"
        }
        # Static messages for English and Telugu
        self.static_messages = {
            "en": {
                "greeting": "Hello! I'm here to assist you with your health needs.",
                "choose_option": "Please choose an option. Say one if you already know which department to consult and want to directly book an appointment. Say two if you're not sure what's wrong and want to describe your symptoms.",
                "invalid_input": "Invalid input. Please restart the bot and choose a valid option.",
                "describe_symptoms": "Could you briefly describe what you're experiencing?",
                "schedule_appointment": "Would you like me to help you schedule an appointment?",
                "declined_appointment": "Got it. Reach out if you need any help. Take care!",
                "select_department": "Please tell me which department you'd like to book an appointment with.",
                "no_doctors": "No doctors available in {department}. Please try another department.",
                "no_doctors_final": "Sorry, no doctors available after several attempts. Please restart the process.",
                "select_doctor": "Please select a doctor by saying their name.",
                "doctor_not_found": "I could not identify the doctor you selected. Please try again.",
                "doctor_not_found_final": "Sorry, I couldn't identify the doctor after several attempts. Please restart the process.",
                "selected_doctor": "You have selected {doctor}.",
                "lets_book": "Let's book an appointment with {doctor}.",
                "no_slots": "Sorry, Dr. {doctor} has no available appointments.",
                "available_slots": "Here are the available slots:",
                "on_date": "On {date}, {doctor} is available at {times}.",
                "state_preferred": "Please state your preferred date and time.",
                "cancel_booking": "Okay, cancelling the booking process.",
                "booking_trouble": "I'm sorry, I couldn't find that slot. Please try again.",
                "booking_trouble_final": "I'm still having trouble understanding. Let's try booking again from the start.",
                "confirm_booking": "Just to confirm, you want to book an appointment with {doctor} on {date} at {time}. Is that correct?",
                "booking_confirmed": "Your appointment with {doctor} on {date} at {time} is confirmed.",
                "my_mistake": "My mistake. Let's try booking that again.",
                "other_questions": "Do you have any other questions I can help you with?",
                "thank_you": "Thank you for using our service. Wishing you good health!",
                "tell_question": "Please tell me your question.",
                "not_provide_diagnosis": "I'm not able to provide a diagnosis or solution. This bot is designed to help you collect information for your healthcare provider.",
                "not_provide_topic": "I'm sorry, but this bot cannot provide information on that topic. Please ask a medical question related to your appointment or symptoms.",
                "didnt_catch": "I didn't catch that. Do you have any other questions I can help you with? Please say yes or no."
            },
            "hi": {
                "greeting": "नमस्ते! मैं आपकी स्वास्थ्य संबंधी जरूरतों में मदद करने के लिए यहां हूं।",
                "choose_option": "कृपया एक विकल्प चुनें। एक कहें अगर आप पहले से जानते हैं कि किस विभाग से परामर्श लेना है और सीधे अपॉइंटमेंट बुक करना चाहते हैं। दो कहें अगर आपको नहीं पता कि क्या गलत है और आप अपने लक्षणों का वर्णन करना चाहते हैं।",
                "invalid_input": "अमान्य इनपुट। कृपया बॉट को पुनः प्रारंभ करें और एक वैध विकल्प चुनें।",
                "describe_symptoms": "क्या आप संक्षेप में बता सकते हैं कि आप क्या अनुभव कर रहे हैं?",
                "schedule_appointment": "क्या आप चाहते हैं कि मैं आपको अपॉइंटमेंट शेड्यूल करने में मदद करूं?",
                "declined_appointment": "ठीक है। अगर आपको कोई मदद चाहिए तो संपर्क करें। ध्यान रखें!",
                "select_department": "कृपया बताएं कि आप किस विभाग में अपॉइंटमेंट बुक करना चाहते हैं।",
                "no_doctors": "{department} विभाग में कोई डॉक्टर उपलब्ध नहीं है। कृपया दूसरे विभाग को आज़माएं।",
                "no_doctors_final": "क्षमा करें, कई प्रयासों के बाद भी कोई डॉक्टर उपलब्ध नहीं है। कृपया प्रक्रिया को पुनः प्रारंभ करें।",
                "select_doctor": "कृपया डॉक्टर का नाम कहकर चुनें।",
                "doctor_not_found": "मैं आपके द्वारा चुने गए डॉक्टर की पहचान नहीं कर पाया। कृपया पुनः प्रयास करें।",
                "doctor_not_found_final": "क्षमा करें, कई प्रयासों के बाद भी मैं डॉक्टर की पहचान नहीं कर पाया। कृपया प्रक्रिया को పునఃప్రారంభించండి.",
                "selected_doctor": "आपने {doctor} को चुना है।",
                "lets_book": "चलिए {doctor} के साथ अपॉइंटमेंट बुक करते हैं।",
                "no_slots": "क्षमा करें, डॉक्टर {doctor} के पास कोई उपलब्ध अपॉइंटमेंट नहीं है।",
                "available_slots": "यहां उपलब्ध समय स्लॉट हैं:",
                "on_date": "{date} को {doctor} {times} पर उपलब्ध हैं।",
                "state_preferred": "कृपया अपनी पसंदीदा तारीख और समय बताएं।",
                "cancel_booking": "ठीक है, बुकिंग प्रक्रिया रद्द कर रहा हूं।",
                "booking_trouble": "क्षमा करें, నాకు ఆ స్లాట్‌ను కనుగొనలేకపోయాను. దయచేసి మళ్లీ ప్రయత్నించండి.",
                "booking_trouble_final": "మళ్లీ ప్రయత్నించండి.",
                "confirm_booking": "बस पुष्टि के लिए, आप {doctor} के साथ {date} को {time} पर अपॉइंटमेंट बुक करना चाहते हैं। क्या यह सही है?",
                "booking_confirmed": "आपका {doctor} के साथ {date} को {time} पर अपॉइंटमेंट पुष्टि हो गया है।",
                "my_mistake": "मेरी गलती। चलिए फिर से बुकिंग करने की कोशिश करते हैं।",
                "other_questions": "क्या आपके पास कोई अन्य प्रश्न हैं जिनमें मैं आपकी मदद कर सकता हूं?",
                "thank_you": "हमारी सेवा का उपयोग करने के लिए धन्यवाद। आपकी अच्छी सेहत की कामना करता हूं!",
                "tell_question": "कृपया मुझे अपना प्रश्न बताएं।",
                "not_provide_diagnosis": "मैं निदान या समाधान प्रदान नहीं कर सकता। यह बॉट आपके स्वास्थ्य सेवा प्रदाता के लिए जानकारी एकत्र करने में मदद करने के लिए डिज़ाइन किया गया है।",
                "not_provide_topic": "क्षमा करें, लेकिन यह बॉट उस विषय पर जानकारी प्रदान नहीं कर सकता। कृपया अपने अपॉइंटमेंट या लक्षणों से संबंधित चिकित्सीय प्रश्न पूछें।",
                "didnt_catch": "मैंने वह नहीं पकड़ा। क्या आपके पास कोई अन्य प्रश्न हैं जिनमें मैं आपकी मदद कर सकता हूं? कृपया हां या नहीं कहें।"
            },
            "te": {
                "greeting": "హలో! నేను మీ ఆరోగ్య అవసరాలకు సహాయం చేయడానికి ఇక్కడ ఉన్నాను.",
                "choose_option": "దయచేసి ఒక ఎంపికను ఎంచుకోండి. మీరు ఏ విభాగాన్ని సంప్రదించాలో ఇప్పటికే తెలుసు అయితే ఒకటి చెప్పండి మరియు నేరుగా అపాయింట్మెంట్ బుక్ చేయండి. మీకు ఏమైంది తెలియకపోతే మరియు మీ లక్షణాలను వివరించాలనుకుంటే రెండు చెప్పండి.",
                "invalid_input": "చెల్లని ఇన్‌పుట్. దయచేసి బాట్‌ను మళ్లీ ప్రారంభించి సరైన ఎంపికను ఎంచుకోండి.",
                "describe_symptoms": "మీరు అనుభవిస్తున్నదాన్ని సంక్షిప్తంగా వివరించగలరా?",
                "schedule_appointment": "మీకు అపాయింట్మెంట్ షెడ్యూల్ చేయడంలో నేను సహాయపడాలా?",
                "declined_appointment": "సరే. మీకు ఏదైనా సహాయం అవసరమైతే సంప్రదించండి. జాగ్రత్త!",
                "select_department": "దయచేసి మీరు ఏ విభాగానికి అపాయింట్మెంట్ బుక్ చేయాలనుకుంటున్నారో చెప్పండి.",
                "no_doctors": "{department} విభాగంలో డాక్టర్లు అందుబాటులో లేరు. దయచేసి మరో విభాగాన్ని ప్రయత్నించండి.",
                "no_doctors_final": "క్షమించండి, అనేక ప్రయత్నాల తర్వాత కూడా డాక్టర్లు అందుబాటులో లేరు. దయచేసి ప్రక్రియను మళ్లీ ప్రారంభించండి.",
                "select_doctor": "దయచేసి డాక్టర్ పేరును చెప్పి ఎంపిక చేయండి.",
                "doctor_not_found": "మీరు ఎంపిక చేసిన డాక్టర్‌ను గుర్తించలేకపోయాను. దయచేసి మళ్లీ ప్రయత్నించండి.",
                "doctor_not_found_final": "క్షమించండి, అనేక ప్రయత్నాల తర్వాత కూడా డాక్టర్‌ను గుర్తించలేకపోయాను. దయచేసి ప్రక్రియను మళ్లీ ప్రారంభించండి.",
                "selected_doctor": "మీరు {doctor} ను ఎంపిక చేసుకున్నారు.",
                "lets_book": "{doctor} తో అపాయింట్మెంట్ బుక్ చేద్దాం.",
                "no_slots": "క్షమించండి, డాక్టర్ {doctor} కు అందుబాటులో అపాయింట్మెంట్లు లేవు.",
                "available_slots": "ఇవి అందుబాటులో ఉన్న స్లాట్లు:",
                "on_date": "{date} న {doctor} గారు {times} మీకు అందుబాటులో ఉంటారు.",
                "state_preferred": "దయచేసి మీకు ఇష్టమైన తేదీ మరియు సమయాన్ని చెప్పండి.",
                "cancel_booking": "సరే, బుకింగ్ ప్రక్రియను రద్దు చేస్తున్నాను.",
                "booking_trouble": "క్షమించండి, ఆ స్లాట్‌ను కనుగొనలేకపోయాను. దయచేసి మళ్లీ ప్రయత్నించండి.",
                "booking_trouble_final": "ఇంకా అర్థం చేసుకోవడంలో ఇబ్బంది పడుతున్నాను. మళ్లీ ప్రారంభిద్దాం.",
                "confirm_booking": "దయచేసి నిర్ధారించండి, మీరు {doctor} గారితో {date}న {time}కు అపాయింట్మెంట్ బుక్ చేయాలనుకుంటున్నారా?",
                "booking_confirmed": "మీరు {doctor} గారితో {date}న {time}కు అపాయింట్మెంట్ బుక్ చేసుకున్నారు.",
                "my_mistake": "నా తప్పు. మళ్లీ బుకింగ్ ప్రయత్నిద్దాం.",
                "other_questions": "మీకు ఇంకేమైనా ప్రశ్నలు ఉన్నాయా? నేను సహాయపడగలనా?",
                "thank_you": "మా సేవను ఉపయోగించినందుకు ధన్యవాదాలు. మీకు మంచి ఆరోగ్యం కలగాలని కోరుకుంటున్నాం!",
                "tell_question": "దయచేసి మీ ప్రశ్నను చెప్పండి.",
                "not_provide_diagnosis": "నేను నిర్ధారణ లేదా పరిష్కారం ఇవ్వలేను. ఈ బాట్ మీ ఆరోగ్య సేవాదారుని కోసం సమాచారం సేకరించడానికే రూపొందించబడింది.",
                "not_provide_topic": "క్షమించండి, ఈ విషయం మీద సమాచారం ఇవ్వలేను. దయచేసి మీ అపాయింట్మెంట్ లేదా లక్షణాలకు సంబంధించిన వైద్య ప్రశ్నను అడగండి.",
                "didnt_catch": "నేను అర్థం చేసుకోలేకపోయాను. మీకు ఇంకేమైనా ప్రశ్నలు ఉన్నాయా? దయచేసి అవును లేదా కాదు అని చెప్పండి."
            }
        }

    def get_lang_key(self):
        if self.language_config and isinstance(self.language_config, dict) and self.language_config.get("code") == "te-IN":
            return "te"
        elif self.language_config and isinstance(self.language_config, dict) and self.language_config.get("code") == "hi-IN":
            return "hi"
        return "en"

    def ask_ai(self, prompt):
        system_message = {
            "role": "system",
            "content": (
                "You are a voice-enabled healthcare assistant.\n\n"
                "For every user question, respond in JSON with:\n"
                "- spoken_text: Short, 1–2 sentence summary suitable for speech\n"
                "- display_text: Full, detailed response to show in chat\n"
                "spoken_text should summarize the most important part of display_text clearly and naturally."
            )
        }
        self.messages.append({"role": "user", "content": prompt})
        try:
            response = litellm.completion(
                model="groq/llama-3.1-8b-instant",
                api_key=self.api_key,
                api_base="https://api.groq.com/openai/v1",
                messages=[system_message] + self.messages,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            reply = response["choices"][0]["message"]["content"].strip()
            
            # Parse JSON response
            try:
                import json
                response_data = json.loads(reply)
                spoken_text = response_data.get("spoken_text", "")
                display_text = response_data.get("display_text", "")
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                spoken_text = reply
                display_text = reply
            
            self.messages.append({"role": "assistant", "content": display_text})
            
            # Translate to Telugu if needed
            if self.language_config and self.language_config.get("code") == "te-IN":
                translated_spoken = self.sarvam.translate_to_telugu(spoken_text)
                if isinstance(translated_spoken, str):
                    return {"spoken_text": translated_spoken, "display_text": display_text}
                else:
                    return {"spoken_text": spoken_text, "display_text": display_text}
            # Translate to Hindi if needed
            elif self.language_config and self.language_config.get("code") == "hi-IN":
                translated_spoken = self.sarvam.translate_to_hindi(spoken_text)
                if isinstance(translated_spoken, str):
                    return {"spoken_text": translated_spoken, "display_text": display_text}
                else:
                    return {"spoken_text": spoken_text, "display_text": display_text}
            
            return {"spoken_text": spoken_text, "display_text": display_text}
        except Exception as e:
            print(f"❌ Error: {e}")
            error_response = "I'm having trouble responding right now."
            if self.language_config and self.language_config.get("code") == "te-IN":
                error_response = self.static_messages[self.get_lang_key()]["not_provide_topic"]
            elif self.language_config and self.language_config.get("code") == "hi-IN":
                error_response = self.static_messages[self.get_lang_key()]["not_provide_topic"]
            return {"spoken_text": error_response, "display_text": error_response}

    def infer_department_from_llm(self, symptoms: str) -> str:
        # First check if we have a severity assessment
        assessment = self.assess_symptom_severity(symptoms)
        if assessment["department"] != "General Medicine":
            return assessment["department"]
        
        prompt = f"""The user described their health issue as: "{symptoms}". 

Based on this description, identify the most relevant medical department using proper medical reasoning:
- Chest pain, heart issues → Cardiology
- Stomach, digestive issues → Gastroenterology  
- Head, brain, nerve issues → Neurology
- Bone, joint, muscle issues → Orthopedics
- Skin issues → Dermatology
- Children's health → Pediatrics
- Ear, nose, throat → ENT
- Eye issues → Ophthalmology
- Urinary issues → Urology
- Dental issues → Dentistry
- General health, multiple symptoms → General Medicine

Choose only from: Cardiology, Gastroenterology, Neurology, Orthopedics, Dermatology, Pediatrics, ENT, Ophthalmology, Urology, Dentistry, General Medicine.

Respond with only the department name (in English)."""
        try:
            response = litellm.completion(
                model="groq/llama-3.1-8b-instant",
                api_key=self.api_key,
                api_base="https://api.groq.com/openai/v1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return response["choices"][0]["message"]["content"].strip().replace(".", "").title()
        except Exception as e:
            print(f"❌ Department inference error: {e}")
            return "General Medicine"

    def generate_medical_advice(self, symptoms: str) -> str:
        """Generate AI medical advice when user specifically requests it"""
        prompt = f"""The patient has requested advice. Based on the symptoms: '{symptoms}', provide AI-generated guidance clearly, in a friendly and supportive tone. Add a disclaimer that this is not a medical diagnosis.

Respond ONLY in JSON with:
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned."""

        try:
            response = litellm.completion(
                model="groq/llama-3.1-8b-instant",
                api_key=self.api_key,
                api_base="https://api.groq.com/openai/v1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"❌ Medical advice generation error: {e}")
            return "I'm unable to provide medical advice at the moment. Please consult with a healthcare professional."

    def assess_symptom_severity(self, symptoms: str) -> dict:
        """Assess symptom severity and provide emergency guidance"""
        emergency_symptoms = {
            "chest pain": {
                "severity": "high",
                "emergency_indicators": ["radiating to arm/back", "shortness of breath", "sweating", "nausea", "weakness in arm", "difficulty breathing"],
                "emergency_message": "Chest pain can be a medical emergency. If you experience severe chest pain, shortness of breath, or pain radiating to your arm, please call emergency services immediately.",
                "department": "Cardiology"
            },
            "headache": {
                "severity": "medium",
                "emergency_indicators": ["sudden severe", "with confusion", "with vision changes", "worse than ever"],
                "emergency_message": "If you experience a sudden, severe headache or headache with confusion or vision changes, seek immediate medical attention.",
                "department": "Neurology"
            },
            "shortness of breath": {
                "severity": "high",
                "emergency_indicators": ["sudden onset", "with chest pain", "with blue lips", "severe"],
                "emergency_message": "Sudden shortness of breath can be a medical emergency. If severe, call emergency services immediately.",
                "department": "Cardiology"
            }
        }
        
        symptoms_lower = symptoms.lower()
        assessment = {
            "severity": "low",
            "emergency_message": None,
            "department": "General Medicine",
            "requires_immediate_attention": False
        }
        
        for symptom, details in emergency_symptoms.items():
            if symptom in symptoms_lower:
                assessment["severity"] = details["severity"]
                assessment["department"] = details["department"]
                assessment["emergency_message"] = details["emergency_message"]
                
                # Check for emergency indicators
                for indicator in details["emergency_indicators"]:
                    if indicator in symptoms_lower:
                        assessment["requires_immediate_attention"] = True
                        break
                
                # If no specific indicators found but symptom is high severity, still flag
                if details["severity"] == "high" and not assessment["requires_immediate_attention"]:
                    assessment["requires_immediate_attention"] = True
                break
                
        return assessment

    def medical_triage(self, symptoms: str) -> str:
        """Perform medical triage and provide appropriate guidance"""
        assessment = self.assess_symptom_severity(symptoms)
        
        if assessment["requires_immediate_attention"]:
            return f"EMERGENCY ALERT: {assessment['emergency_message']} Please call emergency services immediately if symptoms are severe or worsening."
        
        if assessment["emergency_message"]:
            return f"IMPORTANT: {assessment['emergency_message']} Please monitor your symptoms and seek immediate care if they worsen."
        
        return None  # No emergency concerns

    def correlate_symptoms(self, primary_symptoms: str, new_symptoms: str) -> str:
        """Correlate multiple symptoms and provide insights"""
        correlation_prompt = f"""
        Primary symptoms: {primary_symptoms}
        New symptoms: {new_symptoms}
        
        Analyze if these symptoms might be related:
        1. Could they be part of the same condition?
        2. What might be the underlying cause?
        3. What additional information would help?
        
        Provide a brief analysis (2-3 sentences) focusing on potential connections.

        Respond ONLY in JSON with:
        - spoken_text: Short, 1–2 sentence summary suitable for speech
        - display_text: Full, detailed response to show in chat

        Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned."""
        
        try:
            response = litellm.completion(
                model="groq/llama-3.1-8b-instant",
                api_key=self.api_key,
                api_base="https://api.groq.com/openai/v1",
                messages=[{"role": "user", "content": correlation_prompt}],
                temperature=0.3
            )
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"❌ Symptom correlation error: {e}")
            return "These symptoms may be related. Please discuss all your symptoms with your healthcare provider."

    def handle_multiple_symptoms(self, new_symptoms: str) -> str:
        """Correlate when user mentions additional symptoms"""
        if hasattr(self, 'user_symptoms') and self.user_symptoms:
            correlation = self.correlate_symptoms(self.user_symptoms, new_symptoms)
            return f"Thank you for sharing that you're experiencing {new_symptoms}. {correlation} Please be sure to mention both your original symptoms and this new symptom to your doctor during your appointment."
        else:
            return f"Thank you for sharing that you're experiencing {new_symptoms}. Please provide more details about the timing, severity, and any other symptoms you're experiencing."

    def login(self):
        while True:
            phone = input("Enter your phone number to log in: ").strip()
            user = self.db.query(User).filter_by(phone=phone).first()
            if user:
                self.user_id = user.id
                print(f"Welcome, {user.name}!")
                return
            else:
                print("No user found with that phone number. Please try again.")

    @start()
    def run_flow(self):
        self.login()
        # Create a new session for this conversation
        self.session_id = create_session(self.user_id)
        print(f"Session started. Session ID: {self.session_id}")
        
        # Try to load existing session data
        if self.load_session_data(self.session_id):
            print("Session data recovered successfully.")
        
        # No further session details printed in terminal
        if not self.voice.select_language():
            return "language selection failed"
        self.language_config = self.voice.selected_language
        lang = self.get_lang_key()
        
        # Save session data before proceeding
        self.save_session_data()
        
        if lang == "te":
            return self.run_flow_te()
        elif lang == "hi":
            return self.run_flow_hi()
        else:
            return self.run_flow_en()

    # Example: log all assistant and user messages
    def log_and_speak(self, message):
        # Handle dual-response format (only for LLM-generated responses)
        if isinstance(message, dict) and "spoken_text" in message and "display_text" in message:
            # Print both spoken and display text with prefixes FIRST
            print(f"🎤 Spoken: {message['spoken_text']}")
            print(f"📄 Display: {message['display_text']}")
            # Log the display text for conversation history
            log_message(self.session_id, f"Assistant: {message['display_text']}")
            # Speak only the spoken text
            self.voice.speak(message['spoken_text'])
        else:
            # Print static message FIRST
            print(f"🤖 Assistant: {message}")
            log_message(self.session_id, f"Assistant: {message}")
            self.voice.speak(message)

    def log_and_get_voice_input(self, prompt=None):
        if prompt:
            self.log_and_speak(prompt)
        user_input = self.voice.get_voice_input()
        log_message(self.session_id, f"User: {user_input}")
        print(f"🎙️ You: {user_input}")  # <-- Add this line to show user's response in terminal
        return user_input

    def run_flow_en(self):
        # Only speak language selection once
        self.log_and_speak(self.static_messages["en"]["greeting"])
        self.log_and_speak(self.static_messages["en"]["choose_option"])
        option = self.log_and_get_voice_input().strip().lower()
        
        # More flexible input validation
        if any(word in option for word in ["one", "1", "first", "direct", "know", "department"]):
            result = self.direct_booking_flow_en()
            if result == "ended":
                return
            return result
        elif any(word in option for word in ["two", "2", "second", "symptoms", "don't know", "not sure", "help"]):
            result = self.symptom_diagnosis_flow_en()
            if result == "ended":
                return
            return result
        else:
            # Provide helpful guidance instead of just saying invalid
            self.log_and_speak("I didn't catch that clearly. Let me explain your options again:")
            self.log_and_speak("Say 'one' or 'direct booking' if you know which department you need.")
            self.log_and_speak("Say 'two' or 'symptoms' if you want to describe your symptoms and get help choosing the right department.")
            return self.run_flow_en()  # Recursive call to try again

    def run_flow_te(self):
        self.log_and_speak(self.static_messages["te"]["greeting"])
        self.log_and_speak(self.static_messages["te"]["choose_option"])
        option = self.log_and_get_voice_input().strip().lower()
        option = self.NUMBER_WORDS_TE.get(option, option)
        if option == "1":
            result = self.direct_booking_flow_te()
            if result == "ended":
                return
            return result
        elif option == "2":
            result = self.symptom_diagnosis_flow_te()
            if result == "ended":
                return
            return result
        else:
            self.log_and_speak(self.static_messages["te"]["invalid_input"])
            return "invalid input"

    def run_flow_hi(self):
        self.log_and_speak(self.static_messages["hi"]["greeting"])
        self.log_and_speak(self.static_messages["hi"]["choose_option"])
        option = self.log_and_get_voice_input().strip().lower()
        option = self.NUMBER_WORDS_HI.get(option, option)
        if option == "1":
            result = self.direct_booking_flow_hi()
            if result == "ended":
                return
            return result
        elif option == "2":
            result = self.symptom_diagnosis_flow_hi()
            if result == "ended":
                return
            return result
        else:
            self.log_and_speak(self.static_messages["hi"]["invalid_input"])
            return "invalid input"

    # English flows (no translation)
    def direct_booking_flow_en(self):
        self.log_and_speak(self.static_messages["en"]["select_department"])
        department = self.log_and_get_voice_input().strip().title()
        self.user_symptoms = department
        result = self.offer_appointment(direct=True)
        if result == "ended":
            return
        if result == "appointment confirmed":
            # After confirmation, handle follow-up queries
            followup_result = self.handle_followup_queries()
            if followup_result == "ended":
                return
            return followup_result
        return result

    def direct_booking_flow_te(self):
        self.log_and_speak(self.static_messages["te"]["select_department"])
        department_input = self.log_and_get_voice_input().strip()
        department = self.infer_department_from_llm(department_input)
        self.user_symptoms = department
        result = self.offer_appointment(direct=True)
        if result == "ended":
            return
        if result == "appointment confirmed":
            followup_result = self.handle_followup_queries()
            if followup_result == "ended":
                return
            return followup_result
        return result

    def direct_booking_flow_hi(self):
        self.log_and_speak(self.static_messages["hi"]["select_department"])
        department_input = self.log_and_get_voice_input().strip()
        department = self.infer_department_from_llm(department_input)
        self.user_symptoms = department
        result = self.offer_appointment(direct=True)
        if result == "ended":
            return
        if result == "appointment confirmed":
            followup_result = self.handle_followup_queries()
            if followup_result == "ended":
                return
            return followup_result
        return result

    def symptom_diagnosis_flow_en(self):
        self.log_and_speak(self.static_messages["en"]["describe_symptoms"])
        user_symptoms = self.log_and_get_voice_input()
        self.user_symptoms = user_symptoms
        self.messages.append({"role": "user", "content": user_symptoms})

        # Collect follow-up answers
        followup_answers = []
        for _ in range(4):  # or until you decide enough info is collected
            followup_prompt = f"""
User reported: '{self.user_symptoms}'
Based on these symptoms, ask ONE critical follow-up question to assess:
1. Symptom severity (1-10 scale)
2. Duration of symptoms
3. Associated symptoms
4. Risk factors (age, medical history)
5. Emergency indicators

Ask the most important question first. Keep it under 15 words.

Respond ONLY in JSON with:
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned.
"""
            followup_response = self.ask_ai(followup_prompt)
            self.log_and_speak(followup_response)
            answer = self.log_and_get_voice_input()
            followup_answers.append(answer)
            # Optionally, break if LLM says "no more questions" or similar

        # Now, after all symptom collection, perform triage
        all_symptoms = f"{self.user_symptoms}. " + " ".join(followup_answers)
        triage_prompt = f"""
You are a medical triage assistant. Based on the following symptoms and answers, classify the case as one of:
- self_care (mild, can be managed at home)
- appointment_needed (moderate, needs doctor visit)
- emergency (potentially life-threatening)

Symptoms and answers: "{all_symptoms}"

Respond ONLY in JSON with:
- triage_level: self_care, appointment_needed, or emergency
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat
- suggested_actions: List of suggested actions for the user (e.g., ["Set Reminder", "Book Appointment Anyway", "Read More Tips"])

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned.
"""
        triage_result = self.ask_llm_json(triage_prompt)
        self.save_conversation_step(triage_result)
        self.log_and_speak(triage_result)

        # Show suggested actions if present
        actions = triage_result.get("suggested_actions", [])
        if actions:
            actions_str = ", ".join(actions)
            self.log_and_speak(f"Suggested actions: {actions_str}")

        triage_level = triage_result.get("triage_level", "")
        if triage_level == "self_care":
            self.log_and_speak("What would you like to do? You can say: " + ", ".join(actions))
            choice = self.log_and_get_voice_input().strip().lower()
            if "reminder" in choice:
                self.log_and_speak("Reminder set. We'll check in after 3 days.")
                return "ended"
            elif "book" in choice or "appointment" in choice:
                result = self.offer_appointment()
                if result == "ended":
                    return "ended"
                if result == "appointment confirmed":
                    return self.handle_followup_queries()
                return result
            else:
                self.log_and_speak("Take care! Let us know if you need anything else.")
                return "ended"
        elif triage_level == "appointment_needed":
            result = self.offer_appointment()
            if result == "ended":
                return "ended"
            if result == "appointment confirmed":
                return self.handle_followup_queries()
            return result
        elif triage_level == "emergency":
            self.log_and_speak("This may be an emergency. Please seek immediate medical attention.")
            self.log_and_speak("Would you also like to book an appointment as a backup? Please say yes or no.")
            choice = self.log_and_get_voice_input().strip().lower()
            if "yes" in choice:
                result = self.offer_appointment()
                if result == "ended":
                    return "ended"
                if result == "appointment confirmed":
                    return self.handle_followup_queries()
                return result
            else:
                self.log_and_speak("Take care! If you need anything else, let us know.")
                return "ended"

    # Telugu flows (with translation)
    def symptom_diagnosis_flow_te(self):
        self.log_and_speak(self.static_messages["te"]["describe_symptoms"])
        user_symptoms_te = self.log_and_get_voice_input()
        user_symptoms_en = self.sarvam.translate_to_english(user_symptoms_te)
        self.user_symptoms = user_symptoms_en
        self.messages.append({"role": "user", "content": user_symptoms_en})

        followup_answers = []
        for _ in range(4):
            followup_prompt = f"""User reported: '{self.user_symptoms}'
Based on these symptoms, ask ONE critical follow-up question to assess:
1. Symptom severity (1-10 scale)
2. Duration of symptoms
3. Associated symptoms
4. Risk factors (age, medical history)
5. Emergency indicators

Ask the most important question first. Keep it under 15 words.

Respond ONLY in JSON with:
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned."""
            followup_response_te = self.ask_ai(followup_prompt)
            self.log_and_speak(followup_response_te)
            user_input_te = self.log_and_get_voice_input()
            user_input_en = self.sarvam.translate_to_english(user_input_te)
            followup_answers.append(user_input_en)
            self.messages.append({"role": "user", "content": user_input_en})

        all_symptoms = f"{self.user_symptoms}. " + " ".join(followup_answers)
        triage_prompt = f"""
You are a medical triage assistant. Based on the following symptoms and answers, classify the case as one of:
- self_care (mild, can be managed at home)
- appointment_needed (moderate, needs doctor visit)
- emergency (potentially life-threatening)

Symptoms and answers: "{all_symptoms}"

Respond ONLY in JSON with:
- triage_level: self_care, appointment_needed, or emergency
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat
- suggested_actions: List of suggested actions for the user (e.g., ["Set Reminder", "Book Appointment Anyway", "Read More Tips"])

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned.
"""
        triage_result = self.ask_llm_json(triage_prompt)
        self.save_conversation_step(triage_result)
        self.log_and_speak(triage_result)

        actions = triage_result.get("suggested_actions", [])
        if actions:
            actions_str = ", ".join(actions)
            self.log_and_speak(f"Suggested actions: {actions_str}")

        triage_level = triage_result.get("triage_level", "")
        if triage_level == "self_care":
            self.log_and_speak("What would you like to do? You can say: " + ", ".join(actions))
            choice = self.log_and_get_voice_input().strip().lower()
            if "reminder" in choice:
                self.log_and_speak("Reminder set. We'll check in after 3 days.")
                return "ended"
            elif "book" in choice or "appointment" in choice:
                result = self.offer_appointment()
                if result == "ended":
                    return "ended"
                if result == "appointment_confirmed":
                    return self.handle_followup_queries()
                return result
            else:
                self.log_and_speak("Take care! Let us know if you need anything else.")
                return "ended"
        elif triage_level == "appointment_needed":
            result = self.offer_appointment()
            if result == "ended":
                return "ended"
            if result == "appointment_confirmed":
                return self.handle_followup_queries()
            return result
        elif triage_level == "emergency":
            self.log_and_speak("ఇది అత్యవసర పరిస్థితి కావచ్చు. దయచేసి వెంటనే వైద్య సహాయం పొందండి.")
            self.log_and_speak("బ్యాకప్‌గా అపాయింట్మెంట్ బుక్ చేయాలనుకుంటున్నారా? అవును లేదా కాదు అని చెప్పండి.")
            choice = self.log_and_get_voice_input().strip().lower()
            if "అవును" in choice or "yes" in choice:
                result = self.offer_appointment()
                if result == "ended":
                    return "ended"
                if result == "appointment confirmed":
                    return self.handle_followup_queries()
                return result
            else:
                self.log_and_speak("జాగ్రత్త! మీకు మరేదైనా అవసరం ఉంటే మాకు తెలియజేయండి.")
                return "ended"

    # Hindi flows (with translation)
    def symptom_diagnosis_flow_hi(self):
        self.log_and_speak(self.static_messages["hi"]["describe_symptoms"])
        user_symptoms_hi = self.log_and_get_voice_input()
        user_symptoms_en = self.sarvam.translate_to_english(user_symptoms_hi, source_language_code="hi-IN")
        self.user_symptoms = user_symptoms_en
        self.messages.append({"role": "user", "content": user_symptoms_en})

        followup_answers = []
        for _ in range(4):
            followup_prompt = f"""User reported: '{self.user_symptoms}'
Based on these symptoms, ask ONE critical follow-up question to assess:
1. Symptom severity (1-10 scale)
2. Duration of symptoms
3. Associated symptoms
4. Risk factors (age, medical history)
5. Emergency indicators

Ask the most important question first. Keep it under 15 words.

Respond ONLY in JSON with:
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned."""
            followup_response_hi = self.ask_ai(followup_prompt)
            self.log_and_speak(followup_response_hi)
            user_input_hi = self.log_and_get_voice_input()
            user_input_en = self.sarvam.translate_to_english(user_input_hi, source_language_code="hi-IN")
            followup_answers.append(user_input_en)
            self.messages.append({"role": "user", "content": user_input_en})

        all_symptoms = f"{self.user_symptoms}. " + " ".join(followup_answers)
        triage_prompt = f"""
You are a medical triage assistant. Based on the following symptoms and answers, classify the case as one of:
- self_care (mild, can be managed at home)
- appointment_needed (moderate, needs doctor visit)
- emergency (potentially life-threatening)

Symptoms and answers: "{all_symptoms}"

Respond ONLY in JSON with:
- triage_level: self_care, appointment_needed, or emergency
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat
- suggested_actions: List of suggested actions for the user (e.g., ["Set Reminder", "Book Appointment Anyway", "Read More Tips"])

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned.
"""
        triage_result = self.ask_llm_json(triage_prompt)
        self.save_conversation_step(triage_result)
        self.log_and_speak(triage_result)

        actions = triage_result.get("suggested_actions", [])
        if actions:
            actions_str = ", ".join(actions)
            self.log_and_speak(f"Suggested actions: {actions_str}")

        triage_level = triage_result.get("triage_level", "")
        if triage_level == "self_care":
            self.log_and_speak("What would you like to do? You can say: " + ", ".join(actions))
            choice = self.log_and_get_voice_input().strip().lower()
            if "reminder" in choice:
                self.log_and_speak("Reminder set. We'll check in after 3 days.")
                return "ended"
            elif "book" in choice or "appointment" in choice:
                result = self.offer_appointment()
                if result == "ended":
                    return "ended"
                if result == "appointment confirmed":
                    return self.handle_followup_queries()
                return result
            else:
                self.log_and_speak("Take care! Let us know if you need anything else.")
                return "ended"
        elif triage_level == "appointment_needed":
            result = self.offer_appointment()
            if result == "ended":
                return "ended"
            if result == "appointment confirmed":
                return self.handle_followup_queries()
            return result
        elif triage_level == "emergency":
            self.log_and_speak("यह आपातकालीन स्थिति हो सकती है। कृपया तुरंत चिकित्सा सहायता प्राप्त करें।")
            self.log_and_speak("क्या आप बैकअप के रूप में अपॉइंटमेंट बुक करना चाहेंगे? कृपया हां या नहीं कहें।")
            choice = self.log_and_get_voice_input().strip().lower()
            if "हाँ" in choice or "haan" in choice or "yes" in choice:
                result = self.offer_appointment()
                if result == "ended":
                    return "ended"
                if result == "appointment confirmed":
                    return self.handle_followup_queries()
                return result
            else:
                self.log_and_speak("ध्यान रखें! अगर आपको कुछ और चाहिए तो हमें बताएं।")
                return "ended"

    def extract_number(self, text: str) -> str:
        """
        Extract number from text, handling both numeric and word representations
        """
        text = text.lower().strip()
        # First try direct match for words
        if text in self.NUMBER_WORDS:
            return self.NUMBER_WORDS[text]
        
        # Try to find number word in the text
        for word in text.split():
            if word in self.NUMBER_WORDS:
                return self.NUMBER_WORDS[word]

        # Check for digits in the text
        numeric_part = ''.join(filter(str.isdigit, text))
        if numeric_part:
            return numeric_part
        
        return None

    def format_natural_date_to_telugu(self, date_str, include_brackets=True):
        """
        Convert natural date format (e.g., "May 10th 2025") to Telugu with optional English reference
        """
        if not self.language_config or self.language_config.get("code") != "te-IN":
            return date_str
            
        # English to Telugu numeral mapping
        numeral_mapping = {
            "0": "సున్న", "1": "ఒకటి", "2": "రెండు", "3": "మూడు", "4": "నాలుగు", "5": "అయిదు",
            "6": "ఆరు", "7": "ఏడు", "8": "ఎనిమిది", "9": "తొమ్మిది", "10": "పది", "పదకొండు": "11",
            "పన్నెండు": "12", "పదమూడు": "13", "పదునాలుగు": "14", "పదునయిదు": "15", "పదహారు": "16",
            "పదిహేడు": "17", "పద్దెనిమిది": "18", "పందొమ్మిది": "19", "20": "ఇరవై", "21": "ఇరవై ఒకటి",
            "22": "ఇరవై రెండు", "23": "ఇరవై మూడు", "24": "ఇరవై నాలుగు", "25": "ఇరవై అయిదు",
            "26": "ఇరవై ఆరు", "27": "ఇరవై ఏడు", "28": "ఇరవై ఎనిమిది", "29": "ఇరవై తొమ్మిది", "30": "ముప్పై", "31": "ముప్పై ఒకటి"
        }
        
        # English to Telugu month mapping
        month_mapping = {
            "January": "జనవరి", "February": "ఫిబ్రవరి", "March": "మార్చి", "April": "ఏప్రిల్",
            "May": "మే", "June": "జూన్", "July": "జులై", "August": "ఆగస్టు",
            "September": "సెప్టెంబర్", "October": "అక్టోబర్", "November": "నవంబర్", "December": "డిసెంబర్"
        }
        
        def convert_year_to_telugu(year_str):
            """Convert year to proper Telugu number words"""
            year = int(year_str)
            if year == 2025:
                return "రెండు వేల ఇరవై ఐదు"
            elif year == 2024:
                return "రెండు వేల ఇరవై నాలుగు"
            elif year == 2026:
                return "రెండు వేల ఇరవై ఆరు"
            elif year == 2023:
                return "రెండు వేల ఇరవై మూడు"
            elif year == 2027:
                return "రెండు వేల ఇరవై ఏడు"
            elif year == 2028:
                return "రెండు వేల ఇరవై ఎనిమిది"
            elif year == 2029:
                return "రెండు వేల ఇరవై తొమ్మిది"
            elif year == 2030:
                return "రెండు వేల ముప్పై"
            else:
                # Fallback to digit-by-digit conversion for other years
                year_telugu = ""
                for digit in year_str:
                    year_telugu += numeral_mapping.get(digit, digit)
                return year_telugu
        
        import re
        
        # Pattern to match natural date format: "Month Day Year" (e.g., "May 10th 2025")
        date_pattern = r'(\w+)\s+(\d{1,2})(st|nd|rd|th)\s+(\d{4})'
        
        def replace_natural_date(match):
            month = match.group(1)
            day = match.group(2)
            suffix = match.group(3)
            year = match.group(4)
            
            # Convert month to Telugu
            month_telugu = month_mapping.get(month, month)
            
            # Convert day and year to Telugu
            day_telugu = numeral_mapping.get(day, day)
            year_telugu = convert_year_to_telugu(year)
            
            if include_brackets:
                return f"{month_telugu}({month}) {day_telugu}({day}), {year_telugu}({year})న"
            else:
                return f"{month_telugu} {day_telugu}, {year_telugu}న"
        
        return re.sub(date_pattern, replace_natural_date, date_str)

    def convert_time_to_telugu(self, time_str, include_brackets=True):
        """
        Convert time format (HH:MM) to Telugu with optional English reference
        """
        if not self.language_config or self.language_config.get("code") != "te-IN":
            return time_str
            
        # English to Telugu numeral mapping
        numeral_mapping = {
            "0": "సున్న", "1": "ఒకటి", "2": "రెండు", "3": "మూడు", "4": "నాలుగు", "5": "అయిదు",
            "6": "ఆరు", "7": "ఏడు", "8": "ఎనిమిది", "9": "తొమ్మిది", "10": "పది", "11": "పదకొండు",
            "12": "పన్నెండు", "13": "పదమూడు", "14": "పదునాలుగు", "15": "పదునయిదు", "16": "పదహారు",
            "17": "పదిహేడు", "18": "పద్దెనిమిది", "19": "పందొమ్మిది", "20": "ఇరవై", "21": "ఇరవై ఒకటి",
            "22": "ఇరవై రెండు", "23": "ఇరవై మూడు", "24": "ఇరవై నాలుగు", "25": "ఇరవై అయిదు",
            "26": "ఇరవై ఆరు", "27": "ఇరవై ఏడు", "28": "ఇరవై ఎనిమిది", "29": "ఇరవై తొమ్మిది", "30": "ముప్పై", "31": "ముప్పై ఒకటి"
        }
        
        import re
        
        # Handle time format (HH:MM)
        time_pattern = r'(\d{1,2}):(\d{2})'
        def replace_time(match):
            hour = int(match.group(1))
            minute = int(match.group(2))
            original_time = match.group(0)  # e.g., "10:00"
            
            # Convert to Telugu numerals
            hour_telugu = numeral_mapping.get(str(hour), str(hour))
            minute_telugu = numeral_mapping.get(str(minute), str(minute))
            
            # Determine time period (morning/afternoon/evening)
            if hour < 12:
                time_period = "ఉదయం"
            elif hour < 17:
                time_period = "మధ్యాహ్నం"
            else:
                time_period = "సాయంత్రం"
            
            # Format time in natural Telugu
            if minute == 0:
                # Exact hour
                if include_brackets:
                    return f"{time_period} {hour_telugu}({original_time}) గంటలకు"
                else:
                    return f"{time_period} {hour_telugu} గంటలకు"
            else:
                # Hour with minutes
                if include_brackets:
                    return f"{hour_telugu} గంటల {minute_telugu} నిమిషాలకు({original_time})"
                else:
                    return f"{hour_telugu} గంటల {minute_telugu} నిమిషాలకు"
        
        return re.sub(time_pattern, replace_time, time_str)

    def english_to_telugu_numerals(self, text, include_brackets=True):
        """
        Convert English numerals in text to Telugu numerals with optional English reference in brackets
        """
        if not self.language_config or self.language_config.get("code") != "te-IN":
            return text
            
        # English to Telugu numeral mapping for complete numbers
        numeral_mapping = {
            "0": "సున్న", "1": "ఒకటి", "2": "రెండు", "3": "మూడు", "4": "నాలుగు", "5": "అయిదు",
            "6": "ఆరు", "7": "ఏడు", "8": "ఎనిమిది", "9": "తొమ్మిది", "10": "పది", "11": "పదకొండు",
            "12": "పన్నెండు", "13": "పదమూడు", "14": "పదునాలుగు", "15": "పదునయిదు", "16": "పదహారు",
            "17": "పదిహేడు", "18": "పద్దెనిమిది", "19": "పందొమ్మిది", "20": "ఇరవై", "21": "ఇరవై ఒకటి",
            "22": "ఇరవై రెండు", "23": "ఇరవై మూడు", "24": "ఇరవై నాలుగు", "25": "ఇరవై అయిదు",
            "26": "ఇరవై ఆరు", "27": "ఇరవై ఏడు", "28": "ఇరవై ఎనిమిది", "29": "ఇరవై తొమ్మిది", "30": "ముప్పై", "31": "ముప్పై ఒకటి"
        }
        
        # Special handling for time format (HH:MM)
        import re
        
        # Handle time format first (e.g., "10:00", "11:30")
        time_pattern = r'(\d{1,2}):(\d{2})'
        def replace_time(match):
            hour = match.group(1)
            minute = match.group(2)
            if include_brackets:
                hour_telugu = numeral_mapping.get(hour, hour)
                minute_telugu = numeral_mapping.get(minute, minute)
                return f"{hour_telugu}({hour}):{minute_telugu}({minute})"
            else:
                hour_telugu = numeral_mapping.get(hour, hour)
                minute_telugu = numeral_mapping.get(minute, minute)
                return f"{hour_telugu}:{minute_telugu}"
        
        text = re.sub(time_pattern, replace_time, text)
        
        # Handle year format (e.g., "2025")
        year_pattern = r'(\d{4})'
        def replace_year(match):
            year = match.group(1)
            if include_brackets:
                # Convert each digit individually for years
                year_telugu = ""
                for digit in year:
                    year_telugu += numeral_mapping.get(digit, digit)
                return f"{year_telugu}({year})"
            else:
                year_telugu = ""
                for digit in year:
                    year_telugu += numeral_mapping.get(digit, digit)
                return year_telugu
        
        text = re.sub(year_pattern, replace_year, text)
        
        # Handle day numbers with suffixes (e.g., "10th", "17th") - but be careful not to match month names
        day_pattern = r'\b(\d{1,2})(st|nd|rd|th)\b'
        def replace_day(match):
            day = match.group(1)
            suffix = match.group(2)
            if include_brackets:
                day_telugu = numeral_mapping.get(day, day)
                return f"{day_telugu}({day}){suffix}"
            else:
                day_telugu = numeral_mapping.get(day, day)
                return f"{day_telugu}{suffix}"
        
        text = re.sub(day_pattern, replace_day, text)
        
        # Handle remaining single and double digit numbers that are not part of other patterns
        # Use word boundaries to avoid matching parts of larger numbers
        # Also avoid matching already converted Telugu numerals
        number_pattern = r'\b(\d{1,2})\b'
        def replace_number(match):
            number = match.group(1)
            # Skip if this number is already part of a converted pattern
            start_pos = match.start()
            end_pos = match.end()
            # Check if this number is already inside parentheses (already converted)
            if start_pos > 0 and text[start_pos-1] == '(' and end_pos < len(text) and text[end_pos] == ')':
                return match.group(0)  # Return unchanged
            if include_brackets:
                number_telugu = numeral_mapping.get(number, number)
                return f"{number_telugu}({number})"
            else:
                number_telugu = numeral_mapping.get(number, number)
                return number_telugu
        
        text = re.sub(number_pattern, replace_number, text)
            
        return text

    def format_date_for_speech(self, date_str, natural=False):
        try:
            year, month, day = date_str.split('-')
            import calendar
            month_name = calendar.month_name[int(month)]
            day_int = int(day)
            suffix = 'th' if 11<=day_int<=13 else {1:'st',2:'nd',3:'rd'}.get(day_int%10, 'th')
            if natural:
                return f"{month_name} {day_int}{suffix} {year}"
            return f"{year} {month} {day}"
        except:
            return date_str

    def parse_spoken_date(self, date_text: str) -> str:
        """
        Convert spoken date to YYYY-MM-DD format
        """
        # Remove common words and clean the input
        date_text = date_text.lower().replace('hyphen', '-').replace('dash', '-')
        date_text = ' '.join(date_text.split())
        
        # Try to extract numbers
        numbers = re.findall(r'\d+', date_text)
        if len(numbers) >= 3:
            year = numbers[0]
            month = numbers[1].zfill(2)  # Pad with leading zero if needed
            day = numbers[2].zfill(2)    # Pad with leading zero if needed
            return f"{year}-{month}-{day}"
        return None

    def parse_spoken_time(self, spoken_time):
        """Convert spoken time into HH:MM format"""
        spoken_time = spoken_time.lower().strip()
        
        # Direct time format mapping
        time_mapping = {
            "ten": "10:00",
            "ten o'clock": "10:00",
            "ten zero zero": "10:00",
            "ten hundred": "10:00",
            "ten am": "10:00",
            "ten a.m.": "10:00",
            "ten in the morning": "10:00",
            "ten in the afternoon": "10:00",
            "ten pm": "22:00",
            "ten p.m.": "22:00",
            "ten in the evening": "22:00",
            "ten at night": "22:00",
            "two": "14:00",
            "two o'clock": "14:00",
            "two zero zero": "14:00",
            "two hundred": "14:00",
            "two pm": "14:00",
            "two p.m.": "14:00",
            "two in the afternoon": "14:00",
            "two in the evening": "14:00",
            "eleven": "11:00",
            "eleven o'clock": "11:00",
            "eleven zero zero": "11:00",
            "eleven hundred": "11:00",
            "eleven am": "11:00",
            "eleven a.m.": "11:00",
            "eleven in the morning": "11:00",
            "eleven in the afternoon": "11:00",
            "eleven pm": "23:00",
            "eleven p.m.": "23:00",
            "eleven in the evening": "23:00",
            "eleven at night": "23:00",
            "one": "13:00",
            "one o'clock": "13:00",
            "one zero zero": "13:00",
            "one hundred": "13:00",
            "one pm": "13:00",
            "one p.m.": "13:00",
            "one in the afternoon": "13:00",
            "one in the evening": "13:00"
        }

        # Try direct mapping first
        if spoken_time in time_mapping:
            return time_mapping[spoken_time]

        # Try to extract numbers
        numbers = re.findall(r'\d+', spoken_time)
        if len(numbers) >= 2:
            hour = int(numbers[0])
            minute = int(numbers[1])
            return f"{hour:02d}:{minute:02d}"
        elif len(numbers) == 1:
            hour = int(numbers[0])
            return f"{hour:02d}:00"

        # Try word-based number conversion
        for word, number in self.NUMBER_WORDS.items():
            if word in spoken_time:
                hour = int(number)  # Convert to integer
                # Check for PM
                if any(pm_word in spoken_time for pm_word in ["pm", "p.m.", "evening", "night"]):
                    if hour < 12:
                        hour += 12
                return f"{hour:02d}:00"

        return None

    def handle_post_appointment_questions(self):
        self.log_and_speak(self.static_messages[self.get_lang_key()]["other_questions"])
        followup_response = self.log_and_get_voice_input().strip().lower()
        # Remove punctuation for robust matching
        followup_response_clean = followup_response.translate(str.maketrans('', '', string.punctuation))
        
        # Define yes/no words for both English and Telugu
        if self.language_config and self.language_config.get("code") == "te-IN":
            yes_words = ["yes", "yeah", "ok", "okay", "y", "sure", "అవును", "సరే", "ఓకే", "అవునండి"]
            no_words = ["no", "bye", "thank you", "goodbye", "కాదు", "లేదు", "ధన్యవాదాలు", "వీడ్కోలు"]
        elif self.language_config and self.language_config.get("code") == "hi-IN":
            yes_words = ["yes", "yeah", "ok", "okay", "y", "sure", "हाँ", "हां", "हा", "सही", "ठीक", "बिल्कुल"]
            no_words = ["no", "bye", "thank you", "goodbye", "नहीं", "नही", "नहि", "धन्यवाद", "अलविदा"]
        else:
            yes_words = ["yes", "yeah", "ok", "okay", "y", "sure"]
            no_words = ["no", "bye", "thank you", "goodbye"]
            
        if any(word in followup_response_clean.split() for word in no_words):
            self.log_and_speak(self.static_messages[self.get_lang_key()]["thank_you"])
            return "ended"
        elif any(word in followup_response_clean.split() for word in yes_words):
            self.log_and_speak(self.static_messages[self.get_lang_key()]["tell_question"])
            user_question = self.log_and_get_voice_input()
            
            # Check for incomplete input
            user_question_clean = user_question.strip()
            incomplete_endings = ('I', 'i', 'also', 'and', 'but', 'been', 'had', 'have', 'am', 'is', 'are', 'was', 'were')
            if (len(user_question_clean) < 5 or 
                user_question_clean.endswith(incomplete_endings) or
                user_question_clean.count(' ') < 2):
                self.log_and_speak("I didn't catch that completely. Could you please repeat your question?")
                return self.handle_post_appointment_questions()
            
            # Check for clarification statements
            clarification_keywords = ['not talking', 'not about', 'not referring', 'not discussing', 'clarify', 'explain', 'mean']
            if any(keyword in user_question_clean.lower() for keyword in clarification_keywords):
                self.log_and_speak("I understand. How else can I help you?")
                return self.handle_post_appointment_questions()
            
            # Use the enhanced prompt for post-appointment Q&A with context awareness
            context = f"Patient's original symptoms: {self.user_symptoms}"
            
            # Get appointment details for responses
            appointment_info = ""
            if hasattr(self, 'current_appointment') and self.current_appointment:
                appointment_info = f"Current appointment: {self.current_appointment.get('formatted_date', '')} at {self.current_appointment.get('time', '')} with {self.current_appointment.get('doctor', '')}"
            
            prompt = f"""
You are a healthcare assistant. A patient just finished booking an appointment and asked: "{user_question}"

Patient's context: {context}
{appointment_info}

IMPORTANT: First, determine if this is a clarification/explanation (not a question). If the user is clarifying, correcting, or explaining something, respond with: "I understand. How else can I help you?"

If it's a question, classify it based on these keywords:

**Appointment Info** (keywords: date, time, when, where, location, address, hospital, attend, visit, appointment, schedule)
- For date/time questions: "Your appointment is scheduled for {self.current_appointment.get('formatted_date', 'the scheduled date')} at {self.current_appointment.get('time', 'the scheduled time')} with {self.current_appointment.get('doctor', 'your doctor')}. Please arrive 15 minutes early."
- For address questions: "Our hospital is located at 123 Medical Center Drive, Healthcare City, HC 12345. Call (555) 123-4567 for directions."

**Symptom Follow-up** (keywords: symptom, pain, feeling, experiencing, condition, health)
- Ask for more specific details about their symptoms

**New Health Issue** (keywords: new, also, additional, another, headache, fever, etc.)
- Ask about timing, severity, and connection to existing symptoms

**Medical Advice Request** (keywords: advice, help, relief, treatment, cure, medicine, medication)
- Provide general guidance with disclaimer: "(Note: This advice is AI-generated and not a diagnosis.)"

**General Question** (anything else)
- Answer appropriately

RESPOND DIRECTLY without mentioning classification. Keep responses concise and professional.

Respond ONLY in JSON with:
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned."""
            response_data = self.ask_ai(prompt)
            
            # Handle dual-response format
            if isinstance(response_data, dict) and "spoken_text" in response_data and "display_text" in response_data:
                response = response_data["display_text"].strip()
            else:
                response = response_data.strip()
            
            # Clean up response - remove any classification text
            if "**" in response:
                response = response.split("→", 1)[-1].strip() if "→" in response else response
                response = response.replace("**", "").strip()
            
            # Handle multiple symptoms specifically ONLY if it's actually a new health issue
            if "new health issue" in response.lower() or "new symptoms" in response.lower():
                # Extract the new symptom from user question
                if "headache" in user_question.lower():
                    response = self.handle_multiple_symptoms("headache")
                elif "chest pain" in user_question.lower():
                    response = self.handle_multiple_symptoms("chest pain")
                else:
                    # Generic handling for other new symptoms
                    response = self.handle_multiple_symptoms(user_question)

            self.log_and_speak(response_data)
            
            # Ask if there are more questions
            return self.handle_post_appointment_questions()
        else:
            self.log_and_speak(self.static_messages[self.get_lang_key()]["didnt_catch"])
            return self.handle_post_appointment_questions()

    def handle_followup_queries(self):
        # Track user answers and asked questions
        questions_asked = 0
        max_questions = 4
        asked_questions = set()
        user_answers = []
        # Track repeated diagnostic questions
        if not hasattr(self, 'diagnosis_attempts'):
            self.diagnosis_attempts = 0
        diagnostic_phrases = [
            'what is the reason', 'what would be the reason', 'what is causing', 'what could be the cause',
            'what is the cause', 'what am i experiencing', 'what is wrong with me', 'what is my diagnosis',
            'do i have', 'is this', 'can you diagnose', 'what does this mean', 'what should i do', 'what is the solution', 'how do i treat', 'how can i fix', 'how do i cure', 'what is the treatment'
        ]
        while questions_asked < max_questions:
            # Use the full conversation for context
            context = '\n'.join([f"Q: {q}\nA: {a}" for q, a in user_answers])
            prompt = f"""
You are a professional healthcare assistant helping a patient describe their health problem.

Patient's initial symptoms: '{self.user_symptoms}'
Previous Q&A:
{context}

Instructions:
- Review all previous questions and answers.
- DO NOT repeat any question.
- Identify the most important missing medical detail (e.g., duration, severity, associated symptoms, risk factors, emergency signs).
- Ask ONE new, clear, and medically relevant follow-up question (max 12 words) that has NOT been asked before.
- If you have enough information to recommend next steps or triage, reply with 'END_FOLLOWUP' instead of a question.

Respond ONLY in JSON with:
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned.
"""
            followup_response = self.ask_ai(prompt)
            
            # Handle dual-response format
            if isinstance(followup_response, dict) and "spoken_text" in followup_response and "display_text" in followup_response:
                followup_question = followup_response["display_text"].strip()
            else:
                followup_question = followup_response.strip()
            
            # Early exit if LLM says enough info
            if followup_question == 'END_FOLLOWUP':
                break
            if followup_question in asked_questions:
                continue
            asked_questions.add(followup_question)
            self.log_and_speak(followup_response)
            response = self.log_and_get_voice_input()
            user_answers.append((followup_question, response))
            # Early exit if user says 'no' to a key question
            if response.strip().lower() in ["no", "nope", "nah", "కాడూ", "लेदू", "नहीं"]:
                break
            questions_asked += 1
            # Track repeated diagnostic questions
            if any(phrase in response.lower() for phrase in diagnostic_phrases):
                self.diagnosis_attempts += 1
            else:
                self.diagnosis_attempts = 0
            if self.diagnosis_attempts >= 2:
                self.log_and_speak("I'm not able to provide a diagnosis. Please discuss your symptoms with your healthcare provider.")
                self.diagnosis_attempts = 0
                return self.handle_followup_queries()
            if any(phrase in response.lower() for phrase in diagnostic_phrases):
                self.log_and_speak(self.static_messages[self.get_lang_key()]["not_provide_diagnosis"])
                return self.handle_followup_queries()
        self.log_and_speak(self.static_messages[self.get_lang_key()]["other_questions"])
        followup_response = self.log_and_get_voice_input().strip().lower()
        # Remove punctuation for robust matching
        followup_response_clean = followup_response.translate(str.maketrans('', '', string.punctuation))
        
        # Define yes/no words for both English and Telugu
        if self.language_config and self.language_config.get("code") == "te-IN":
            yes_words = ["yes", "yeah", "ok", "okay", "y", "sure", "అవును", "సరే", "ఓకే", "అవునండి"]
            no_words = ["no", "bye", "thank you", "goodbye", "కాదు", "లేదు", "ధన్యవాదాలు", "వీడ్కోలు"]
        elif self.language_config and self.language_config.get("code") == "hi-IN":
            yes_words = ["yes", "yeah", "ok", "okay", "y", "sure", "हाँ", "हां", "हा", "सही", "ठीक", "बिल्कुल"]
            no_words = ["no", "bye", "thank you", "goodbye", "नहीं", "नही", "नहि", "धन्यवाद", "अलविदा"]
        else:
            yes_words = ["yes", "yeah", "ok", "okay", "y", "sure"]
            no_words = ["no", "bye", "thank you", "goodbye"]
            
        if any(word in followup_response_clean.split() for word in no_words):
            self.log_and_speak(self.static_messages[self.get_lang_key()]["thank_you"])
            return "ended"
        elif any(word in followup_response_clean.split() for word in yes_words):
            self.log_and_speak(self.static_messages[self.get_lang_key()]["tell_question"])
            user_question = self.log_and_get_voice_input()
            
            # Check for incomplete input
            user_question_clean = user_question.strip()
            incomplete_endings = ('I', 'i', 'also', 'and', 'but', 'been', 'had', 'have', 'am', 'is', 'are', 'was', 'were')
            if (len(user_question_clean) < 5 or 
                user_question_clean.endswith(incomplete_endings) or
                user_question_clean.count(' ') < 2):
                self.log_and_speak("I didn't catch that completely. Could you please repeat your question?")
                return self.handle_followup_queries()
            # Check for clarification statements
            clarification_keywords = ['not talking', 'not about', 'not referring', 'not discussing', 'clarify', 'explain', 'mean']
            if any(keyword in user_question_clean.lower() for keyword in clarification_keywords):
                self.log_and_speak("I understand. How else can I help you?")
                return self.handle_followup_queries()
            
            # Use the enhanced prompt for post-appointment Q&A with context awareness
            context = f"Patient's original symptoms: {self.user_symptoms}"
            
            # Get appointment details for responses
            appointment_info = ""
            if hasattr(self, 'current_appointment') and self.current_appointment:
                appointment_info = f"Current appointment: {self.current_appointment.get('formatted_date', '')} at {self.current_appointment.get('time', '')} with {self.current_appointment.get('doctor', '')}"
            
            prompt = f"""
You are a healthcare assistant. A patient just finished booking an appointment and asked: "{user_question}"

Patient's context: {context}
{appointment_info}

IMPORTANT: First, determine if this is a clarification/explanation (not a question). If the user is clarifying, correcting, or explaining something, respond with: "I understand. How else can I help you?"

If it's a question, classify it based on these keywords:

**Appointment Info** (keywords: date, time, when, where, location, address, hospital, attend, visit, appointment, schedule)
- For date/time questions: "Your appointment is scheduled for {self.current_appointment.get('formatted_date', 'the scheduled date')} at {self.current_appointment.get('time', 'the scheduled time')} with {self.current_appointment.get('doctor', 'your doctor')}. Please arrive 15 minutes early."
- For address questions: "Our hospital is located at 123 Medical Center Drive, Healthcare City, HC 12345. Call (555) 123-4567 for directions."

**Symptom Follow-up** (keywords: symptom, pain, feeling, experiencing, condition, health)
- Ask for more specific details about their symptoms

**New Health Issue** (keywords: new, also, additional, another, headache, fever, etc.)
- Ask about timing, severity, and connection to existing symptoms

**Medical Advice Request** (keywords: advice, help, relief, treatment, cure, medicine, medication)
- Provide general guidance with disclaimer: "(Note: This advice is AI-generated and not a diagnosis.)"

**General Question** (anything else)
- Answer appropriately

RESPOND DIRECTLY without mentioning classification. Keep responses concise and professional.

Respond ONLY in JSON with:
- spoken_text: Short, 1–2 sentence summary suitable for speech
- display_text: Full, detailed response to show in chat

Do NOT include any JSON formatting or code blocks in your spoken_text or display_text. Only the JSON object should be returned."""
            response_data = self.ask_ai(prompt)
            
            # Handle dual-response format
            if isinstance(response_data, dict) and "spoken_text" in response_data and "display_text" in response_data:
                response = response_data["display_text"].strip()
            else:
                response = response_data.strip()
            
            # Clean up response - remove any classification text
            if "**" in response:
                response = response.split("→", 1)[-1].strip() if "→" in response else response
                response = response.replace("**", "").strip()
            
            # Handle multiple symptoms specifically ONLY if it's actually a new health issue
            if "new health issue" in response.lower() or "new symptoms" in response.lower():
                # Extract the new symptom from user question
                if "headache" in user_question.lower():
                    response = self.handle_multiple_symptoms("headache")
                elif "chest pain" in user_question.lower():
                    response = self.handle_multiple_symptoms("chest pain")
                else:
                    # Generic handling for other new symptoms
                    response = self.handle_multiple_symptoms(user_question)

            self.log_and_speak(response_data)
            return self.handle_post_appointment_questions()
        else:
            self.log_and_speak(self.static_messages[self.get_lang_key()]["didnt_catch"])
            return self.handle_post_appointment_questions()
    
    def load_session_data(self, session_id):
        """
        Attempt to load session data for the given session_id.
        Returns True if session data is loaded, False otherwise.
        """
        # Example: Try to load from self.session_data dict or a database/file
        # For now, this is a stub that always returns False.
        # You can implement actual loading logic here if needed.
        return False

    # def save_session_data(self):
    def save_session_data(self):
        """
        Save session data for the current session.
        Implement actual saving logic as needed.
        """
        # Example: Save to self.session_data dict, file, or database
        # For now, this is a stub that does nothing.
        pass
    # def save_conversation_step(self, data):
    def save_conversation_step(self, data):
        """
        Stub for saving a conversation step.
        Implement actual saving logic as needed.
        """
        pass
    def select_language(self):
    # def select_language(self):ease select your language. Say one for English, two for Hindi, three for Telugu.")
        self.log_and_speak("Please select your language. Say one for English, two for Hindi, three for Telugu.")
        while True:
            lang_input = self.log_and_get_voice_input().strip().lower()
            if lang_input in ["1", "one", "english"]:
                self.selected_language = {"code": "en-US"}
                return True
            elif lang_input in ["2", "two", "hindi"]:
                self.selected_language = {"code": "hi-IN"}
                return True
            elif lang_input in ["3", "three", "telugu"]:
                self.selected_language = {"code": "te-IN"}
                return True
            else:
                self.log_and_speak("I couldn't understand your language choice. Please say one for English, two for Hindi, or three for Telugu.")

    def offer_appointment(self, direct=False):
        max_dept_attempts = 3
        dept_attempts = 0
        while dept_attempts < max_dept_attempts:
            if direct:
                department = self.user_symptoms
            else:
                # Use LLM to infer department from user input (Telugu or English)
                department = self.infer_department_from_llm(self.user_symptoms)
            # --- DB LOGIC: Query doctors by department ---
            db_department = self.db.query(Department).filter(Department.name.ilike(department)).first()
            if not db_department:
                available_doctors = []
            else:
                available_doctors = self.db.query(Doctor).filter_by(department_id=db_department.id).all()
            if not available_doctors:
                dept_attempts += 1
                if dept_attempts < max_dept_attempts:
                    self.log_and_speak(self.static_messages[self.get_lang_key()]["no_doctors"].format(department=department))
                    self.log_and_speak(self.static_messages[self.get_lang_key()]["select_department"])
                    department_input = self.log_and_get_voice_input().strip()
                    department = self.infer_department_from_llm(department_input)
                    self.user_symptoms = department
                    continue
                else:
                    self.log_and_speak(self.static_messages[self.get_lang_key()]["no_doctors_final"])
                    return "no doctors available"
            print("\nAvailable Doctors:")
            for doctor in available_doctors:
                print(f"{doctor.name}")
            max_attempts = 3
            attempts = 0
            selected_doctor = None
            while attempts < max_attempts and not selected_doctor:
                self.log_and_speak(self.static_messages[self.get_lang_key()]["select_doctor"])
                selection = self.log_and_get_voice_input().strip().lower()
                lang = self.get_lang_key()
                # For now, match by name (case-insensitive)
                selected_doctor = next((doc for doc in available_doctors if doc.name.lower().replace("dr. ", "") in selection or selection in doc.name.lower()), None)
                if not selected_doctor:
                    attempts += 1
                    if attempts < max_attempts:
                        self.log_and_speak(self.static_messages[self.get_lang_key()]["doctor_not_found"])
                    else:
                        self.log_and_speak(self.static_messages[self.get_lang_key()]["doctor_not_found_final"])
                        return "doctor not found"
            # Prepare a dict for compatibility with downstream code
            doctor_dict = {"name": selected_doctor.name, "availability": []}
            for slot in selected_doctor.slots:
                date_str = slot.date.strftime("%Y-%m-%d")
                # Group slots by date
                found = False
                for avail in doctor_dict["availability"]:
                    if avail["date"] == date_str:
                        avail["slots"].append(slot.time.strftime("%H:%M"))
                        found = True
                        break
                if not found:
                    doctor_dict["availability"].append({"date": date_str, "slots": [slot.time.strftime("%H:%M")]})
            self.log_and_speak(self.static_messages[self.get_lang_key()]["lets_book"].format(doctor=selected_doctor.name))
            self.log_and_speak(self.static_messages[self.get_lang_key()]["selected_doctor"].format(doctor=selected_doctor.name))
            return self.handle_date_time_selection(doctor_dict)

    def parse_date_and_time_with_llm(self, text: str, available_slots_by_date: dict) -> (str, str):
        prompt = f"""
        From the user's response "{text}", identify the date and time they want to book.
        The available appointment slots are structured as a dictionary where keys are dates (YYYY-MM-DD) and values are lists of times (HH:MM): {available_slots_by_date}.
        Analyze the user's text. Find the best matching date and time from the available slots.
        If the user says "yes" or "correct" and there is only ONE available date and ONE available time slot in total, you can assume they are confirming that single slot.
        Return the result as a JSON object with two keys: "date" and "time".
        If the user's response is ambiguous or does not match any available slot, return a JSON object with "date": null and "time": null.
        Example of a successful response: {{"date": "2025-05-11", "time": "14:00"}}
        """
        try:
            response = litellm.completion(
                model="groq/llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            date = result.get("date")
            time = result.get("time")

            # Validate that the parsed slot is actually available
            if date and time and date in available_slots_by_date and time in available_slots_by_date[date]:
                return date, time
            return None, None
        except Exception as e:
            print(f"Error parsing date and time with LLM: {e}")
            return None, None

    def handle_date_time_selection(self, doctor):
        available_slots_by_date = {d['date']: d['slots'] for d in doctor['availability']}
        if not available_slots_by_date:
            self.log_and_speak(self.static_messages[self.get_lang_key()]["no_slots"].format(doctor=doctor['name']))
            return "no slots"
        self.log_and_speak(self.static_messages[self.get_lang_key()]["available_slots"])
        for date, times in sorted(available_slots_by_date.items()):
            date_str = self.format_date_for_speech(date, natural=True)
            # Sort times chronologically
            sorted_times = sorted(times, key=lambda x: datetime.strptime(x, "%H:%M"))
            times_str = " and ".join(sorted_times)
            # Use Telugu doctor name and convert numerals to Telugu
            doctor_name = doctor['name_te'] if self.get_lang_key() == "te" and 'name_te' in doctor else doctor['name_hi'] if self.get_lang_key() == "hi" and 'name_hi' in doctor else doctor['name']
            if self.get_lang_key() == "te":
                date_str_display = self.format_natural_date_to_telugu(date_str, include_brackets=True)
                times_display = self.convert_time_to_telugu(times_str, include_brackets=True)
                date_str_speech = self.format_natural_date_to_telugu(date_str, include_brackets=False)
                times_speech = self.convert_time_to_telugu(times_str, include_brackets=False)
                print(f"🤖 Assistant: {self.static_messages[self.get_lang_key()]['on_date'].format(date=date_str_display, doctor=doctor_name, times=times_display)}")
                self.log_and_speak(self.static_messages[self.get_lang_key()]["on_date"].format(date=date_str_speech, doctor=doctor_name, times=times_speech))
            elif self.get_lang_key() == "hi":
                date_str_display = self.format_natural_date_to_hindi(date_str, include_brackets=True)
                times_display = self.convert_time_to_hindi(times_str, include_brackets=True)
                date_str_speech = self.format_natural_date_to_hindi(date_str, include_brackets=False)
                times_speech = self.convert_time_to_hindi(times_str, include_brackets=False)
                print(f"🤖 Assistant: {self.static_messages[self.get_lang_key()]['on_date'].format(date=date_str_display, doctor=doctor_name, times=times_display)}")
                self.log_and_speak(self.static_messages[self.get_lang_key()]["on_date"].format(date=date_str_speech, doctor=doctor_name, times=times_speech))
            else:
                self.log_and_speak(self.static_messages[self.get_lang_key()]["on_date"].format(date=date_str, doctor=doctor_name, times=times_str))
            
            selected_date, selected_time = None, None
            for _ in range(3):
                self.log_and_speak(self.static_messages[self.get_lang_key()]["state_preferred"])
                response_text = self.log_and_get_voice_input()
                # Translate Telugu numerals and time expressions to English if needed
                try:
                    if self.get_lang_key() == "te":
                        # Basic replacements for Telugu numerals and time words
                        response_text = response_text.replace("ఏ ఎం", "AM").replace("పిఎం", "PM").replace("ఉదయం", "AM").replace("సాయంత్రం", "PM").replace("మధ్యాహ్నం", "PM")
                        
                        # Telugu numeral mappings
                        telugu_numerals = {
                            "సున్న": "0", "ఒకటి": "1", "రెండు": "2", "మూడు": "3", "నాలుగు": "4", "అయిదు": "5",
                            "ఆరు": "6", "ఏడు": "7", "ఎనిమిది": "8", "తొమ్మిది": "9", "పది": "10", "పదకొండు": "11",
                            "పన్నెండు": "12", "పదమూడు": "13", "పదునాలుగు": "14", "పదునయిదు": "15"
                        }
                        
                        # Replace Telugu numerals with English numbers
                        for telugu, english in telugu_numerals.items():
                            response_text = response_text.replace(telugu, english)
                        
                        # Replace Telugu month names
                        telugu_months = {
                            "జనవరి": "January", "ఫిబ్రవరి": "February", "మార్చి": "March", "ఏప్రిల్": "April",
                            "మే": "May", "జూన్": "June", "జులై": "July", "ఆగస్టు": "August",
                            "సెప్టెంబర్": "September", "అక్టోబర్": "October", "నవంబర్": "November", "డిసెంబర్": "December"
                        }
                        
                        for telugu, english in telugu_months.items():
                            response_text = response_text.replace(telugu, english)
                        
                        # Add more replacements as needed
                    selected_date, selected_time = self.parse_date_and_time_with_llm(response_text, available_slots_by_date)
                except Exception as e:
                    print(f"Error parsing date/time: {e}")
                    selected_date, selected_time = None, None
                if selected_date and selected_time:
                    break
                else:
                    self.log_and_speak(self.static_messages[self.get_lang_key()]["booking_trouble"])
            if not (selected_date and selected_time):
                self.log_and_speak(self.static_messages[self.get_lang_key()]["booking_trouble_final"])
                return "booking not confirmed"
            date_str = self.format_date_for_speech(selected_date, natural=True)
            # Use Telugu doctor name and convert numerals to Telugu
            doctor_name = doctor['name_te'] if self.get_lang_key() == "te" and 'name_te' in doctor else doctor['name_hi'] if self.get_lang_key() == "hi" and 'name_hi' in doctor else doctor['name']
            
            if self.get_lang_key() == "te":
                # For display (printed) - include English reference in brackets
                date_str_display = self.format_natural_date_to_telugu(date_str, include_brackets=True)
                time_display = self.convert_time_to_telugu(selected_time, include_brackets=True)
                # For speech (spoken) - Telugu only
                date_str_speech = self.format_natural_date_to_telugu(date_str, include_brackets=False)
                time_speech = self.convert_time_to_telugu(selected_time, include_brackets=False)
                
                # Print with brackets for reference
                print(f"🤖 Assistant: {self.static_messages[self.get_lang_key()]['confirm_booking'].format(doctor=doctor_name, date=date_str_display, time=time_display)}")
                # Speak without brackets
                self.log_and_speak(self.static_messages[self.get_lang_key()]["confirm_booking"].format(doctor=doctor_name, date=date_str_speech, time=time_speech))
            else:
                self.log_and_speak(self.static_messages[self.get_lang_key()]["confirm_booking"].format(doctor=doctor_name, date=date_str, time=selected_time))
                
            confirm_response = self.log_and_get_voice_input().lower()
            # Add Telugu affirmatives
            yes_words = ["yes", "correct", "yep", "yeah", "ok", "అవును", "సరే", "ఓకే"]
            try:
                if any(word in confirm_response for word in yes_words):
                    # --- DB LOGIC START ---
                    # Find the user by user_id
                    user = self.db.query(User).filter_by(id=self.user_id).first()
                    # Find the doctor in DB
                    db_doctor = self.db.query(Doctor).filter_by(name=doctor['name']).first()
                    # Find the slot object in DB
                    slot = self.db.query(Slot).filter_by(doctor_id=db_doctor.id, date=selected_date, time=selected_time, is_booked=0).first()
                    if slot and user and db_doctor:
                        slot.is_booked = 1
                        appointment = Appointment(user_id=user.id, doctor_id=db_doctor.id, slot_id=slot.id)
                        self.db.add(appointment)
                        self.db.commit()
                        
                        # Verify booking was successful
                        verification = self.db.query(Appointment).filter_by(
                            user_id=user.id, 
                            doctor_id=db_doctor.id, 
                            slot_id=slot.id
                        ).first()
                        
                        if verification:
                            # Only show confirmation after successful database save
                            if self.get_lang_key() == "te":
                                # Print with brackets for reference
                                print(f"🤖 Assistant: {self.static_messages[self.get_lang_key()]['booking_confirmed'].format(doctor=doctor_name, date=date_str_display, time=time_display)}")
                                # Speak without brackets
                                self.log_and_speak(self.static_messages[self.get_lang_key()]["booking_confirmed"].format(doctor=doctor_name, date=date_str_speech, time=time_speech))
                            else:
                                self.log_and_speak(self.static_messages[self.get_lang_key()]["booking_confirmed"].format(doctor=doctor_name, date=date_str, time=selected_time))
                            
                            self.log_and_speak(f"Booking confirmed! Your appointment with {doctor['name']} on {self.format_date_for_speech(selected_date, natural=True)} at {selected_time} has been successfully saved to our system.")
                            
                            # Store appointment details for Q&A
                            self.current_appointment = {
                                'doctor': doctor['name'],
                                'date': selected_date,
                                'time': selected_time,
                                'formatted_date': self.format_date_for_speech(selected_date, natural=True)
                            }
                            
                    return self.handle_post_appointment_questions()
                else:
                    self.log_and_speak("There was an issue saving your appointment. Please contact our support team.")
                    return "booking not confirmed"
            except Exception as e:
                print(f"Error in confirmation step: {e}")
                self.log_and_speak(self.static_messages[self.get_lang_key()]["my_mistake"])
                return self.handle_date_time_selection(doctor)

    def get_available_doctors(self, department_name):
        """Get available doctors in the specified department."""
        try:
            department = self.db.query(Department).filter(
                Department.name.ilike(f"%{department_name}%")
            ).first()
            
            if not department:
                return []
            
            doctors = self.db.query(Doctor).filter(
                Doctor.department_id == department.id
            ).all()
            
            return doctors
        except Exception as e:
            print(f"Error getting doctors: {e}")
            return []
    
    def select_doctor(self, doctors):
        """Let user select a doctor from available options."""
        max_attempts = 3
        for attempt in range(max_attempts):
            if attempt == 0:
                doctor_names = [d.name for d in doctors]
                self.log_and_speak(f"Available doctors: {', '.join(doctor_names)}")
                self.log_and_speak(self.static_messages[self.get_lang_key()]["select_doctor"])
            else:
                self.log_and_speak("Please try selecting a doctor again.")
            
            user_input = self.log_and_get_voice_input().strip().lower()
            
            # Find matching doctor
            for doctor in doctors:
                if doctor.name.lower() in user_input or user_input in doctor.name.lower():
                    self.log_and_speak(self.static_messages[self.get_lang_key()]["selected_doctor"].format(doctor=doctor.name))
                    return doctor
            
            if attempt < max_attempts - 1:
                self.log_and_speak(self.static_messages[self.get_lang_key()]["doctor_not_found"])
            else:
                self.log_and_speak(self.static_messages[self.get_lang_key()]["doctor_not_found_final"])
                return None
        
        return None
    
    def get_available_slots(self, doctor_id):
        """Get available appointment slots for the specified doctor."""
        try:
            # Get slots for next 30 days
            from datetime import timedelta
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=30)
            
            slots = self.db.query(Slot).filter(
                Slot.doctor_id == doctor_id,
                Slot.date >= start_date,
                Slot.date <= end_date,
                Slot.is_booked == 0
            ).order_by(Slot.date, Slot.time).all()
            
            return slots
        except Exception as e:
            print(f"Error getting slots: {e}")
            return []
    
    def select_date_time(self, slots):
        """Let user select date and time from available slots."""
        max_attempts = 3
        for attempt in range(max_attempts):
            if attempt == 0:
                # Group slots by date
                slots_by_date = {}
                for slot in slots:
                    date_str = slot.date.strftime('%Y-%m-%d')
                    if date_str not in slots_by_date:
                        slots_by_date[date_str] = []
                    slots_by_date[date_str].append(slot)
                
                # Show available dates and times
                self.log_and_speak(self.static_messages[self.get_lang_key()]["available_slots"])
                for date_str, date_slots in list(slots_by_date.items())[:5]:  # Show first 5 dates
                    times = [slot.time.strftime('%I:%M %p') for slot in date_slots]
                    formatted_date = self.format_date_for_speech(date_str, natural=True)
                    self.log_and_speak(self.static_messages[self.get_lang_key()]["on_date"].format(
                        date=formatted_date,
                        doctor="the doctor",
                        times=", ".join(times)
                    ))
                
                self.log_and_speak(self.static_messages[self.get_lang_key()]["state_preferred"])
            else:
                self.log_and_speak("Please try selecting a date and time again.")
            
            user_input = self.log_and_get_voice_input().strip().lower()
            
            # Parse date and time using LLM
            parsed_datetime = self.parse_date_and_time_with_llm(user_input)
            if parsed_datetime:
                # Find matching slot
                for slot in slots:
                    if (slot.date.strftime('%Y-%m-%d') == parsed_datetime['date'] and 
                        slot.time.strftime('%H:%M') == parsed_datetime['time']):
                        return slot
            
            if attempt < max_attempts - 1:
                self.log_and_speak(self.static_messages[self.get_lang_key()]["booking_trouble"])
            else:
                self.log_and_speak(self.static_messages[self.get_lang_key()]["booking_trouble_final"])
                return None
        
        return None
    
    def confirm_booking(self, doctor, slot):
        """Confirm the appointment booking with the user."""
        formatted_date = self.format_date_for_speech(slot.date.strftime('%Y-%m-%d'), natural=True)
        formatted_time = slot.time.strftime('%I:%M %p')
        
        self.log_and_speak(self.static_messages[self.get_lang_key()]["confirm_booking"].format(
            doctor=doctor.name,
            date=formatted_date,
            time=formatted_time
        ))
        
        user_input = self.log_and_get_voice_input().strip().lower()
        
        # Check for confirmation
        confirm_keywords = ['yes', 'correct', 'right', 'confirm', 'okay', 'ok', 'sure', 'yeah', 'yep']
        deny_keywords = ['no', 'wrong', 'incorrect', 'cancel', 'stop', 'end']
        
        if any(keyword in user_input for keyword in confirm_keywords):
            return True
        elif any(keyword in user_input for keyword in deny_keywords):
            return False
        else:
            # Ask again if unclear
            self.log_and_speak("I didn't catch that. Please say yes to confirm or no to cancel.")
            user_input = self.log_and_get_voice_input().strip().lower()
            return any(keyword in user_input for keyword in confirm_keywords)
    
    def create_appointment(self, doctor, slot):
        """Create the appointment in the database."""
        try:
            # Create appointment
            appointment = Appointment(
                user_id=self.user_id,
                doctor_id=doctor.id,
                slot_id=slot.id
            )
            
            # Mark slot as booked
            slot.is_booked = 1
            
            # Add to database
            self.db.add(appointment)
            self.db.commit()
            
            return appointment
        except Exception as e:
            print(f"Error creating appointment: {e}")
            self.db.rollback()
            return None


    def ask_llm_json(self, prompt: str) -> dict:
        """Call LLM and return parsed JSON dict without translation or formatting."""
        try:
            response = litellm.completion(
                model="groq/llama-3.1-8b-instant",
                api_key=self.api_key,
                api_base="https://api.groq.com/openai/v1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            content = response["choices"][0]["message"]["content"].strip()
            import json
            return json.loads(content)
        except Exception as e:
            print(f"❌ ask_llm_json error: {e}")
            return {}