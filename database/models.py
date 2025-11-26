"""
Database Models for Academic Assistant
SQLAlchemy models for students, advisors, appointments, etc.
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class Student(Base):
    """Student model"""
    __tablename__ = 'students'
    
    asu_id = Column(String(20), primary_key=True)
    email = Column(String(100), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    program_level = Column(String(20), nullable=False)  # 'undergraduate' or 'graduate'
    assigned_advisor_id = Column(String(50), ForeignKey('advisors.advisor_id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="student")
    advisor = relationship("Advisor", back_populates="students")


class Advisor(Base):
    """Advisor model"""
    __tablename__ = 'advisors'
    
    advisor_id = Column(String(50), primary_key=True)  # email or unique ID
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    phone = Column(String(20), nullable=True)
    title = Column(String(100), nullable=True)
    program_level = Column(String(20), nullable=False)  # 'undergraduate' or 'graduate'
    office_location = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    students = relationship("Student", back_populates="advisor")
    appointments = relationship("Appointment", back_populates="advisor")
    calendar_slots = relationship("AdvisorCalendar", back_populates="advisor")


class Appointment(Base):
    """Appointment model"""
    __tablename__ = 'appointments'
    
    appointment_id = Column(String(50), primary_key=True)  # UUID
    student_id = Column(String(20), ForeignKey('students.asu_id'), nullable=False)
    advisor_id = Column(String(50), ForeignKey('advisors.advisor_id'), nullable=False)
    slot_datetime = Column(DateTime, nullable=False)
    status = Column(String(20), default='pending')  # 'pending', 'confirmed', 'cancelled'
    confirmation_email_sent = Column(Boolean, default=False)
    reason = Column(Text, nullable=True)  # Optional reason for appointment
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = relationship("Student", back_populates="appointments")
    advisor = relationship("Advisor", back_populates="appointments")


class AdvisorCalendar(Base):
    """Advisor calendar slots model"""
    __tablename__ = 'advisor_calendar'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_id = Column(String(50), ForeignKey('advisors.advisor_id'), nullable=False)
    slot_datetime = Column(DateTime, nullable=False)
    status = Column(String(20), default='available')  # 'available', 'booked', 'blocked'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    advisor = relationship("Advisor", back_populates="calendar_slots")
    
    # Unique constraint: one slot per advisor per datetime
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class ChatHistory(Base):
    """Chat history model"""
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False)
    student_id = Column(String(20), ForeignKey('students.asu_id'), nullable=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    message = Column(Text, nullable=False)
    message_metadata = Column(Text, nullable=True)  # JSON string for additional data (renamed from metadata - reserved word)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class Admin(Base):
    """Admin model"""
    __tablename__ = 'admins'
    
    admin_id = Column(String(50), primary_key=True)  # username or email
    email = Column(String(100), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

