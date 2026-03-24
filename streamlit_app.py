from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

import streamlit as st

from db.models import Appointment, Department, Doctor, Slot, User
from db.session import SessionLocal


LANGUAGES = ["English", "Hindi", "Telugu"]

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
    st.session_state.selected_department_id = None
    st.session_state.selected_doctor_id = None
    st.session_state.selected_slot_id = None
    st.session_state.symptoms = ""
    st.session_state.booking_status = ""


def main():
    st.set_page_config(page_title="Healthcare Appointment Bot", page_icon="🩺", layout="centered")
    st.title("🩺 Healthcare Appointment UI")
    st.caption("Streamlit interface for department-based appointment booking.")

    if "language" not in st.session_state:
        st.session_state.language = LANGUAGES[0]
    if "user_phone" not in st.session_state:
        st.session_state.user_phone = ""
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "selected_department_id" not in st.session_state:
        st.session_state.selected_department_id = None
    if "selected_doctor_id" not in st.session_state:
        st.session_state.selected_doctor_id = None
    if "selected_slot_id" not in st.session_state:
        st.session_state.selected_slot_id = None
    if "symptoms" not in st.session_state:
        st.session_state.symptoms = ""
    if "booking_status" not in st.session_state:
        st.session_state.booking_status = ""

    with st.sidebar:
        st.subheader("Session")
        st.selectbox("Language", LANGUAGES, key="language")
        if st.button("Reset Booking Flow", use_container_width=True):
            reset_flow()
            st.rerun()
        if st.session_state.user_name:
            st.success(f"Signed in as {st.session_state.user_name}")

    st.subheader("1) Login")
    phone = st.text_input("Phone Number", value=st.session_state.user_phone, placeholder="e.g. 5551000001")
    if st.button("Login"):
        user = get_user_by_phone(phone.strip())
        if user:
            st.session_state.user_phone = user.phone
            st.session_state.user_name = user.name
            st.session_state.user_id = user.id
            st.success(f"Welcome, {user.name}!")
        else:
            st.error("No user found for this phone number. Seed the database or use a valid number.")

    if not st.session_state.user_id:
        st.info("Login to continue booking.")
        return

    st.subheader("2) Department selection")
    mode = st.radio(
        "Choose how you want to proceed",
        options=["Direct booking", "Book via symptoms"],
        horizontal=True,
    )

    departments = get_departments()
    if not departments:
        st.error("No departments found. Run DB initialization and seeding first.")
        return

    department_names = [name for _, name in departments]

    if mode == "Book via symptoms":
        st.session_state.symptoms = st.text_area(
            "Describe your symptoms",
            value=st.session_state.symptoms,
            placeholder="e.g. chest pain and shortness of breath since morning",
        )
        if st.button("Suggest department"):
            suggestion = infer_department_from_symptoms(st.session_state.symptoms, department_names)
            st.session_state.selected_department_id = next(dep_id for dep_id, dep_name in departments if dep_name == suggestion)
            st.success(f"Suggested department: {suggestion}")

    current_department_id = st.session_state.selected_department_id or departments[0][0]
    department_map = {dep_id: dep_name for dep_id, dep_name in departments}
    chosen_department_id = st.selectbox(
        "Department",
        options=[dep_id for dep_id, _ in departments],
        format_func=lambda dep_id: department_map[dep_id],
        index=[dep_id for dep_id, _ in departments].index(current_department_id),
    )
    st.session_state.selected_department_id = chosen_department_id

    st.subheader("3) Doctor and slot selection")
    doctors = get_doctors(chosen_department_id)
    if not doctors:
        st.warning("No doctors available in this department.")
        return

    doctor_map = {doc_id: doc_name for doc_id, doc_name in doctors}
    chosen_doctor_id = st.selectbox(
        "Doctor",
        options=[doc_id for doc_id, _ in doctors],
        format_func=lambda doc_id: doctor_map[doc_id],
    )
    st.session_state.selected_doctor_id = chosen_doctor_id

    slots = get_available_slots(chosen_doctor_id)
    if not slots:
        st.warning("No available slots for this doctor.")
        return

    grouped_slots = defaultdict(list)
    for slot_id, date_value, time_value in slots:
        grouped_slots[date_value].append((slot_id, time_value))

    date_options = sorted(grouped_slots.keys())
    selected_date = st.selectbox("Date", options=date_options, format_func=lambda d: d.strftime("%d %b %Y"))

    slot_options = grouped_slots[selected_date]
    slot_map = {slot_id: time_value.strftime("%I:%M %p") for slot_id, time_value in slot_options}
    chosen_slot_id = st.selectbox(
        "Time",
        options=[slot_id for slot_id, _ in slot_options],
        format_func=lambda slot_id: slot_map[slot_id],
    )
    st.session_state.selected_slot_id = chosen_slot_id

    doctor_name = doctor_map[chosen_doctor_id]
    selected_time = slot_map[chosen_slot_id]
    st.info(
        f"Confirm booking for **{doctor_name}** on **{selected_date.strftime('%d %b %Y')}** at **{selected_time}**."
    )

    if st.button("Book appointment", type="primary"):
        ok, message = book_appointment(
            user_id=st.session_state.user_id,
            doctor_id=chosen_doctor_id,
            slot_id=chosen_slot_id,
        )
        st.session_state.booking_status = message
        if ok:
            st.success(message)
        else:
            st.error(message)

    if st.session_state.booking_status:
        st.caption(f"Last status: {st.session_state.booking_status}")


if __name__ == "__main__":
    main()
