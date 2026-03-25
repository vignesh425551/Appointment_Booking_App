from collections import defaultdict
from contextlib import contextmanager
import os
import re

import streamlit as st
from sqlalchemy.exc import OperationalError as SAOperationalError

st.set_page_config(page_title="Healthcare Appointment Bot", page_icon="🩺", layout="centered")

from db.models import Appointment, Department, Doctor, Slot, User
from db.session import DATABASE_URL, DATABASE_URL_SOURCE, DATABASE_URL_SUMMARY, SessionLocal
from utils.sarvam_integration import SarvamHandler


LANGUAGES = ["English", "Hindi", "Telugu"]
LANGUAGE_CONFIG = {
    "English": {"code": "en-IN", "speaker": "manisha"},
    "Hindi": {"code": "hi-IN", "speaker": "manisha"},
    "Telugu": {"code": "te-IN", "speaker": "abhilash"},
}
SAMPLE_PHONES = [
    "5551000001",
    "5551000002",
    "5551000003",
    "5551000004",
]

SYMPTOM_DEPARTMENT_HINTS = {
    "Cardiology": ["chest pain", "palpitations", "heart", "shortness of breath", "bp"],
    "Gastroenterology": ["stomach", "acidity", "gas", "abdomen", "vomit", "nausea"],
    "Neurology": ["headache", "migraine", "dizziness", "seizure", "numbness"],
    "Orthopedics": ["joint", "knee", "back pain", "fracture", "bone", "muscle"],
    "Dermatology": ["rash", "itching", "skin", "acne", "allergy"],
    "Pediatrics": ["child", "baby", "infant", "kid"],
    "ENT": ["ear", "nose", "throat", "sinus", "tonsil"],
    "General Medicine": ["fever", "cold", "cough", "weakness", "fatigue"],
}


@contextmanager
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def infer_department_from_symptoms(symptoms: str, department_names: list[str]) -> str:
    text = (symptoms or "").lower()
    for department, keywords in SYMPTOM_DEPARTMENT_HINTS.items():
        if department in department_names and any(keyword in text for keyword in keywords):
            return department
    return "General Medicine" if "General Medicine" in department_names else department_names[0]


def get_user_by_phone(phone: str):
    with db_session() as session:
        return session.query(User).filter(User.phone == phone).first()


def get_departments():
    with db_session() as session:
        rows = session.query(Department).order_by(Department.name.asc()).all()
        return [(row.id, row.name) for row in rows]


def get_doctors(department_id: int):
    with db_session() as session:
        rows = (
            session.query(Doctor)
            .filter(Doctor.department_id == department_id)
            .order_by(Doctor.name.asc())
            .all()
        )
        return [(row.id, row.name) for row in rows]


def get_available_slots(doctor_id: int):
    with db_session() as session:
        rows = (
            session.query(Slot)
            .filter(Slot.doctor_id == doctor_id, Slot.is_booked == 0)
            .order_by(Slot.date.asc(), Slot.time.asc())
            .all()
        )
        return [(row.id, row.date, row.time) for row in rows]


def book_appointment(user_id: int, doctor_id: int, slot_id: int):
    with db_session() as session:
        slot = session.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            return False, "Selected slot does not exist."
        if slot.is_booked == 1:
            return False, "Selected slot is already booked. Please refresh and choose another slot."

        slot.is_booked = 1
        appointment = Appointment(user_id=user_id, doctor_id=doctor_id, slot_id=slot_id)
        session.add(appointment)
        session.commit()
        return True, "Appointment booked successfully."


def reset_flow():
    st.session_state.dialog_stage = "awaiting_login"
    st.session_state.user_phone = ""
    st.session_state.user_name = ""
    st.session_state.user_id = None
    st.session_state.mode = None
    st.session_state.symptoms = ""
    st.session_state.selected_department_id = None
    st.session_state.selected_doctor_id = None
    st.session_state.selected_slot_id = None
    st.session_state.booking_status = ""
    st.session_state.chat_history = []


def init_sarvam(language: str):
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        return None
    return SarvamHandler(language_config=LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"]))


def transcribe_audio_input(audio_file, sarvam: SarvamHandler):
    if audio_file is None or sarvam is None:
        return ""
    transcript = sarvam.speech_to_text_from_bytes(
        audio_bytes=audio_file.getvalue(),
        mime_type=getattr(audio_file, "type", None) or "audio/wav",
        filename=getattr(audio_file, "name", None) or "audio.wav",
    )
    if transcript.startswith("[ERROR:"):
        st.error(f"Voice transcription failed: {transcript}")
        return ""
    return transcript.strip()


def speak_text(text: str, sarvam: SarvamHandler):
    if not text or sarvam is None:
        return
    audio_path = sarvam.text_to_speech(text)
    if not audio_path:
        st.warning("Could not generate speech audio.")
        return
    with open(audio_path, "rb") as audio_file:
        st.audio(audio_file.read(), format="audio/wav")


def get_audio_input_widget(label: str, key: str):
    """Use audio_input when available, else fallback to file uploader."""
    if hasattr(st, "audio_input"):
        return st.audio_input(label, key=key)
    return st.file_uploader(
        f"{label} (upload .wav/.mp3/.m4a)",
        type=["wav", "mp3", "m4a"],
        key=key,
        accept_multiple_files=False,
    )


def assistant_reply(text: str, sarvam: SarvamHandler | None):
    st.session_state.chat_history.append(("assistant", text))
    if st.session_state.voice_mode:
        speak_text(text, sarvam)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def is_yes(text: str) -> bool:
    value = normalize(text)
    return value in {"yes", "y", "haan", "ha", "avunu", "ok", "okay", "confirm"}


def is_no(text: str) -> bool:
    value = normalize(text)
    return value in {"no", "n", "cancel", "vaddu", "nahi"}


def pick_department_id(user_text: str, departments: list[tuple[int, str]]) -> int | None:
    value = normalize(user_text)
    for dep_id, dep_name in departments:
        if normalize(dep_name) in value:
            return dep_id
    return None


def pick_doctor_id(user_text: str, doctors: list[tuple[int, str]]) -> int | None:
    value = normalize(user_text).replace("doctor ", "").replace("dr ", "")
    for doc_id, doc_name in doctors:
        doc_clean = normalize(doc_name).replace("dr.", "").replace("dr ", "").strip()
        if doc_clean and doc_clean in value:
            return doc_id
    return None


def pick_slot_id(user_text: str, slots: list[tuple[int, object, object]]) -> int | None:
    value = normalize(user_text).replace(".", ":")
    value = re.sub(r"\b(\d{1,2})\s*(am|pm)\b", r"\1:00 \2", value)

    month_map = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
        "nov": 11, "november": 11, "dec": 12, "december": 12,
    }
    day_match = re.search(r"\b([0-3]?\d)(?:st|nd|rd|th)?\b", value)
    requested_day = int(day_match.group(1)) if day_match else None
    requested_month = None
    for key, month in month_map.items():
        if re.search(rf"\b{key}\b", value):
            requested_month = month
            break

    filtered_slots = []
    if requested_day:
        for slot_id, date_value, time_value in slots:
            if date_value.day == requested_day and (requested_month is None or date_value.month == requested_month):
                filtered_slots.append((slot_id, date_value, time_value))
    if not filtered_slots:
        filtered_slots = slots

    for slot_id, _, time_value in filtered_slots:
        hour_24 = time_value.strftime("%H")
        minute = time_value.strftime("%M")
        hour_12 = str((time_value.hour % 12) or 12)
        am_pm = "am" if time_value.hour < 12 else "pm"
        candidates = {
            f"{hour_24}:{minute}",
            hour_24,
            f"{hour_12}:{minute} {am_pm}",
            f"{hour_12} {am_pm}",
        }
        if any(candidate in value for candidate in candidates):
            return slot_id
    return None


def main():
    st.title("🩺 Healthcare Appointment UI")
    st.caption("Streamlit interface for department-based appointment booking.")

    if "language" not in st.session_state:
        st.session_state.language = LANGUAGES[0]
    if "voice_mode" not in st.session_state:
        st.session_state.voice_mode = False
    if "dialog_stage" not in st.session_state:
        st.session_state.dialog_stage = "awaiting_login"
    if "user_phone" not in st.session_state:
        st.session_state.user_phone = ""
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "mode" not in st.session_state:
        st.session_state.mode = None
    if "symptoms" not in st.session_state:
        st.session_state.symptoms = ""
    if "selected_department_id" not in st.session_state:
        st.session_state.selected_department_id = None
    if "selected_doctor_id" not in st.session_state:
        st.session_state.selected_doctor_id = None
    if "selected_slot_id" not in st.session_state:
        st.session_state.selected_slot_id = None
    if "booking_status" not in st.session_state:
        st.session_state.booking_status = ""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.sidebar:
        st.subheader("Session")
        st.selectbox("Language", LANGUAGES, key="language")
        st.toggle("Voice mode", key="voice_mode", help="Use microphone input and spoken responses.")
        st.caption("Sample mobile numbers")
        for sample_phone in SAMPLE_PHONES:
            st.code(sample_phone)
        if st.button("Reset Conversation", use_container_width=True):
            reset_flow()
            st.rerun()
        if st.session_state.user_name:
            st.success(f"Signed in as {st.session_state.user_name}")

    sarvam = init_sarvam(st.session_state.language)
    if st.session_state.voice_mode and sarvam is None:
        st.warning("Voice mode needs `SARVAM_API_KEY` in your environment.")

    if DATABASE_URL_SOURCE == "fallback":
        st.error(
            "Database connection is not configured for this environment. "
            "Set `DATABASE_URL` in Streamlit Cloud app secrets (see `.streamlit/secrets.toml.example`) "
            "or set `DB_HOST/DB_NAME/DB_USER/DB_PASSWORD` env vars."
        )
        return

    if DATABASE_URL_SOURCE == "env_localhost":
        st.error(
            "⚠️ Your `DATABASE_URL` secret points to **localhost**, which is unavailable on Streamlit Cloud. "
            "Please update it in **App Settings → Secrets** to a real hosted PostgreSQL URL "
            "(e.g. from Neon, Supabase, or Railway)."
        )
        st.code('DATABASE_URL = "postgresql://user:password@your-cloud-host:5432/dbname?sslmode=require"', language="toml")
        return

    try:
        departments = get_departments()
    except SAOperationalError as e:
        host = DATABASE_URL_SUMMARY.get("host")
        dbname = DATABASE_URL_SUMMARY.get("database")
        port = DATABASE_URL_SUMMARY.get("port")
        st.error(
            "Could not connect to the database. "
            "Check your Streamlit Cloud database secrets / connection settings."
        )
        st.info(
            f"DB source: {DATABASE_URL_SOURCE} | host: {host} | port: {port} | db: {dbname}"
        )
        # The full exception is still available in Streamlit Cloud logs ("Manage app").
        st.write(f"OperationalError: {type(e).__name__}")
        return
    if not departments:
        st.error("No departments found. Run DB initialization and seeding first.")
        return

    department_names = [name for _, name in departments]
    department_map = {dep_id: dep_name for dep_id, dep_name in departments}

    st.subheader("Conversational Assistant")
    st.caption("Use one Talk flow: type or record, then click Talk.")
    st.info("Login hint: try sample numbers 5551000001, 5551000002, 5551000003, or 5551000004.")

    if not st.session_state.chat_history:
        opening = (
            "Hello! Please share your phone number to login and start booking. "
            "You can use sample numbers like 5551000001 or 5551000002."
            if st.session_state.dialog_stage == "awaiting_login"
            else "Welcome back. Say 'direct booking' or 'symptoms'."
        )
        st.session_state.chat_history.append(("assistant", opening))
        if st.session_state.voice_mode:
            speak_text(opening, sarvam)

    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.write(message)

    text_input = st.text_input("Your message", placeholder="Type here or use microphone below...")
    audio_input = get_audio_input_widget("Voice input", "talk_audio_input")

    if st.button("Talk", type="primary"):
        user_text = text_input.strip()
        if audio_input is not None:
            transcript = transcribe_audio_input(audio_input, sarvam)
            if transcript:
                user_text = transcript

        if not user_text:
            st.warning("Please type or record something before pressing Talk.")
            return

        st.session_state.chat_history.append(("user", user_text))
        msg = normalize(user_text)

        if st.session_state.dialog_stage == "awaiting_login":
            digits = "".join(ch for ch in user_text if ch.isdigit())
            phone = digits if len(digits) >= 10 else user_text.strip()
            user = get_user_by_phone(phone)
            if user:
                st.session_state.user_phone = user.phone
                st.session_state.user_name = user.name
                st.session_state.user_id = user.id
                st.session_state.dialog_stage = "awaiting_mode"
                assistant_reply(
                    f"Welcome {user.name}. Say 'direct booking' to pick department, or 'symptoms' to describe your issue.",
                    sarvam,
                )
            else:
                assistant_reply(
                    "I could not find that phone number. Please say or type a valid number. "
                    "Try sample numbers like 5551000001, 5551000002, or 5551000003.",
                    sarvam,
                )

        elif st.session_state.dialog_stage == "awaiting_mode":
            if "symptom" in msg:
                st.session_state.mode = "symptoms"
                st.session_state.dialog_stage = "awaiting_symptoms"
                assistant_reply("Please describe your symptoms.", sarvam)
            elif "direct" in msg or "booking" in msg:
                st.session_state.mode = "direct"
                st.session_state.dialog_stage = "awaiting_department"
                assistant_reply("Please choose a department: " + ", ".join(department_names), sarvam)
            else:
                assistant_reply("Please say either 'direct booking' or 'symptoms'.", sarvam)

        elif st.session_state.dialog_stage == "awaiting_symptoms":
            st.session_state.symptoms = user_text
            suggestion = infer_department_from_symptoms(st.session_state.symptoms, department_names)
            st.session_state.selected_department_id = next(dep_id for dep_id, dep_name in departments if dep_name == suggestion)
            st.session_state.dialog_stage = "awaiting_doctor"
            assistant_reply(
                f"Based on symptoms, suggested department is {suggestion}. Now say doctor name.",
                sarvam,
            )

        elif st.session_state.dialog_stage == "awaiting_department":
            dep_id = pick_department_id(user_text, departments)
            if dep_id is None:
                assistant_reply("I could not match that department. Available: " + ", ".join(department_names), sarvam)
            else:
                st.session_state.selected_department_id = dep_id
                st.session_state.dialog_stage = "awaiting_doctor"
                doctors = get_doctors(dep_id)
                if not doctors:
                    assistant_reply("No doctors are available in that department. Please choose another department.", sarvam)
                    st.session_state.dialog_stage = "awaiting_department"
                else:
                    doctor_names = [doc_name for _, doc_name in doctors]
                    assistant_reply("Available doctors: " + ", ".join(doctor_names) + ". Say a doctor name.", sarvam)

        elif st.session_state.dialog_stage == "awaiting_doctor":
            dep_id = st.session_state.selected_department_id
            doctors = get_doctors(dep_id) if dep_id else []
            doc_id = pick_doctor_id(user_text, doctors)
            if doc_id is None:
                doctor_names = [doc_name for _, doc_name in doctors]
                assistant_reply("I could not match doctor. Say one of: " + ", ".join(doctor_names), sarvam)
            else:
                st.session_state.selected_doctor_id = doc_id
                st.session_state.dialog_stage = "awaiting_slot"
                slots = get_available_slots(doc_id)
                if not slots:
                    assistant_reply("No slots available for this doctor. Say another doctor name.", sarvam)
                    st.session_state.dialog_stage = "awaiting_doctor"
                else:
                    grouped_slots = defaultdict(list)
                    for slot_id, date_value, time_value in slots:
                        grouped_slots[date_value].append((slot_id, time_value))
                    lines = []
                    for date_value in sorted(grouped_slots.keys())[:5]:
                        times = ", ".join(tm.strftime("%I:%M %p") for _, tm in grouped_slots[date_value][:5])
                        lines.append(f"{date_value.strftime('%d %b %Y')}: {times}")
                    assistant_reply(
                        "Available slots are:\n" + "\n".join(lines) + "\nSay preferred time (example: 10:00 AM).",
                        sarvam,
                    )

        elif st.session_state.dialog_stage == "awaiting_slot":
            doc_id = st.session_state.selected_doctor_id
            slots = get_available_slots(doc_id) if doc_id else []
            slot_id = pick_slot_id(user_text, slots)
            if slot_id is None:
                examples = ", ".join(
                    f"{date_value.strftime('%d %b')} {time_value.strftime('%I:%M %p')}"
                    for _, date_value, time_value in slots[:3]
                )
                assistant_reply(
                    "I could not match that slot. Please say date and time like: "
                    + examples,
                    sarvam,
                )
            else:
                st.session_state.selected_slot_id = slot_id
                st.session_state.dialog_stage = "awaiting_confirmation"
                selected_slot = next((s for s in slots if s[0] == slot_id), None)
                doctor_name = dict(get_doctors(st.session_state.selected_department_id)).get(doc_id, "selected doctor")
                if selected_slot:
                    _, date_value, time_value = selected_slot
                    assistant_reply(
                        f"Please confirm booking with {doctor_name} on {date_value.strftime('%d %b %Y')} at {time_value.strftime('%I:%M %p')}. Say yes or no.",
                        sarvam,
                    )
                else:
                    assistant_reply("Please confirm booking. Say yes or no.", sarvam)

        elif st.session_state.dialog_stage == "awaiting_confirmation":
            if is_yes(msg):
                ok, message = book_appointment(
                    user_id=st.session_state.user_id,
                    doctor_id=st.session_state.selected_doctor_id,
                    slot_id=st.session_state.selected_slot_id,
                )
                st.session_state.booking_status = message
                if ok:
                    st.session_state.dialog_stage = "completed"
                    assistant_reply("Appointment booked successfully. Say 'restart' for a new booking.", sarvam)
                else:
                    st.session_state.dialog_stage = "awaiting_slot"
                    assistant_reply(f"{message} Please choose another slot.", sarvam)
            elif is_no(msg):
                st.session_state.dialog_stage = "awaiting_slot"
                assistant_reply("Booking cancelled. Please say another preferred time.", sarvam)
            else:
                assistant_reply("Please say yes to confirm or no to cancel.", sarvam)

        elif st.session_state.dialog_stage == "completed":
            if "restart" in msg or "new" in msg:
                reset_flow()
                assistant_reply("Conversation reset. Please share phone number to login.", sarvam)
            else:
                assistant_reply("Booking is complete. Say 'restart' to begin a new booking.", sarvam)

    if st.session_state.booking_status:
        st.caption(f"Last status: {st.session_state.booking_status}")


if __name__ == "__main__":
    main()
