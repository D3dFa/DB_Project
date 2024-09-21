import time
import random
import string
import psutil  # для мониторинга использования ресурсов системы
import os
from sqlalchemy import create_engine, select, update, delete, func, text
from sqlalchemy.orm import sessionmaker
from models import Base, Subject

# Настройки
DATABASE_URL = 'sqlite:///benchmark_subjects.db'  # Файл базы данных
ENGINE = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=ENGINE)


# Функция для генерации случайного названия предмета
def generate_random_name(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


# Создание таблицы
def create_table():
    Base.metadata.drop_all(ENGINE)  # Удаляем таблицу, если она существует
    Base.metadata.create_all(ENGINE)
    print("Таблица 'subjects' создана.")


# Заполнение таблицы данными
def populate_table(session, num_records):
    subjects = [Subject(name=generate_random_name()) for _ in range(num_records)]
    session.bulk_save_objects(subjects)
    session.commit()


# Функция для очистки кэша (в случае с SQLite)
def clear_cache():
    if 'sqlite' in DATABASE_URL:
        with ENGINE.connect() as conn:
            conn.execute(text("PRAGMA optimize"))


# Функция для измерения использования ресурсов (памяти и процессора)
def measure_system_resources():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    return {'cpu': cpu_percent, 'memory': mem_info.rss / (1024 * 1024)}  # память в МБ


# Функция для выполнения операции несколько раз и получения среднего времени
def measure_time(func, *args, repetitions=5, **kwargs):
    total_time = 0.0
    resources_before = measure_system_resources()

    for _ in range(repetitions):
        start_time = time.perf_counter()
        func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time += (end_time - start_time)

    average_time = (total_time / repetitions) * 1000  # мс
    resources_after = measure_system_resources()

    resource_usage = {
        'cpu_diff': resources_after['cpu'] - resources_before['cpu'],
        'memory_diff': resources_after['memory'] - resources_before['memory']
    }

    return average_time, resource_usage


# Операции для бенчмаркинга
def benchmark_operations(num_records):
    results = {}

    with Session() as session:
        # Очистка таблицы перед заполнением
        session.query(Subject).delete()
        session.commit()

        print(f"\nЗаполнение таблицы {num_records} записей...")
        populate_table(session, num_records)
        print("Заполнение завершено.")

        # Получение списка всех ID для корректного выбора случайного ID
        all_ids = session.query(Subject.id).all()
        all_ids = [id_tuple[0] for id_tuple in all_ids]

        if not all_ids:
            print("Таблица пуста после заполнения. Прерывание бенчмарка.")
            return results

        # Выбор случайного ID и имени для операций
        random_id = random.choice(all_ids)
        subject = session.get(Subject, random_id)
        subject_name = subject.name if subject else generate_random_name()
        pattern = subject_name[:3]  # Берем первые 3 символа для LIKE-запроса

        # Определение функций для каждой операции
        def find_by_id():
            session.get(Subject, random_id)

        def find_by_name():
            session.query(Subject).filter_by(name=subject_name).all()

        def find_like_pattern():
            session.query(Subject).filter(Subject.name.like(f'%{pattern}%')).all()

        def add_record():
            new_subject = Subject(name=generate_random_name())
            session.add(new_subject)
            session.commit()

        def add_group_records():
            new_subjects = [Subject(name=generate_random_name()) for _ in range(100)]
            session.bulk_save_objects(new_subjects)
            session.commit()

        def update_by_id():
            new_name = generate_random_name()
            session.query(Subject).filter_by(id=random_id).update({"name": new_name})
            session.commit()

        def update_by_name():
            updated_name = generate_random_name()
            session.query(Subject).filter_by(name=subject_name).update({"name": updated_name})
            session.commit()

        def delete_by_id():
            subject_to_delete = session.query(Subject).filter_by(id=random_id).first()
            if subject_to_delete:
                session.delete(subject_to_delete)
                session.commit()

        def delete_by_name():
            session.query(Subject).filter_by(name=subject_name).delete()
            session.commit()

        def delete_group_records():
            subquery = select(Subject.id).order_by(Subject.id).limit(100)
            session.query(Subject).filter(Subject.id.in_(subquery)).delete(synchronize_session=False)
            session.commit()

        def vacuum_db():
            session.execute(text("VACUUM"))
            session.commit()

        # Очищаем кэш перед операциями
        clear_cache()

        # Измерение времени и ресурсов для каждой операции
        print("Тест: Поиск по ключевому полю (id)")
        results['Поиск по ключевому полю (id)'] = measure_time(find_by_id)

        clear_cache()
        print("Тест: Поиск по не ключевому полю (name) - полное совпадение")
        results['Поиск по не ключевому полю (name)'] = measure_time(find_by_name)

        clear_cache()
        print("Тест: Поиск по маске (LIKE '%pattern%')")
        results['Поиск по маске (LIKE \'%pattern%\')'] = measure_time(find_like_pattern)

        clear_cache()
        print("Тест: Добавление записи")
        results['Добавление записи'] = measure_time(add_record)

        clear_cache()
        print("Тест: Добавление группы записей (100 записей)")
        results['Добавление группы записей (100 записей)'] = measure_time(add_group_records)

        clear_cache()
        print("Тест: Изменение записи по ключевому полю (id)")
        results['Изменение записи по ключевому полю (id)'] = measure_time(update_by_id)

        clear_cache()
        print("Тест: Изменение записи по не ключевому полю (name)")
        results['Изменение записи по не ключевому полю (name)'] = measure_time(update_by_name)

        clear_cache()
        print("Тест: Удаление записи по ключевому полю (id)")
        results['Удаление записи по ключевому полю (id)'] = measure_time(delete_by_id)

        clear_cache()
        print("Тест: Удаление записи по не ключевому полю (name)")
        results['Удаление записи по не ключевому полю (name)'] = measure_time(delete_by_name)

        clear_cache()
        print("Тест: Удаление группы записей (100 записей)")
        results['Удаление группы записей (100 записей)'] = measure_time(delete_group_records)

        clear_cache()
        print("Тест: Сжатие базы данных после удаления 200 строк")
        results['Сжатие базы данных (после удаления 200 строк)'] = measure_time(vacuum_db)

    return results


# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def main():
    create_table()

    # Размеры таблицы для тестирования
    sizes = [1000, 10000, 100000]

    # Результаты будут храниться в словаре
    all_results = {}

    for size in sizes:
        print(f"\n=== Бенчмаркинг для {size} записей ===")
        results = benchmark_operations(size)
        all_results[size] = results

    # Вывод результатов
    print("\n\n=== Результаты бенчмаркинга ===")
    header = ["Операция"] + [f"{size} записей" for size in sizes]
    rows = []

    # Получение списка всех операций
    operations = list(next(iter(all_results.values())).keys())

    for operation in operations:
        row = [operation]
        for size in sizes:
            time_ms, resource_usage = all_results[size].get(operation, (None, None))
            if time_ms is not None:
                row.append(
                    f"{time_ms:.3f} мс (CPU: {resource_usage['cpu_diff']}%, MEM: {resource_usage['memory_diff']:.2f}MB)")
            else:
                row.append("—")
        rows.append(row)

    # Определение ширины столбцов
    col_widths = [max(len(row[i]) for row in [header] + rows) + 2 for i in range(len(header))]

    # Функция для форматирования строки
    def format_row(row):
        return "".join(word.ljust(col_widths[i]) for i, word in enumerate(row))

    # Вывод заголовка
    print(format_row(header))
    print("-" * sum(col_widths))

    # Вывод строк
    for row in rows:
        print(format_row(row))


if __name__ == "__main__":
    main()
