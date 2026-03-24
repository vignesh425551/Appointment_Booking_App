from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time, create_engine
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True)
    appointments = relationship('Appointment', back_populates='user')

class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    doctors = relationship('Doctor', back_populates='department')

class Doctor(Base):
    __tablename__ = 'doctors'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    department_id = Column(Integer, ForeignKey('departments.id'))
    department = relationship('Department', back_populates='doctors')
    slots = relationship('Slot', back_populates='doctor')
    appointments = relationship('Appointment', back_populates='doctor')

class Slot(Base):
    __tablename__ = 'slots'
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey('doctors.id'))
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    is_booked = Column(Integer, default=0)  # 0 = available, 1 = booked
    doctor = relationship('Doctor', back_populates='slots')
    appointment = relationship('Appointment', back_populates='slot', uselist=False)

class Appointment(Base):
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    doctor_id = Column(Integer, ForeignKey('doctors.id'))
    slot_id = Column(Integer, ForeignKey('slots.id'))
    user = relationship('User', back_populates='appointments')
    doctor = relationship('Doctor', back_populates='appointments')
    slot = relationship('Slot', back_populates='appointment') 