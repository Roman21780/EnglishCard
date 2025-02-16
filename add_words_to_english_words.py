import psycopg2
from dotenv import load_dotenv
import os
import re

load_dotenv()

# Подключение к базе данных
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),  # Исправлено имя переменной окружения
    user=os.getenv('DB_USER'),    # Исправлено имя переменной окружения
    password=os.getenv('DB_PASSWORD'),  # Исправлено имя переменной окружения
    host=os.getenv('DB_HOST', 'localhost'),  # Используйте корректное имя переменной окружения
    port=os.getenv('DB_PORT', '5432')  # Используйте корректное имя переменной окружения
)

cursor = conn.cursor()

# Чтение слов из файла
with open('dict.txt', 'r', encoding='utf-8') as file:
    words = file.readlines()

# Добавление слов в таблицу
for line in words:
    line = line.strip()  # удалить пробелы и символы новой строки
    if line:  # проверка на пустые строки
        # Используем регулярное выражение для разделения слов
        split_words = re.split(r'\s+', line)  # Разделение по пробелам (включая несколько пробелов)
        if len(split_words) == 2:  # Убедимся, что нашли два слова
            english_word, russian_word = split_words
            cursor.execute("INSERT INTO english_words (english, russian) VALUES (%s, %s)", (english_word, russian_word))

# Сохранение изменений и закрытие соединения
conn.commit()
cursor.close()
conn.close()
