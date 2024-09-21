# create_db.py
from database import init_db, SessionLocal
from models import Specialty, Subject, Topic, Question, Group, Student
from datetime import datetime


def populate_initial_data():
    session = SessionLocal()

    # Проверка, если данные уже существуют, чтобы избежать дублирования
    if session.query(Specialty).first():
        print("Данные уже инициализированы.")
        session.close()
        return

    # Добавление специальностей
    specialty1 = Specialty(name='Информатика')
    specialty2 = Specialty(name='Математика')

    session.add_all([specialty1, specialty2])
    session.commit()

    # Добавление предметов
    subject1 = Subject(name='Алгоритмы')
    subject2 = Subject(name='Математический анализ')
    subject3 = Subject(name='Физика')

    session.add_all([subject1, subject2, subject3])
    session.commit()

    # Связь специальностей и предметов
    specialty1.subjects.extend([subject1, subject3])
    specialty2.subjects.append(subject2)
    session.commit()

    # Добавление тем
    topic1 = Topic(name='Сортировки', subject=subject1)
    topic2 = Topic(name='Пределы', subject=subject2)
    topic3 = Topic(name='Кинематика', subject=subject3)

    session.add_all([topic1, topic2, topic3])
    session.commit()

    # Добавление вопросов
    question1 = Question(
        text='Что такое быстрая сортировка?',
        correct_answer='Алгоритм сортировки разделением.'
    )
    question2 = Question(
        text='Определите предел последовательности.',
        correct_answer='Число, к которому стремится последовательность.'
    )
    question3 = Question(
        text='Что такое ускорение в кинематике?',
        correct_answer='Производная скорости по времени.'
    )

    session.add_all([question1, question2, question3])
    session.commit()

    # Связь тем и вопросов
    topic1.questions.append(question1)
    topic2.questions.append(question2)
    topic3.questions.append(question3)
    session.commit()

    # Добавление групп
    group1 = Group(name='ИФ-101', specialty=specialty1)
    group2 = Group(name='М-201', specialty=specialty2)

    session.add_all([group1, group2])
    session.commit()

    # Добавление студентов
    student1 = Student(telegram_id=123456789, name='Иван Иванов', group=group1)
    student2 = Student(telegram_id=987654321, name='Мария Петрова', group=group1)
    student3 = Student(telegram_id=192837465, name='Алексей Смирнов', group=group2)

    session.add_all([student1, student2, student3])
    session.commit()

    session.close()


if __name__ == '__main__':
    init_db()
    populate_initial_data()
    print("База данных инициализирована и заполнена начальными данными.")
