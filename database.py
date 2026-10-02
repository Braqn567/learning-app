import hashlib
import hmac
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

# Файлът с базата е до app.py. Той НЕ трябва да отива в GitHub.
DB_PATH = Path(__file__).resolve().parent / "quizify.db"
ITERATIONS = 200_000  # колкото повече, толкова по-трудно се налучква парола


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # за да четем колоните по име
    return conn


def init_db():
    """Създава таблиците, ако още ги няма."""
    with closing(_connect()) as conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    percent INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
                """
            )


def _hash_password(password, salt):
    """Превръща паролата в нечетим низ. От него не може да се върне паролата."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


def create_user(username, password):
    """Създава профил. Връща True, а ако името е заето - False."""
    salt = os.urandom(16)  # случайна сол, различна за всеки потребител
    password_hash = _hash_password(password, salt)
    try:
        with closing(_connect()) as conn:
            with conn:
                # Знаците ? пазят от SQL инжекция: данните никога не се вмъкват направо в заявката
                conn.execute(
                    "INSERT INTO users (username, salt, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (
                        username.strip(),
                        salt.hex(),
                        password_hash.hex(),
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
    except sqlite3.IntegrityError:
        return False  # такова име вече има
    return True


def verify_user(username, password):
    """Проверява името и паролата. Връща {'id', 'username'} или None."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    if row is None:
        return None
    expected = bytes.fromhex(row["password_hash"])
    actual = _hash_password(password, bytes.fromhex(row["salt"]))
    if hmac.compare_digest(expected, actual):  # безопасно сравняване
        return {"id": row["id"], "username": row["username"]}
    return None


def save_result(user_id, result):
    """Запазва един решен тест (целият речник като текст във формат JSON)."""
    data = json.dumps(result, ensure_ascii=False)
    with closing(_connect()) as conn:
        with conn:
            conn.execute(
                "INSERT INTO results (user_id, created_at, percent, data) VALUES (?, ?, ?, ?)",
                (
                    user_id,
                    datetime.now().isoformat(timespec="seconds"),
                    result["percent"],
                    data,
                ),
            )


def count_results(user_id):
    """Колко теста е запазил потребителят."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM results WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row["n"]