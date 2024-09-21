# models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Table, Float, DateTime, Boolean
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Связующая таблица для многих-ко-многим: Специальности и Предметы
specialty_subject = Table(
    'specialty_subject', Base.metadata,
    Column('specialty_id', ForeignKey('specialties.id'), primary_key=True),
    Column('subject_id', ForeignKey('subjects.id'), primary_key=True)
)

# Связующая таблица для многих-ко-многим: Темы и Вопросы
topic_question = Table(
    'topic_question', Base.metadata,
    Column('topic_id', ForeignKey('topics.id'), primary_key=True),
    Column('question_id', ForeignKey('questions.id'), primary_key=True)
)

# Связующая таблица для многих-ко-многим: Тесты и Темы
test_topic = Table(
    'test_topic', Base.metadata,
    Column('test_id', ForeignKey('tests.id'), primary_key=True),
    Column('topic_id', ForeignKey('topics.id'), primary_key=True)
)

class Specialty(Base):
    __tablename__ = 'specialties'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    subjects = relationship('Subject', secondary=specialty_subject, back_populates='specialties')
    groups = relationship('Group', back_populates='specialty')

class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    specialties = relationship('Specialty', secondary=specialty_subject, back_populates='subjects')
    topics = relationship('Topic', back_populates='subject')

class Topic(Base):
    __tablename__ = 'topics'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    subject = relationship('Subject', back_populates='topics')
    questions = relationship('Question', secondary=topic_question, back_populates='topics')
    tests = relationship('Test', secondary=test_topic, back_populates='topics')  # Добавлено отношение

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)
    # Можно добавить дополнительные поля, например, сложность
    topics = relationship('Topic', secondary=topic_question, back_populates='questions')

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    specialty_id = Column(Integer, ForeignKey('specialties.id'))
    specialty = relationship('Specialty', back_populates='groups')
    students = relationship('Student', back_populates='group')

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship('Group', back_populates='students')
    test_results = relationship('TestResult', back_populates='student')

class Test(Base):
    __tablename__ = 'tests'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship('Group')
    topics = relationship('Topic', secondary=test_topic, back_populates='tests')
    created_at = Column(DateTime)
    test_results = relationship('TestResult', back_populates='test')
    is_shared = Column(Boolean, default=False)  # Индикатор отправлен ли тест

class TestResult(Base):
    __tablename__ = 'test_results'
    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey('tests.id'))
    student_id = Column(Integer, ForeignKey('students.id'))
    score = Column(Float, default=0.0)
    completed_at = Column(DateTime)
    test = relationship('Test', back_populates='test_results')
    student = relationship('Student', back_populates='test_results')
    # Можно добавить поля для хранения ответов
