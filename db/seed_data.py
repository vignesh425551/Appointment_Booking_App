from db.models import Base, Department, Doctor, Slot, User
from db.session import SessionLocal, engine
from datetime import datetime, timedelta
from sqlalchemy import text

def clear_db(session):
    # Truncate in order to avoid FK issues
    session.execute(text('TRUNCATE TABLE appointments RESTART IDENTITY CASCADE'))
    session.execute(text('TRUNCATE TABLE slots RESTART IDENTITY CASCADE'))
    session.execute(text('TRUNCATE TABLE doctors RESTART IDENTITY CASCADE'))
    session.execute(text('TRUNCATE TABLE departments RESTART IDENTITY CASCADE'))
    session.execute(text('TRUNCATE TABLE users RESTART IDENTITY CASCADE'))
    session.commit()

def seed():
    session = SessionLocal()
    clear_db(session)
    # Define departments
    departments = [
        "Gastroenterology", "Cardiology", "Dermatology", "Orthopedics", "Pediatrics", "Neurology", "ENT", "General Medicine"
    ]
    dept_objs = {}
    for dept in departments:
        d = Department(name=dept)
        session.add(d)
        dept_objs[dept] = d
    session.commit()

    # Add sample users
    users_data = [
        {"name": "Vignesh", "phone": "5551000001"},
        {"name": "Akhila", "phone": "5551000002"},
        {"name": "Shreya", "phone": "5551000003"},
        {"name": "Meghana", "phone": "5551000004"},
        {"name": "Vaishno", "phone": "5551000005"},
        {"name": "Koushik", "phone": "5551000006"},
        {"name": "Prajith", "phone": "5551000007"},
        {"name": "Vivek", "phone": "5551000008"},

        {"name": "Chandu", "phone": "5551000009"},
        {"name": "Lokesh", "phone": "5551000010"}
    ]
    for user in users_data:
        session.add(User(name=user["name"], phone=user["phone"]))
    session.commit()

    # Doctor and slot data (from doctor_db.py, normalized)
    doctors_data = [
        {"name": "Dr. Gupta", "department": "Gastroenterology", "availability": [{"date": "2025-05-11", "slots": ["10:00", "14:00"]}]},
        {"name": "Dr. Rao", "department": "Gastroenterology", "availability": [{"date": "2025-05-13", "slots": ["10:30", "11:30"]}]},
        {"name": "Dr. Mohan", "department": "Gastroenterology", "availability": [{"date": "2025-05-15", "slots": ["09:00", "11:00"]}]},
        {"name": "Dr. Bhaskar", "department": "Gastroenterology", "availability": [{"date": "2025-05-14", "slots": ["14:00", "15:00"]}]},
        {"name": "Dr. Sinha", "department": "Gastroenterology", "availability": [{"date": "2025-05-16", "slots": ["10:00", "13:00"]}]},
        {"name": "Dr. Kiran", "department": "Gastroenterology", "availability": [{"date": "2025-05-17", "slots": ["09:30", "12:00"]}]},
        {"name": "Dr. Malhotra", "department": "Gastroenterology", "availability": [{"date": "2025-05-18", "slots": ["10:00", "11:30"]}]},
        {"name": "Dr. Sharma", "department": "Cardiology", "availability": [{"date": "2025-05-08", "slots": ["10:00", "11:00"]}]},
        {"name": "Dr. Mehta", "department": "Cardiology", "availability": [{"date": "2025-05-10", "slots": ["11:00", "12:00"]}]},
        {"name": "Dr. Pillai", "department": "Cardiology", "availability": [{"date": "2025-05-12", "slots": ["09:00", "13:00"]}]},
        {"name": "Dr. Raghav", "department": "Cardiology", "availability": [{"date": "2025-05-13", "slots": ["10:00", "14:00"]}]},
        {"name": "Dr. Shinde", "department": "Cardiology", "availability": [{"date": "2025-05-14", "slots": ["11:00", "15:00"]}]},
        {"name": "Dr. Bajaj", "department": "Cardiology", "availability": [{"date": "2025-05-15", "slots": ["09:30", "12:00"]}]},
        {"name": "Dr. Tyagi", "department": "Cardiology", "availability": [{"date": "2025-05-16", "slots": ["10:30", "13:00"]}]},
        {"name": "Dr. Verma", "department": "Dermatology", "availability": [{"date": "2025-05-08", "slots": ["09:30", "13:00"]}]},
        {"name": "Dr. Kapoor", "department": "Dermatology", "availability": [{"date": "2025-05-09", "slots": ["10:00", "11:30"]}]},
        {"name": "Dr. Roy", "department": "Dermatology", "availability": [{"date": "2025-05-10", "slots": ["10:00", "12:00"]}]},
        {"name": "Dr. Suresh", "department": "Dermatology", "availability": [{"date": "2025-05-11", "slots": ["11:00", "14:00"]}]},
        {"name": "Dr. Iqbal", "department": "Dermatology", "availability": [{"date": "2025-05-12", "slots": ["09:00", "10:30"]}]},
        {"name": "Dr. Fernandes", "department": "Dermatology", "availability": [{"date": "2025-05-13", "slots": ["12:00", "14:00"]}]},
        {"name": "Dr. Rao", "department": "Dermatology", "availability": [{"date": "2025-05-14", "slots": ["10:30", "13:30"]}]},
        {"name": "Dr. Deshmukh", "department": "Orthopedics", "availability": [{"date": "2025-05-08", "slots": ["09:00", "10:00"]}]},
        {"name": "Dr. Rao", "department": "Orthopedics", "availability": [{"date": "2025-05-09", "slots": ["10:00", "11:30"]}]},
        {"name": "Dr. Sen", "department": "Orthopedics", "availability": [{"date": "2025-05-10", "slots": ["14:00", "15:00"]}]},
        {"name": "Dr. Lal", "department": "Orthopedics", "availability": [{"date": "2025-05-11", "slots": ["09:30", "10:30"]}]},
        {"name": "Dr. Saxena", "department": "Orthopedics", "availability": [{"date": "2025-05-12", "slots": ["10:00", "11:00"]}]},
        {"name": "Dr. Khanna", "department": "Orthopedics", "availability": [{"date": "2025-05-13", "slots": ["11:00", "13:00"]}]},
        {"name": "Dr. Abraham", "department": "Orthopedics", "availability": [{"date": "2025-05-14", "slots": ["09:00", "12:00"]}]},
        {"name": "Dr. Iyer", "department": "Pediatrics", "availability": [{"date": "2025-05-08", "slots": ["08:00", "09:00"]}]},
        {"name": "Dr. Rani", "department": "Pediatrics", "availability": [{"date": "2025-05-09", "slots": ["10:00", "12:00"]}]},
        {"name": "Dr. Arjun", "department": "Pediatrics", "availability": [{"date": "2025-05-10", "slots": ["11:00", "12:00"]}]},
        {"name": "Dr. Joshi", "department": "Pediatrics", "availability": [{"date": "2025-05-11", "slots": ["13:00", "14:30"]}]},
        {"name": "Dr. Kamal", "department": "Pediatrics", "availability": [{"date": "2025-05-12", "slots": ["09:00", "11:00"]}]},
        {"name": "Dr. Zaveri", "department": "Pediatrics", "availability": [{"date": "2025-05-13", "slots": ["10:30", "12:00"]}]},
        {"name": "Dr. Dev", "department": "Pediatrics", "availability": [{"date": "2025-05-14", "slots": ["11:00", "13:00"]}]},
        {"name": "Dr. Singh", "department": "Neurology", "availability": [{"date": "2025-05-08", "slots": ["09:00", "10:00"]}]},
        {"name": "Dr. Bose", "department": "Neurology", "availability": [{"date": "2025-05-09", "slots": ["11:00", "13:00"]}]},
        {"name": "Dr. Ram", "department": "Neurology", "availability": [{"date": "2025-05-10", "slots": ["10:00", "11:30"]}]},
        {"name": "Dr. Jain", "department": "Neurology", "availability": [{"date": "2025-05-11", "slots": ["09:30", "11:30"]}]},
        {"name": "Dr. Dubey", "department": "Neurology", "availability": [{"date": "2025-05-12", "slots": ["13:00", "14:00"]}]},
        {"name": "Dr. Krishnan", "department": "Neurology", "availability": [{"date": "2025-05-13", "slots": ["10:00", "12:00"]}]},
        {"name": "Dr. Ghosh", "department": "Neurology", "availability": [{"date": "2025-05-14", "slots": ["11:00", "12:30"]}]},
        {"name": "Dr. Das", "department": "ENT", "availability": [{"date": "2025-05-08", "slots": ["09:30", "10:30"]}]},
        {"name": "Dr. Joseph", "department": "ENT", "availability": [{"date": "2025-05-09", "slots": ["11:00", "12:00"]}]},
        {"name": "Dr. Neha", "department": "ENT", "availability": [{"date": "2025-05-10", "slots": ["10:00", "11:30"]}]},
        {"name": "Dr. Ajay", "department": "ENT", "availability": [{"date": "2025-05-11", "slots": ["13:00", "14:00"]}]},
        {"name": "Dr. Thomas", "department": "ENT", "availability": [{"date": "2025-05-12", "slots": ["08:30", "10:00"]}]},
        {"name": "Dr. Swati", "department": "ENT", "availability": [{"date": "2025-05-13", "slots": ["10:00", "11:00"]}]},
        {"name": "Dr. Pal", "department": "ENT", "availability": [{"date": "2025-05-14", "slots": ["10:00", "12:00"]}]},
        {"name": "Dr. Nair", "department": "General Medicine", "availability": [{"date": "2025-05-15", "slots": ["08:00", "09:30"]}]},
        {"name": "Dr. Desai", "department": "General Medicine", "availability": [{"date": "2025-05-16", "slots": ["10:00", "12:00"]}]},
        {"name": "Dr. Banerjee", "department": "General Medicine", "availability": [{"date": "2025-05-17", "slots": ["09:00", "11:00"]}]},
        {"name": "Dr. Kale", "department": "General Medicine", "availability": [{"date": "2025-05-18", "slots": ["08:30", "10:30"]}]},
        {"name": "Dr. Mishra", "department": "General Medicine", "availability": [{"date": "2025-05-19", "slots": ["09:00", "11:00"]}]},
        {"name": "Dr. Goswami", "department": "General Medicine", "availability": [{"date": "2025-05-20", "slots": ["08:00", "09:00"]}]},
        {"name": "Dr. Patil", "department": "General Medicine", "availability": [{"date": "2025-05-21", "slots": ["10:00", "11:00"]}]}
    ]
    doctor_objs = {}
    for doc in doctors_data:
        d = Doctor(name=doc["name"], department=dept_objs[doc["department"]])
        session.add(d)
        doctor_objs[doc["name"]] = d
    session.commit()

    # Add slots for each doctor with dates relative to today (next 7-21 days)
    base_day = datetime.now().date()
    day_offsets = [3, 5, 7, 10, 12, 14, 18, 21]
    for doc in doctors_data:
        doctor = doctor_objs[doc["name"]]
        # Use the times from the first availability entry as templates
        times = []
        if doc["availability"]:
            for t in doc["availability"][0]["slots"]:
                times.append(datetime.strptime(t, "%H:%M").time())
        if not times:
            times = [datetime.strptime("10:00", "%H:%M").time(), datetime.strptime("14:00", "%H:%M").time()]
        for offset in day_offsets:
            date = base_day + timedelta(days=offset)
            for tm in times:
                slot = Slot(doctor=doctor, date=date, time=tm)
                session.add(slot)
    session.commit()
    session.close()

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed()
    print("Database seeded with departments, doctors, and slots.") 