-- для хранения информации о пользователях.
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- для хранения всех слов (английских и их переводов).
CREATE TABLE IF NOT EXISTS words (
    word_id SERIAL PRIMARY KEY,
    english VARCHAR(100) NOT NULL,
    russian VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- для связи пользователей с их словами.
CREATE TABLE IF NOT EXISTS user_words (
    user_id BIGINT REFERENCES users(user_id),
    word_id INT REFERENCES words(word_id),
    PRIMARY KEY (user_id, word_id)
);

-- Создаем таблицу для хранения статистики обучения
CREATE TABLE IF NOT EXISTS learning_statistics (
	user_id BIGINT REFERENCES users(user_id),
	word_id INT REFERENCES words(word_id),
	correct_answers INT DEFAULT 0,
	incorrect_answers INT DEFAULT 0,
	PRIMARY KEY (user_id, word_id)
	);


--ALTER TABLE learning_statictics RENAME TO learning_statistics

--SELECT * from words

-- Добавление уникальных слов из одной таблицы в другую
--INSERT INTO english_words (english, russian)
--SELECT english_word, russian_translation 
--FROM words w
--WHERE NOT EXISTS (
--    SELECT 1 
--    FROM english_words e 
--    WHERE e.english = w.english_word AND e.russian = w.russian_translation
--);
--
--INSERT INTO words (english, russian, created_at)
--SELECT english, russian, created_at 
--FROM english_words e
--WHERE NOT EXISTS (
--    SELECT 1 
--    FROM words w 
--    WHERE w.english = e.english AND w.russian = e.russian
--);














