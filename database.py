import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_site.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    excerpt TEXT DEFAULT '',
    content TEXT NOT NULL,
    image_url TEXT DEFAULT '',
    author TEXT DEFAULT 'Команда JARVIS',
    is_published INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS forum_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    icon TEXT DEFAULT '💬',
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS forum_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER REFERENCES forum_categories(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_name TEXT DEFAULT 'Аноним',
    views INTEGER DEFAULT 0,
    is_pinned INTEGER DEFAULT 0,
    is_locked INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS page_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    ip_hash TEXT DEFAULT '',
    referrer TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_hash TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS forum_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER REFERENCES forum_posts(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    author_name TEXT DEFAULT 'Аноним',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()

    # Seed если пусто
    cur = conn.execute("SELECT COUNT(*) FROM admins")
    if cur.fetchone()[0] == 0:
        _seed(conn)

    conn.close()


def _seed(conn):
    # Администратор
    conn.execute(
        "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
        ("admin", generate_password_hash("jarvis2024")),
    )

    # Категории форума
    categories = [
        ("🚀 Общее обсуждение", "Общие вопросы и разговоры о JARVIS", "🚀", 1),
        ("🐛 Баги и проблемы", "Сообщения об ошибках и неполадках", "🐛", 2),
        ("💡 Предложения", "Идеи по улучшению и новые функции", "💡", 3),
        ("📦 Установка", "Помощь с установкой и настройкой", "📦", 4),
    ]
    conn.executemany(
        "INSERT INTO forum_categories (name, description, icon, sort_order) VALUES (?, ?, ?, ?)",
        categories,
    )

    # Стартовая новость
    conn.execute(
        """INSERT INTO news (title, excerpt, content, author, is_published) VALUES (?, ?, ?, ?, ?)""",
        (
            "JARVIS v22.0 — Официальный релиз",
            "Первый публичный релиз JARVIS AI Assistant с поддержкой GigaChat, голосового управления и мультипровайдерного TTS.",
            """<p>Мы рады представить <strong>JARVIS AI Assistant версии 22.0</strong> — первый публичный релиз персонального голосового ассистента нового поколения.</p>

<h3>Что нового в v22.0</h3>
<ul>
<li><strong>GigaChat от Сбера</strong> — AI без VPN, бесплатный tier 1 млн токенов в месяц, отвечает по-русски</li>
<li><strong>Мультипровайдерный TTS</strong> — Edge TTS, ElevenLabs, Coqui XTTS, Fish Audio, Yandex SpeechKit</li>
<li><strong>Sounddevice аудиосистема</strong> — замена устаревших PyAudio и pygame на современный sounddevice</li>
<li><strong>Wake-word активация</strong> — скажи "Джарвис" и он слушает, работает через Vosk офлайн</li>
<li><strong>Голосовые пакеты</strong> — Джарвис из Iron Man и Якубович из Поля чудес</li>
<li><strong>Управление ПК</strong> — открытие программ, сценарии запуска, скриншоты, управление мышью</li>
<li><strong>Discord Rich Presence</strong> — показывает статус JARVIS в Discord</li>
<li><strong>Красивый интерфейс</strong> — WebView интерфейс с тёмными темами</li>
</ul>

<h3>Системные требования</h3>
<ul>
<li>Windows 10 / 11 (64-bit)</li>
<li>ОЗУ: от 4 ГБ (8 ГБ рекомендуется)</li>
<li>Диск: ~2 ГБ свободного места</li>
<li>Микрофон для голосового управления</li>
</ul>

<p>Скачайте установщик и запустите — JARVIS готов к работе без дополнительной настройки.</p>""",
            "Команда JARVIS",
            1,
        ),
    )

    # Стартовые посты на форуме
    conn.execute(
        """INSERT INTO forum_posts (category_id, title, content, author_name, is_pinned) VALUES (?, ?, ?, ?, ?)""",
        (
            1,
            "Добро пожаловать в сообщество JARVIS!",
            "Привет всем! Это официальный форум JARVIS AI Assistant. Здесь вы можете обсуждать возможности, задавать вопросы и делиться опытом. Приятного общения!",
            "Команда JARVIS",
            1,
        ),
    )

    conn.commit()
