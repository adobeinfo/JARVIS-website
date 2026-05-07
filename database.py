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

CREATE TABLE IF NOT EXISTS site_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS online_users (
    ip_hash   TEXT PRIMARY KEY,
    last_seen REAL
);

CREATE TABLE IF NOT EXISTS event_progress (
    token              TEXT PRIMARY KEY,
    ip_hash            TEXT DEFAULT '',
    beta_code          TEXT DEFAULT '',
    beta_granted_at    TIMESTAMP,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_secrets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    riddle_question TEXT NOT NULL,
    riddle_answer   TEXT NOT NULL,
    unlock_at       TIMESTAMP NOT NULL,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_secret_unlocks (
    token       TEXT NOT NULL,
    secret_id   INTEGER NOT NULL REFERENCES event_secrets(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (token, secret_id)
);

CREATE INDEX IF NOT EXISTS idx_visits_created ON page_visits(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_cat      ON forum_posts(category_id);
CREATE INDEX IF NOT EXISTS idx_replies_post   ON forum_replies(post_id);
CREATE INDEX IF NOT EXISTS idx_secrets_unlock ON event_secrets(unlock_at);
CREATE INDEX IF NOT EXISTS idx_unlocks_token  ON event_secret_unlocks(token);
"""

DEFAULT_SETTINGS = {
    "summer_design":      "0",
    "event_active":       "0",
    "event_title":        "🕰 Капсула времени · JARVIS V2",
    "event_text":         "26 мая 2026 — релиз JARVIS V2. До этого момента каждый день в 18:00 МСК открывается секрет. Разгадай загадку и узнай тизер новой фичи. Раскрой все секреты — получи бета-доступ.",
    "event_release_at":   "2026-05-26 18:00:00",
    "event_release_title":"JARVIS V2",
}


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

    # Дефолтные настройки (только если ключа ещё нет)
    for k, v in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)",
            (k, v),
        )
    conn.commit()
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

    # Стартовые секреты эвента-капсулы (тизеры V2)
    import datetime as _dt
    base = _dt.datetime(2026, 5, 7, 18, 0, 0)  # с 7 мая по 1 в день
    secrets = [
        ("Новый движок диалогов",
         "<p>В JARVIS V2 встроен <b>контекстный движок памяти</b>: ассистент помнит предыдущие диалоги, ваше имя, любимые программы и расписание. Контекст шифруется и хранится только локально.</p>",
         "Я помню всё, но никогда не выйду наружу. Что я?", "память"),
        ("Голос как у тебя",
         "<p>Появится <b>клонирование голоса</b> на 30 секундах записи через локальный XTTS-v3. JARVIS сможет говорить вашим голосом или голосом близкого человека.</p>",
         "30 секунд — и я твой двойник. Кто я?", "голос"),
        ("Зрение",
         "<p>JARVIS V2 видит экран. Скажи «что на экране?» — и он опишет окно, прочтёт ошибку, найдёт нужную кнопку. Используется локальная мультимодальная модель.</p>",
         "Я смотрю туда же, куда и ты. Что я делаю?", "вижу"),
        ("Сценарии без кода",
         "<p>Визуальный <b>конструктор сценариев</b>: drag-and-drop блоки «когда → если → сделай». Запускай Photoshop, открывай нужные сайты, играй музыку — одним голосом.</p>",
         "Что мы строим из блоков, не написав ни строчки кода?", "сценарий"),
        ("Open Source",
         "<p>Ядро JARVIS V2 будет <b>open-source</b> под MIT. Закрытыми останутся только premium-голоса и интеграции с платными API.</p>",
         "Свободный, как ветер, и доступен всем. Какой я?", "открытый"),
    ]
    for i, (title, content, q, a) in enumerate(secrets):
        conn.execute(
            "INSERT INTO event_secrets (title, content, riddle_question, riddle_answer, unlock_at, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, content, q, a.lower(),
             (base + _dt.timedelta(days=i*3)).strftime("%Y-%m-%d %H:%M:%S"), i)
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
