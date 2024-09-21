import logging
from telegram import (
    ReplyKeyboardMarkup,
    Update,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)
from database import SessionLocal
from models import (
    Specialty,
    Subject,
    Topic,
    Question,
    Group,
    Student,
    Test,
    TestResult,
    topic_question,
    specialty_subject,
    test_topic
)
from datetime import datetime
import random
from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states for ConversationHandler
# Registration
REGISTER_NAME, REGISTER_GROUP = range(2)

# Test Generation
GENERATE_TEST_SELECT_GROUP, GENERATE_TEST_SELECT_TOPIC, GENERATE_TEST_SELECT_TYPE = range(2, 5)

# Administrative commands
ADMIN_ADD_SPECIALTY, ADMIN_ADD_SUBJECT_SELECT_SPECIALTY, ADMIN_ADD_SUBJECT_NAME = range(5, 8)
ADMIN_ADD_TOPIC_SELECT_SUBJECT, ADMIN_ADD_TOPIC_NAME = range(8, 10)
ADMIN_ADD_QUESTION_SELECT_TOPIC, ADMIN_ADD_QUESTION_TEXT, ADMIN_ADD_QUESTION_ANSWER = range(10, 13)
ADMIN_ADD_GROUP_SELECT_SPECIALTY, ADMIN_ADD_GROUP_NAME = range(13, 15)

# Check if user is admin
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Handler for /start command with buttons for main actions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with SessionLocal() as session:
        student = session.query(Student).filter_by(telegram_id=user.id).first()

        # Define keyboard based on user registration
        if not student:
            keyboard = [['Регистрация']]
        else:
            keyboard = [['Мои результаты'], ['Создать тест']]

        # Add admin commands if user is admin
        if is_admin(user.id):
            keyboard.append(['Админ-панель'])

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    if not student:
        await update.message.reply_text(
            "Привет! Для начала регистрации нажми на кнопку 'Регистрация'.",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Привет! Выберите действие:",
            reply_markup=reply_markup
        )

# Handler to start registration
async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пожалуйста, введите ваше имя:",
        reply_markup=ReplyKeyboardRemove()
    )
    return REGISTER_NAME

# Handler for entering name during registration
async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Имя не может быть пустым. Пожалуйста, введите ваше имя:")
        return REGISTER_NAME

    context.user_data['student_name'] = name

    with SessionLocal() as session:
        groups = session.query(Group).all()

        if not groups:
            await update.message.reply_text("Группы не найдены. Обратитесь к администратору.")
            return ConversationHandler.END

        # Create keyboard with group names
        keyboard = [[group.name] for group in groups]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите вашу группу:",
        reply_markup=reply_markup
    )
    return REGISTER_GROUP

# Handler for selecting group during registration
async def register_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_name = update.message.text.strip()
    with SessionLocal() as session:
        group = session.query(Group).filter_by(name=group_name).first()

        if not group:
            # If group not found, prompt to select again
            groups = session.query(Group).all()
            if not groups:
                await update.message.reply_text("Группы не найдены. Обратитесь к администратору.")
                return ConversationHandler.END

            keyboard = [[group.name] for group in groups]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Группа не найдена. Пожалуйста, выберите группу из списка:",
                reply_markup=reply_markup
            )
            return REGISTER_GROUP

        name = context.user_data['student_name']
        student = Student(
            telegram_id=update.effective_user.id,
            name=name,
            group=group
        )
        session.add(student)
        session.commit()

    await update.message.reply_text(
        f"Регистрация завершена! Привет, {name} из группы {group.name}.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# Handler for "My Results" command
async def my_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with SessionLocal() as session:
        student = session.query(Student).filter_by(telegram_id=user.id).first()

        if not student:
            # If user not registered, prompt to register
            keyboard = [['Регистрация']]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Вы не зарегистрированы. Для регистрации нажмите кнопку 'Регистрация'.",
                reply_markup=reply_markup
            )
            return

        results = session.query(TestResult).filter_by(student_id=student.id).all()

        if not results:
            await update.message.reply_text("У вас пока нет результатов тестов.")
            return

        message = "Ваши результаты тестов:\n"
        for result in results:
            message += f"Тест #{result.test_id}: {result.score} баллов, сдан {result.completed_at.strftime('%Y-%m-%d %H:%M')}\n"

    await update.message.reply_text(message)

# Handler to start test generation
async def generate_test_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with SessionLocal() as session:
        student = session.query(Student).filter_by(telegram_id=user.id).first()

        if not student:
            # If user not registered, prompt to register
            keyboard = [['Регистрация']]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Вы не зарегистрированы. Для регистрации нажмите кнопку 'Регистрация'.",
                reply_markup=reply_markup
            )
            return ConversationHandler.END

        # Get groups for student's specialty
        groups = session.query(Group).filter_by(specialty_id=student.group.specialty_id).all()

        if not groups:
            await update.message.reply_text("Группы не найдены. Обратитесь к администратору.")
            return ConversationHandler.END

        # Create keyboard with group names
        keyboard = [[group.name] for group in groups]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите группу для создания теста:",
        reply_markup=reply_markup
    )
    context.user_data['test_specialty_id'] = student.group.specialty_id
    return GENERATE_TEST_SELECT_GROUP

# Handler for selecting group during test generation
async def generate_test_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_name = update.message.text.strip()
    with SessionLocal() as session:
        group = session.query(Group).filter_by(name=group_name).first()

        if not group:
            # If group not found, prompt to select again
            groups = session.query(Group).filter_by(specialty_id=context.user_data['test_specialty_id']).all()
            if not groups:
                await update.message.reply_text("Группы не найдены. Обратитесь к администратору.")
                return ConversationHandler.END

            keyboard = [[group.name] for group in groups]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Группа не найдена. Пожалуйста, выберите группу из списка:",
                reply_markup=reply_markup
            )
            return GENERATE_TEST_SELECT_GROUP

        context.user_data['test_group_id'] = group.id

        # Get topics for the selected group
        topics = session.query(Topic).join(Subject).filter(
            Subject.id == Topic.subject_id,
            Subject.specialties.any(id=group.specialty_id)
        ).all()

        if not topics:
            await update.message.reply_text("Темы не найдены для выбранной группы. Обратитесь к администратору.")
            return ConversationHandler.END

        # Create keyboard with topic names
        keyboard = [[topic.name] for topic in topics]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите тему для теста:",
        reply_markup=reply_markup
    )
    return GENERATE_TEST_SELECT_TOPIC

# Handler for selecting topic during test generation
async def generate_test_select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic_name = update.message.text.strip()
    with SessionLocal() as session:
        topic = session.query(Topic).filter_by(name=topic_name).first()

        if not topic:
            # If topic not found, prompt to select again
            group_id = context.user_data['test_group_id']
            group = session.query(Group).filter_by(id=group_id).first()
            topics = session.query(Topic).join(Subject).filter(
                Subject.id == Topic.subject_id,
                Subject.specialties.any(id=group.specialty_id)
            ).all()

            keyboard = [[topic.name] for topic in topics]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Тема не найдена. Пожалуйста, выберите тему из списка:",
                reply_markup=reply_markup
            )
            return GENERATE_TEST_SELECT_TOPIC

        context.user_data['test_topic_id'] = topic.id

    # Create keyboard for selecting test type
    keyboard = [['Одинаковый набор', 'Уникальные наборы']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите тип теста:",
        reply_markup=reply_markup
    )
    return GENERATE_TEST_SELECT_TYPE

# Handler for selecting test type during test generation
async def generate_test_select_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip()
    group_id = context.user_data['test_group_id']
    topic_id = context.user_data['test_topic_id']

    with SessionLocal() as session:
        # Get all questions for the selected topic
        questions = session.query(Question).join(topic_question).filter(topic_question.c.topic_id == topic_id).all()

        if not questions:
            await update.message.reply_text("Вопросы для выбранной темы не найдены.")
            return ConversationHandler.END

        if choice == 'Одинаковый набор':
            # Create one test for the entire group
            test = Test(
                group_id=group_id,
                created_at=datetime.now(),
                is_shared=True  # Indicates that the test is shared for the group
            )
            test.topics.append(session.get(Topic, topic_id))
            session.add(test)
            session.commit()

            # Select a fixed set of questions (e.g., randomly)
            selected_questions = random.sample(questions, min(10, len(questions)))

            # Get all students in the group
            students = session.query(Student).filter_by(group_id=group_id).all()

            for student in students:
                await send_test_to_student(student, test, selected_questions, context)

            await update.message.reply_text("Тест создан и отправлен группе.")

        elif choice == 'Уникальные наборы':
            # Create unique tests for each student
            students = session.query(Student).filter_by(group_id=group_id).all()
            for student in students:
                test = Test(
                    group_id=group_id,
                    created_at=datetime.now(),
                    is_shared=False  # Indicates that the test is unique
                )
                test.topics.append(session.get(Topic, topic_id))
                session.add(test)
                session.commit()

                # Select a random set of questions for each student
                selected_questions = random.sample(questions, min(10, len(questions)))

                await send_test_to_student(student, test, selected_questions, context)

            await update.message.reply_text("Уникальные тесты созданы и отправлены студентам.")

        else:
            await update.message.reply_text("Неверный выбор типа теста.")

    return ConversationHandler.END

# Function to send test to a student
async def send_test_to_student(student, test, questions, context: ContextTypes.DEFAULT_TYPE):
    message = f"Тест #{test.id}\n"
    for idx, question in enumerate(questions, 1):
        message += f"{idx}. {question.text}\n"

    try:
        await context.bot.send_message(chat_id=student.telegram_id, text=message)
    except Exception as e:
        logger.error(f"Не удалось отправить тест студенту {student.name} (ID: {student.telegram_id}): {e}")

# Handler for /cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Действие отменено.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# Administrative commands handlers

# Handler to start adding a specialty
async def admin_add_specialty_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Введите название специальности:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADMIN_ADD_SPECIALTY

# Handler for entering specialty name
async def admin_add_specialty_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    specialty_name = update.message.text.strip()

    if not specialty_name:
        await update.message.reply_text("Название специальности не может быть пустым. Пожалуйста, введите название специальности:")
        return ADMIN_ADD_SPECIALTY

    try:
        with SessionLocal() as session:
            existing = session.query(Specialty).filter_by(name=specialty_name).first()

            if existing:
                await update.message.reply_text("Специальность с таким названием уже существует.")
                return ConversationHandler.END

            new_specialty = Specialty(name=specialty_name)
            session.add(new_specialty)
            session.commit()

        await update.message.reply_text(f"Специальность '{specialty_name}' добавлена.")
    except Exception as e:
        logger.error(f"Error adding specialty: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении специальности. Попробуйте снова.")
    return ConversationHandler.END

# Handler to start adding a subject
async def admin_add_subject_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return ConversationHandler.END

    with SessionLocal() as session:
        specialties = session.query(Specialty).all()

        if not specialties:
            await update.message.reply_text("Специальности не найдены. Сначала добавьте специальность.")
            return ConversationHandler.END

        # Create keyboard with specialty names
        keyboard = [[specialty.name] for specialty in specialties]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите специальность, к которой будет относиться предмет:",
        reply_markup=reply_markup
    )
    return ADMIN_ADD_SUBJECT_SELECT_SPECIALTY

# Handler for selecting specialty when adding a subject
async def admin_add_subject_select_specialty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    specialty_name = update.message.text.strip()
    with SessionLocal() as session:
        specialty = session.query(Specialty).filter_by(name=specialty_name).first()

        if not specialty:
            specialties = session.query(Specialty).all()
            keyboard = [[specialty.name] for specialty in specialties]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Специальность не найдена. Пожалуйста, выберите специальность из списка:",
                reply_markup=reply_markup
            )
            return ADMIN_ADD_SUBJECT_SELECT_SPECIALTY

        context.user_data['admin_selected_specialty_id'] = specialty.id
        specialty_name = specialty.name  # Store for later use if needed

    await update.message.reply_text(
        "Введите название предмета:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADMIN_ADD_SUBJECT_NAME

# Handler for entering subject name
async def admin_add_subject_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject_name = update.message.text.strip()
    specialty_id = context.user_data.get('admin_selected_specialty_id')

    if not subject_name:
        await update.message.reply_text("Название предмета не может быть пустым. Пожалуйста, введите название предмета:")
        return ADMIN_ADD_SUBJECT_NAME

    try:
        with SessionLocal() as session:
            existing = session.query(Subject).filter_by(name=subject_name).first()

            if existing:
                await update.message.reply_text("Предмет с таким названием уже существует.")
                return ConversationHandler.END

            new_subject = Subject(name=subject_name)
            # Associate subject with the selected specialty
            specialty = session.get(Specialty, specialty_id)
            if not specialty:
                await update.message.reply_text("Специальность не найдена. Пожалуйста, попробуйте снова.")
                return ConversationHandler.END

            specialty.subjects.append(new_subject)
            session.add(new_subject)
            session.commit()

            # Store specialty name before closing session
            specialty_name = specialty.name

        await update.message.reply_text(f"Предмет '{subject_name}' добавлен к специальности '{specialty_name}'.")
    except Exception as e:
        logger.error(f"Error adding subject: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении предмета. Попробуйте снова.")
    return ConversationHandler.END

# Handler to start adding a topic
async def admin_add_topic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return ConversationHandler.END

    with SessionLocal() as session:
        subjects = session.query(Subject).all()

        if not subjects:
            await update.message.reply_text("Предметы не найдены. Сначала добавьте предмет.")
            return ConversationHandler.END

        # Create keyboard with subject names
        keyboard = [[subject.name] for subject in subjects]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите предмет, к которому будет относиться тема:",
        reply_markup=reply_markup
    )
    return ADMIN_ADD_TOPIC_SELECT_SUBJECT

# Handler for selecting subject when adding a topic
async def admin_add_topic_select_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject_name = update.message.text.strip()
    with SessionLocal() as session:
        subject = session.query(Subject).filter_by(name=subject_name).first()

        if not subject:
            subjects = session.query(Subject).all()
            keyboard = [[subject.name] for subject in subjects]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Предмет не найден. Пожалуйста, выберите предмет из списка:",
                reply_markup=reply_markup
            )
            return ADMIN_ADD_TOPIC_SELECT_SUBJECT

        context.user_data['admin_selected_subject_id'] = subject.id
        subject_name = subject.name  # Store for later use if needed

    await update.message.reply_text(
        "Введите название темы:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADMIN_ADD_TOPIC_NAME

# Handler for entering topic name
async def admin_add_topic_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic_name = update.message.text.strip()
    subject_id = context.user_data.get('admin_selected_subject_id')

    if not topic_name:
        await update.message.reply_text("Название темы не может быть пустым. Пожалуйста, введите название темы:")
        return ADMIN_ADD_TOPIC_NAME

    try:
        with SessionLocal() as session:
            existing = session.query(Topic).filter_by(name=topic_name, subject_id=subject_id).first()

            if existing:
                await update.message.reply_text("Тема с таким названием уже существует для выбранного предмета.")
                return ConversationHandler.END

            new_topic = Topic(name=topic_name, subject_id=subject_id)
            session.add(new_topic)
            session.commit()

            await update.message.reply_text(f"Тема '{topic_name}' добавлена к предмету.")
    except Exception as e:
        logger.error(f"Error adding topic: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении темы. Попробуйте снова.")
    return ConversationHandler.END

# Handler to start adding a question
async def admin_add_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return ConversationHandler.END

    with SessionLocal() as session:
        topics = session.query(Topic).all()

        if not topics:
            await update.message.reply_text("Темы не найдены. Сначала добавьте тему.")
            return ConversationHandler.END

        # Create keyboard with topic names
        keyboard = [[topic.name] for topic in topics]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите тему, к которой будет относиться вопрос:",
        reply_markup=reply_markup
    )
    return ADMIN_ADD_QUESTION_SELECT_TOPIC

# Handler for selecting topic when adding a question
async def admin_add_question_select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic_name = update.message.text.strip()
    with SessionLocal() as session:
        topic = session.query(Topic).filter_by(name=topic_name).first()

        if not topic:
            topics = session.query(Topic).all()
            keyboard = [[topic.name] for topic in topics]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Тема не найдена. Пожалуйста, выберите тему из списка:",
                reply_markup=reply_markup
            )
            return ADMIN_ADD_QUESTION_SELECT_TOPIC

        context.user_data['admin_selected_question_topic_id'] = topic.id
        topic_name = topic.name  # Store for later use if needed

    await update.message.reply_text(
        "Введите текст вопроса:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADMIN_ADD_QUESTION_TEXT

# Handler for entering question text
async def admin_add_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_text = update.message.text.strip()
    if not question_text:
        await update.message.reply_text("Текст вопроса не может быть пустым. Пожалуйста, введите текст вопроса:")
        return ADMIN_ADD_QUESTION_TEXT

    context.user_data['admin_question_text'] = question_text
    await update.message.reply_text(
        "Введите правильный ответ на вопрос:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADMIN_ADD_QUESTION_ANSWER

# Handler for entering correct answer to question
async def admin_add_question_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    correct_answer = update.message.text.strip()
    if not correct_answer:
        await update.message.reply_text("Ответ не может быть пустым. Пожалуйста, введите правильный ответ:")
        return ADMIN_ADD_QUESTION_ANSWER

    question_text = context.user_data.get('admin_question_text')
    topic_id = context.user_data.get('admin_selected_question_topic_id')

    try:
        with SessionLocal() as session:
            new_question = Question(
                text=question_text,
                correct_answer=correct_answer
            )
            topic = session.get(Topic, topic_id)
            if not topic:
                await update.message.reply_text("Тема не найдена. Пожалуйста, попробуйте снова.")
                return ConversationHandler.END

            new_question.topics.append(topic)
            session.add(new_question)
            session.commit()

            await update.message.reply_text(f"Вопрос '{question_text}' добавлен к теме.")
    except Exception as e:
        logger.error(f"Error adding question: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении вопроса. Попробуйте снова.")
    return ConversationHandler.END

# Handler to start adding a group
async def admin_add_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return ConversationHandler.END

    with SessionLocal() as session:
        specialties = session.query(Specialty).all()

        if not specialties:
            await update.message.reply_text("Специальности не найдены. Сначала добавьте специальность.")
            return ConversationHandler.END

        # Create keyboard with specialty names
        keyboard = [[specialty.name] for specialty in specialties]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите специальность, к которой будет относиться группа:",
        reply_markup=reply_markup
    )
    return ADMIN_ADD_GROUP_SELECT_SPECIALTY

# Handler for selecting specialty when adding a group
async def admin_add_group_select_specialty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    specialty_name = update.message.text.strip()
    with SessionLocal() as session:
        specialty = session.query(Specialty).filter_by(name=specialty_name).first()

        if not specialty:
            specialties = session.query(Specialty).all()
            keyboard = [[specialty.name] for specialty in specialties]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Специальность не найдена. Пожалуйста, выберите специальность из списка:",
                reply_markup=reply_markup
            )
            return ADMIN_ADD_GROUP_SELECT_SPECIALTY

        context.user_data['admin_selected_group_specialty_id'] = specialty.id
        specialty_name = specialty.name  # Store for later use if needed

    await update.message.reply_text(
        "Введите название группы:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADMIN_ADD_GROUP_NAME

# Handler for entering group name
async def admin_add_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_name = update.message.text.strip()
    specialty_id = context.user_data.get('admin_selected_group_specialty_id')

    if not group_name:
        await update.message.reply_text("Название группы не может быть пустым. Пожалуйста, введите название группы:")
        return ADMIN_ADD_GROUP_NAME

    try:
        with SessionLocal() as session:
            existing = session.query(Group).filter_by(name=group_name).first()

            if existing:
                await update.message.reply_text("Группа с таким названием уже существует.")
                return ConversationHandler.END

            new_group = Group(
                name=group_name,
                specialty_id=specialty_id
            )
            session.add(new_group)
            session.commit()

            await update.message.reply_text(f"Группа '{group_name}' добавлена к специальности.")
    except Exception as e:
        logger.error(f"Error adding group: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении группы. Попробуйте снова.")
    return ConversationHandler.END

# Handler for Admin Panel
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return

    keyboard = [
        ['Добавить специальность', 'Добавить предмет'],
        ['Добавить тему', 'Добавить вопрос'],
        ['Добавить группу']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Админ-панель. Выберите действие:",
        reply_markup=reply_markup
    )

# Handler for administrative actions via buttons
async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.message.text.strip()
    if action == 'Добавить специальность':
        return await admin_add_specialty_start(update, context)
    elif action == 'Добавить предмет':
        return await admin_add_subject_start(update, context)
    elif action == 'Добавить тему':
        return await admin_add_topic_start(update, context)
    elif action == 'Добавить вопрос':
        return await admin_add_question_start(update, context)
    elif action == 'Добавить группу':
        return await admin_add_group_start(update, context)
    else:
        await update.message.reply_text("Неизвестная команда.")
        return ConversationHandler.END

# ConversationHandler for registration
registration_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Регистрация$'), handle_registration)],
    states={
        REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
        REGISTER_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_group)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# ConversationHandler for test generation
generate_test_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Создать тест$'), generate_test_start)],
    states={
        GENERATE_TEST_SELECT_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_test_select_group)],
        GENERATE_TEST_SELECT_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_test_select_topic)],
        GENERATE_TEST_SELECT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_test_select_type)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# ConversationHandler for adding specialty
admin_add_specialty_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Добавить специальность$'), admin_add_specialty_start)],
    states={
        ADMIN_ADD_SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_specialty_name)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# ConversationHandler for adding subject
admin_add_subject_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Добавить предмет$'), admin_add_subject_start)],
    states={
        ADMIN_ADD_SUBJECT_SELECT_SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_subject_select_specialty)],
        ADMIN_ADD_SUBJECT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_subject_name)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# ConversationHandler for adding topic
admin_add_topic_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Добавить тему$'), admin_add_topic_start)],
    states={
        ADMIN_ADD_TOPIC_SELECT_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_topic_select_subject)],
        ADMIN_ADD_TOPIC_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_topic_name)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# ConversationHandler for adding question
admin_add_question_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Добавить вопрос$'), admin_add_question_start)],
    states={
        ADMIN_ADD_QUESTION_SELECT_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_question_select_topic)],
        ADMIN_ADD_QUESTION_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_question_text)],
        ADMIN_ADD_QUESTION_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_question_answer)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# ConversationHandler for adding group
admin_add_group_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Добавить группу$'), admin_add_group_start)],
    states={
        ADMIN_ADD_GROUP_SELECT_SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_group_select_specialty)],
        ADMIN_ADD_GROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_group_name)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# ConversationHandler for Admin Panel actions
admin_panel_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Админ-панель$'), admin_panel)],
    states={
        # States are handled dynamically in admin_actions
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# ConversationHandler for Admin Actions
admin_actions_conv = ConversationHandler(
    entry_points=[MessageHandler(
        filters.Regex('^(Добавить специальность|Добавить предмет|Добавить тему|Добавить вопрос|Добавить группу)$'),
        admin_actions
    )],
    states={
        # States are handled within admin_actions
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# Function to add all ConversationHandlers to the application
def main():
    # Create the application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(registration_conv)
    application.add_handler(generate_test_conv)
    application.add_handler(admin_panel_conv)
    application.add_handler(admin_add_specialty_conv)
    application.add_handler(admin_add_subject_conv)
    application.add_handler(admin_add_topic_conv)
    application.add_handler(admin_add_question_conv)
    application.add_handler(admin_add_group_conv)
    application.add_handler(admin_actions_conv)
    application.add_handler(MessageHandler(filters.Regex('^Админ-панель$'), admin_panel))
    application.add_handler(MessageHandler(filters.Regex('^Мои результаты$'), my_results))

    # Add handler for /cancel command
    application.add_handler(CommandHandler('cancel', cancel))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
