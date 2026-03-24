import os
from datetime import datetime

from db.session import SessionLocal
from db.models import Department, Doctor, Slot, Appointment, User
from flows.appointment_bot_flow import AppointmentFlow


def main():
    session = SessionLocal()

    # Ensure a known user exists
    user = session.query(User).filter_by(phone="5551000001").first()
    if not user:
        raise RuntimeError("Seed data missing known user 5551000001. Please run: python -m db.seed_data")

    # Pick a department with doctors and future slots
    department_name = "Dermatology"
    department = session.query(Department).filter(Department.name == department_name).first()
    if not department:
        raise RuntimeError(f"Department not found: {department_name}")

    doctor = session.query(Doctor).filter(Doctor.department_id == department.id).first()
    if not doctor:
        raise RuntimeError(f"No doctors found in department: {department_name}")

    slot = (
        session.query(Slot)
        .filter(Slot.doctor_id == doctor.id, Slot.is_booked == 0, Slot.date >= datetime.now().date())
        .order_by(Slot.date, Slot.time)
        .first()
    )
    if not slot:
        raise RuntimeError(f"No available future slots for doctor: {doctor.name}")

    # Instantiate flow with English
    flow = AppointmentFlow(language_config={"code": "en-US"})
    flow.db = session  # reuse same session for ease
    flow.user_id = user.id
    flow.user_symptoms = department_name  # used for direct booking path

    # Monkeypatch voice and LLM-dependent methods to be deterministic
    flow.log_and_speak = lambda msg: print(f"[BOT]: {msg}")
    flow.log_and_get_voice_input = lambda prompt=None: ""
    flow.select_doctor = lambda doctors: doctor
    flow.get_available_doctors = lambda dept: [doctor]
    flow.get_available_slots = lambda doctor_id: [slot]
    flow.select_date_time = lambda slots: slot
    flow.confirm_booking = lambda doc, s: True

    print(f"Attempting to book: user={user.name}, dept={department_name}, doctor={doctor.name}, slot={slot.date} {slot.time}")
    result = flow.offer_appointment(direct=True)
    print(f"Result: {result}")

    # Verify appointment created and slot booked
    created = (
        session.query(Appointment)
        .filter(Appointment.user_id == user.id, Appointment.doctor_id == doctor.id, Appointment.slot_id == slot.id)
        .order_by(Appointment.id.desc())
        .first()
    )
    slot_refreshed = session.query(Slot).get(slot.id)

    assert created is not None, "Appointment was not created"
    assert slot_refreshed.is_booked == 1, "Slot was not marked as booked"

    print("Smoke test passed: appointment created and slot booked.")


if __name__ == "__main__":
    main()