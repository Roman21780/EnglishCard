import logging
import telebot
from telebot import types
import psycopg2
from psycopg2 import Error
import random
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Параметры подключения к PostgreSQL
DB_PARAMS = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# Инициализация бота
TOKEN = os.getenv('TOKEN_BOT')
bot = telebot.TeleBot(TOKEN)

def get_db_connection():
    """Создание подключения к базе данных"""
    try:
        connection = psycopg2.connect(**DB_PARAMS)
        return connection
    except Error as e:
        print(f"Ошибка при подключении к PostgreSQL: {e}")
        return None

def init_db():
    """Инициализация таблиц в базе данных"""
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            # Создание таблиц, если они не существуют
            create_tables_query = '''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS words (
                    word_id SERIAL PRIMARY KEY,
                    english VARCHAR(100) NOT NULL,
                    russian VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_words (
                    user_id BIGINT REFERENCES users(user_id),
                    word_id INT REFERENCES words(word_id),
                    PRIMARY KEY (user_id, word_id)
                );

                CREATE TABLE IF NOT EXISTS learning_statistics (
                    user_id BIGINT REFERENCES users(user_id),
                    word_id INT REFERENCES words(word_id),
                    correct_answers INT DEFAULT 0,
                    incorrect_answers INT DEFAULT 0,
                    PRIMARY KEY (user_id, word_id)
                );
            '''
            cursor.execute(create_tables_query)
            connection.commit()

            cursor.close()
            connection.close()
            print("Таблицы успешно созданы в PostgreSQL")
    except Error as e:
        print(f"Ошибка при создании таблиц: {e}")

@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Приветственное сообщение
    bot.send_message(
        message.chat.id,
        f"Привет, {first_name} {last_name}! 👋\n"
        "Добро пожаловать в бота для изучения английских слов.\n"
        "Используй команду /add чтобы добавить новые слова, или начни тренировку прямо сейчас!"
    )

    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            # Добавление пользователя, если его нет в базе
            cursor.execute(
                "INSERT INTO users (user_id, username, first_name, last_name) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING",
                (user_id, username, first_name, last_name))
            connection.commit()

            # Проверка количества слов пользователя
            cursor.execute("SELECT COUNT(*) FROM user_words WHERE user_id = %s", (user_id,))
            word_count = cursor.fetchone()[0]

            if word_count == 0:
                bot.send_message(
                    message.chat.id,
                    "К сожалению, в вашей базе пока нет слов. "
                    "Добавьте новые слова для начала обучения, используя команду /add!"
                )
                return

            # Если слова есть, начинаем тренировку
            word = get_random_word(user_id)
            if word:
                english, correct_translation = word
                wrong_answers = get_wrong_answers(correct_translation)

                all_answers = [correct_translation] + wrong_answers
                random.shuffle(all_answers)

                keyboard = types.InlineKeyboardMarkup()
                for answer in all_answers:
                    callback_data = f"answer_{answer}_{english}_{correct_translation}"
                    keyboard.add(types.InlineKeyboardButton(answer, callback_data=callback_data))

                bot.send_message(
                    message.chat.id,
                    f"Переведите слово: *{english}*",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )

            cursor.close()
            connection.close()
    except Error as e:
        bot.send_message(message.chat.id, "Произошла ошибка при подключении к базе данных. Попробуйте позже.")
        print(f"Ошибка в команде start: {e}")

@bot.message_handler(commands=['help'])
def help_command(message):
    """Вывод списка доступных команд"""
    help_text = (
        "/start - Начать работу с ботом\n"
        "/add <english> <russian> - Добавить слово в ваш список\n"
        "/delete <english> - Удалить слово из вашего списка\n"
        "/stats - Показать статистику обучения\n"
        "/help - Показать список команд"
    )
    bot.send_message(message.chat.id, help_text)

def get_random_word(user_id):
    """Получение случайного слова из базы для конкретного пользователя"""
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            # Выбираем случайное слово из списка слов пользователя
            cursor.execute("""
                SELECT w.english, w.russian 
                FROM words w
                JOIN user_words uw ON w.word_id = uw.word_id
                WHERE uw.user_id = %s
                ORDER BY RANDOM() 
                LIMIT 1
            """, (user_id,))
            word = cursor.fetchone()
            cursor.close()
            connection.close()
            return word
    except Error as e:
        print(f"Ошибка при получении случайного слова: {e}")
        return None

def get_wrong_answers(correct_answer):
    """Получение неправильных вариантов ответа"""
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT russian FROM words WHERE russian != %s ORDER BY RANDOM() LIMIT 3", (correct_answer,))
            wrong_answers = [row[0] for row in cursor.fetchall()]
            cursor.close()
            connection.close()
            return wrong_answers
    except Error as e:
        print(f"Ошибка при получении вариантов ответа: {e}")
        return []

@bot.callback_query_handler(func=lambda call: True)
def handle_answer(call):
    """Обработчик ответов пользователя"""
    answer_data = call.data.split('_')
    user_answer = answer_data[1]
    english = answer_data[2]
    correct_translation = answer_data[3]

    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            # Получаем word_id для текущего слова
            cursor.execute("SELECT word_id FROM words WHERE english = %s", (english,))
            word_id = cursor.fetchone()[0]

            # Обновляем статистику
            if user_answer == correct_translation:
                cursor.execute("""
                    INSERT INTO learning_statistics (user_id, word_id, correct_answers)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (user_id, word_id) DO UPDATE
                    SET correct_answers = learning_statistics.correct_answers + 1
                """, (call.from_user.id, word_id))
                bot.answer_callback_query(call.id, "Правильно! 👍")
            else:
                cursor.execute("""
                    INSERT INTO learning_statistics (user_id, word_id, incorrect_answers)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (user_id, word_id) DO UPDATE
                    SET incorrect_answers = learning_statistics.incorrect_answers + 1
                """, (call.from_user.id, word_id))
                bot.answer_callback_query(call.id, f"Неправильно! Попробуйте снова.")

            connection.commit()

            # Предлагаем следующее слово
            word = get_random_word(call.from_user.id)
            if word:
                new_english, new_correct_translation = word
                wrong_answers = get_wrong_answers(new_correct_translation)

                all_answers = [new_correct_translation] + wrong_answers
                random.shuffle(all_answers)

                keyboard = types.InlineKeyboardMarkup()
                for answer in all_answers:
                    callback_data = f"answer_{answer}_{new_english}_{new_correct_translation}"
                    keyboard.add(types.InlineKeyboardButton(answer, callback_data=callback_data))

                bot.edit_message_text(
                    f"Переведите слово: *{new_english}*",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
    except Error as e:
        bot.answer_callback_query(call.id, "Произошла ошибка при обработке ответа. Попробуйте позже.")
        print(f"Ошибка в handle_answer: {e}")

@bot.message_handler(commands=['add'])
def add_word(message):
    """Обработчик команды /add"""
    user_id = message.from_user.id

    try:
        if len(message.text.split()) < 3:
            bot.send_message(
                message.chat.id,
                "Пожалуйста, используйте формат: /add english russian_word"
            )
            return

        english = message.text.split()[1].lower()
        russian_word = message.text.split()[2].lower()

        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            # Проверка на существование слова в общем списке
            cursor.execute("SELECT word_id FROM words WHERE english = %s", (english,))
            word = cursor.fetchone()

            if not word:
                # Добавление нового слова в общий список
                cursor.execute(
                    "INSERT INTO words (english, russian) VALUES (%s, %s) RETURNING word_id",
                    (english, russian_word)
                )
                word_id = cursor.fetchone()[0]
            else:
                word_id = word[0]

            # Проверка, есть ли слово у пользователя
            cursor.execute("SELECT * FROM user_words WHERE user_id = %s AND word_id = %s", (user_id, word_id))
            if cursor.fetchone():
                bot.send_message(message.chat.id, f"Слово '{english}' уже есть в вашем списке!")
                return

            # Добавление слова для пользователя
            cursor.execute(
                "INSERT INTO user_words (user_id, word_id) VALUES (%s, %s)",
                (user_id, word_id)
            )
            connection.commit()

            # Получение количества слов пользователя
            cursor.execute("SELECT COUNT(*) FROM user_words WHERE user_id = %s", (user_id,))
            word_count = cursor.fetchone()[0]

            bot.send_message(message.chat.id, f"Слово '{english}' успешно добавлено! Всего слов: {word_count}")
    except Error as e:
        bot.send_message(message.chat.id, "Произошла ошибка при добавлении слова. Попробуйте позже.")
        print(f"Ошибка при добавлении слова: {e}")

@bot.message_handler(commands=['delete'])
def delete_word(message):
    """Обработчик команды /delete"""
    user_id = message.from_user.id

    try:
        if len(message.text.split()) < 2:
            bot.send_message(
                message.chat.id,
                "Пожалуйста, используйте формат: /delete english"
            )
            return

        english = message.text.split()[1].lower()

        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            # Поиск слова в общем списке
            cursor.execute("SELECT word_id FROM words WHERE english = %s", (english,))
            word = cursor.fetchone()

            if not word:
                bot.send_message(message.chat.id, f"Слово '{english}' не найдено в базе!")
                return

            word_id = word[0]

            # Удаление слова у пользователя
            cursor.execute("DELETE FROM user_words WHERE user_id = %s AND word_id = %s", (user_id, word_id))
            connection.commit()

            bot.send_message(message.chat.id, f"Слово '{english}' успешно удалено!")
    except Error as e:
        bot.send_message(message.chat.id, "Произошла ошибка при удалении слова. Попробуйте позже.")
        print(f"Ошибка при удалении слова: {e}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Обработчик команды /stats"""
    user_id = message.from_user.id

    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()

            # Получаем общую статистику пользователя
            cursor.execute("""
                SELECT 
                    SUM(correct_answers) AS total_correct,
                    SUM(incorrect_answers) AS total_incorrect
                FROM learning_statistics
                WHERE user_id = %s
            """, (user_id,))
            stats = cursor.fetchone()

            if stats and (stats[0] or stats[1]):
                total_correct, total_incorrect = stats
                bot.send_message(
                    message.chat.id,
                    f"Ваша статистика обучения:\n"
                    f"Правильных ответов: {total_correct}\n"
                    f"Неправильных ответов: {total_incorrect}"
                )
            else:
                bot.send_message(message.chat.id, "У вас пока нет статистики обучения.")
    except Error as e:
        bot.send_message(message.chat.id, "Произошла ошибка при получении статистики. Попробуйте позже.")
        print(f"Ошибка в show_stats: {e}")

if __name__ == '__main__':
    # Инициализация базы данных
    init_db()
    print('Бот запущен...')
    print('Для завершения нажмите Ctrl+Z')
    bot.polling()