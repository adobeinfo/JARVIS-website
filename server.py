import os
import time
import uuid
import random
import hashlib
import functools
import json as _json
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_file, g, abort, jsonify, make_response
)
from werkzeug.security import check_password_hash
from database import get_db, init_db, DEFAULT_SETTINGS

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "jarvis-rockstar-secret-2024")

# Инициализируем БД при старте (для gunicorn тоже)
with app.app_context():
    init_db()

# Ссылка на скачивание
# Вставь сюда свою ссылку (Яндекс Диск / Google Drive / Telegram)
# Или установи переменную среды DOWNLOAD_URL на Railway
GITHUB_RELEASE_URL = os.environ.get(
    "DOWNLOAD_URL",
    ""  # Здесь вставь ссылку напрямую: если она пустая, используется локальный файл
)

# Локальный путь (для локальной разработки)
_HERE = os.path.dirname(os.path.abspath(__file__))
SETUP_FILE = os.path.abspath(os.path.join(_HERE, "..", "setup_output", "JARVIS_Setup_v22.exe"))

GIGACHAT_AUTH_KEY = "MDE5ZGU5ZWUtZTQ0Ni03YzZlLWI2MTAtOWY3NDYyMjVhZWYwOmQyNjZlNzVhLTA3YTEtNDJmMi04OGU3LTI5NTA1MzNkZjAxYw=="

CHAT_SYSTEM_PROMPT = """Ты — дружелюбный AI-ассистент сайта JARVIS AI Assistant.
Помогаешь пользователям разобраться с программой JARVIS — персональным голосовым ассистентом для Windows.

Что умеет JARVIS:
- Голосовое управление компьютером через Wake-Word «Джарвис»
- Работа с GigaChat (Сбер) без VPN — AI отвечает по-русски
- Поддержка Groq и Mistral AI
- TTS: Edge TTS, ElevenLabs, Coqui XTTS, Fish Audio, Yandex SpeechKit
- Управление ПК: запуск программ, скриншоты, сценарии
- Discord Rich Presence
- 5 тем оформления интерфейса
- Работает на Windows 10/11 64-bit
- Скачать: страница /download на этом сайте
- Форум для обсуждений: /forum
- Новости: /news

Отвечай коротко (2-4 предложения), по-русски, дружелюбно. Не придумывай несуществующие функции."""

_gigachat_token = None
_gigachat_token_exp = 0

def _get_gigachat_token():
    """Получает access_token GigaChat."""
    global _gigachat_token, _gigachat_token_exp
    import time, uuid, requests, urllib3
    urllib3.disable_warnings()
    if _gigachat_token and time.time() < _gigachat_token_exp - 60:
        return _gigachat_token
    try:
        r = requests.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={
                "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": str(uuid.uuid4()),
            },
            data={"scope": "GIGACHAT_API_PERS"},
            timeout=15, verify=False,
        )
        if r.status_code == 200:
            data = r.json()
            _gigachat_token = data.get("access_token")
            exp = data.get("expires_at", 0)
            _gigachat_token_exp = int(exp) / 1000 if exp else time.time() + 1700
            return _gigachat_token
    except Exception as e:
        print(f"[GigaChat OAuth] {e}")
    return None


# ─── DB per request ────────────────────────────────────────────────────────────

def get_conn():
    if "db" not in g:
        g.db = get_db()
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db:
        db.close()


# ─── Auth decorator ────────────────────────────────────────────────────────────

# ═══ Visit & Download tracker ══════════════════════════════════════════════════════════

SKIP_TRACK_PREFIXES = ("/static", "/admin", "/api", "/favicon")

@app.before_request
def track_visit():
    path = request.path
    if any(path.startswith(p) for p in SKIP_TRACK_PREFIXES):
        return
    try:
        import hashlib
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ip_hash = hashlib.md5(ip.encode()).hexdigest()[:12]
        referrer = (request.referrer or "")[:200]
        db = get_conn()
        db.execute(
            "INSERT INTO page_visits (path, ip_hash, referrer) VALUES (?, ?, ?)",
            (path, ip_hash, referrer)
        )
        db.commit()
    except Exception:
        pass


def admin_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


# ═══ Settings helpers ══════════════════════════════════════════════════════════

def get_setting(key, default=""):
    db = get_conn()
    row = db.execute("SELECT value FROM site_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    db = get_conn()
    db.execute(
        "INSERT INTO site_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    db.commit()


def _hash_ip():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    return hashlib.md5(ip.encode()).hexdigest()[:12]


_BOOL_SETTING_KEYS_BASE = {"summer_design", "event_active",
                           "ann_enabled", "gate_tg_enabled", "game_enabled"}


def _site_settings_dict():
    """Подгружает все site_settings и для не-boolean ключей подставляет дефолт,
    если в БД лежит пустая строка (защита от случайно затёртых полей)."""
    out = dict(DEFAULT_SETTINGS)
    try:
        rows = get_conn().execute("SELECT key, value FROM site_settings").fetchall()
        for r in rows:
            key, val = r["key"], r["value"]
            if not val and key not in _BOOL_SETTING_KEYS_BASE and key in DEFAULT_SETTINGS:
                # Пустая строка для текстового поля → дефолт
                out[key] = DEFAULT_SETTINGS[key]
            else:
                out[key] = val
    except Exception:
        pass
    return out


@app.context_processor
def inject_globals():
    """Делает все настройки сайта доступными в шаблонах через `site` + старые поля."""
    s = _site_settings_dict()
    s["summer_design_bool"] = (s.get("summer_design", "0") == "1")
    s["event_active_bool"]  = (s.get("event_active",  "0") == "1")
    s["ann_enabled_bool"]   = (s.get("ann_enabled",   "0") == "1")
    s["gate_tg_enabled_bool"] = (s.get("gate_tg_enabled", "0") == "1")
    s["game_enabled_bool"]  = (s.get("game_enabled",  "0") == "1")
    return {
        "site":           s,
        "summer_design":  s["summer_design_bool"],
        "event_active":   s["event_active_bool"],
        "event_title":    s.get("event_title", ""),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ПУБЛИЧНЫЕ МАРШРУТЫ
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/favicon.ico")
def favicon_ico():
    """Старые браузеры запрашивают /favicon.ico — отдаём app.png."""
    return send_file(os.path.join(_HERE, "static", "img", "favicon.png"),
                     mimetype="image/png")


@app.route("/shop-verification-QR2ONd4OmJ.txt")
def shop_verification():
    resp = make_response("shop-verification-QR2ONd4OmJ")
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp


@app.route("/")
def index():
    db = get_conn()
    latest_news = db.execute(
        "SELECT * FROM news WHERE is_published=1 ORDER BY created_at DESC LIMIT 3"
    ).fetchall()
    return render_template("index.html", latest_news=latest_news)


# ── Новости ────────────────────────────────────────────────────────────────────

@app.route("/news")
def news():
    db = get_conn()
    news_list = db.execute(
        "SELECT * FROM news WHERE is_published=1 ORDER BY created_at DESC"
    ).fetchall()
    return render_template("news.html", news_list=news_list)


@app.route("/news/<int:nid>")
def news_detail(nid):
    db = get_conn()
    article = db.execute("SELECT * FROM news WHERE id=? AND is_published=1", (nid,)).fetchone()
    if not article:
        abort(404)
    return render_template("news_detail.html", article=article)


# ── Скачивание ─────────────────────────────────────────────────────────────────

@app.route("/download")
def download():
    local_exists = os.path.isfile(SETUP_FILE)
    has_url      = bool(GITHUB_RELEASE_URL and GITHUB_RELEASE_URL.strip())

    # Размер файла: реальный если есть локально, иначе из настроек админки
    if local_exists:
        size_mb = round(os.path.getsize(SETUP_FILE) / 1024 / 1024, 1)
    else:
        raw = (get_setting("download_size_mb", "147") or "147").strip()
        try:
            val = float(raw)
            size_mb = int(val) if val.is_integer() else round(val, 1)
        except ValueError:
            size_mb = 147

    # Скачивание доступно если: есть локальный файл ИЛИ есть URL
    file_available = local_exists or has_url

    return render_template("download.html",
                           file_exists=file_available,
                           size_mb=size_mb,
                           github_url=GITHUB_RELEASE_URL if has_url and not local_exists else None)


@app.route("/download/file")
def download_file():
    # Трекинг скачивания
    try:
        import hashlib
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ip_hash = hashlib.md5(ip.encode()).hexdigest()[:12]
        db = get_conn()
        db.execute("INSERT INTO downloads (ip_hash) VALUES (?)", (ip_hash,))
        db.commit()
    except Exception:
        pass

    # Если файл есть локально — отдаём напрямую
    if os.path.isfile(SETUP_FILE):
        return send_file(
            SETUP_FILE,
            as_attachment=True,
            download_name="JARVIS_Setup_v22.exe"
        )

    # Иначе — редирект на GitHub Releases
    if "YOUR_USERNAME" not in GITHUB_RELEASE_URL:
        return redirect(GITHUB_RELEASE_URL)

    flash("Ссылка для скачивания не настроена. Свяжитесь с администратором.", "error")
    return redirect(url_for("download"))


# ── Эвент: «Капсула времени» ───────────────────────────────────────────────────

import datetime as _dt


def _parse_release_at():
    raw = get_setting("event_release_at", DEFAULT_SETTINGS["event_release_at"])
    try:
        return _dt.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return _dt.datetime.strptime(DEFAULT_SETTINGS["event_release_at"], "%Y-%m-%d %H:%M:%S")


def _event_get_or_create():
    db = get_conn()
    token = request.cookies.get("event_token") or ""
    row = None
    if token:
        row = db.execute("SELECT * FROM event_progress WHERE token=?", (token,)).fetchone()
    if not row:
        token = uuid.uuid4().hex
        db.execute(
            "INSERT INTO event_progress (token, ip_hash) VALUES (?, ?)",
            (token, _hash_ip()),
        )
        db.commit()
        row = db.execute("SELECT * FROM event_progress WHERE token=?", (token,)).fetchone()
    return token, row


def _set_event_cookie(resp, token):
    resp.set_cookie("event_token", token,
                    max_age=60 * 60 * 24 * 90, httponly=True, samesite="Lax")
    return resp


def _build_secrets_list(db, token):
    """Возвращает список секретов с состояниями для текущего пользователя."""
    secrets = db.execute(
        "SELECT id, title, content, riddle_question, unlock_at, sort_order "
        "FROM event_secrets ORDER BY unlock_at, sort_order, id"
    ).fetchall()
    unlocked_ids = {r["secret_id"] for r in db.execute(
        "SELECT secret_id FROM event_secret_unlocks WHERE token=?", (token,)
    ).fetchall()}
    now = _dt.datetime.now()
    out = []
    for s in secrets:
        try:
            ua = _dt.datetime.strptime(s["unlock_at"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            ua = now
        is_unlocked = s["id"] in unlocked_ids
        is_available = now >= ua
        out.append({
            "id":          s["id"],
            "title":       s["title"],
            "unlock_at":   s["unlock_at"],
            "unlock_ts":   int(ua.timestamp()),
            "available":   is_available,
            "unlocked":    is_unlocked,
            "riddle":      s["riddle_question"] if (is_available and not is_unlocked) else "",
            "content":     s["content"] if is_unlocked else "",
        })
    return out


def _maybe_grant_beta(db, token):
    """Если пользователь раскрыл все секреты — выдать бета-код."""
    total = db.execute("SELECT COUNT(*) FROM event_secrets").fetchone()[0]
    if total == 0:
        return None
    mine = db.execute(
        "SELECT COUNT(*) FROM event_secret_unlocks WHERE token=?", (token,)
    ).fetchone()[0]
    if mine < total:
        return None
    row = db.execute("SELECT beta_code FROM event_progress WHERE token=?", (token,)).fetchone()
    if row and row["beta_code"]:
        return row["beta_code"]
    code = "JV2-" + uuid.uuid4().hex[:10].upper()
    db.execute(
        "UPDATE event_progress SET beta_code=?, beta_granted_at=CURRENT_TIMESTAMP "
        "WHERE token=?", (code, token),
    )
    db.commit()
    return code


def _event_state(db, token):
    secrets = _build_secrets_list(db, token)
    row = db.execute("SELECT beta_code FROM event_progress WHERE token=?", (token,)).fetchone()
    total = len(secrets)
    unlocked = sum(1 for s in secrets if s["unlocked"])
    return {
        "release_at":     get_setting("event_release_at", DEFAULT_SETTINGS["event_release_at"]),
        "release_ts":     int(_parse_release_at().timestamp()),
        "release_title":  get_setting("event_release_title", DEFAULT_SETTINGS["event_release_title"]),
        "secrets":        secrets,
        "total":          total,
        "unlocked_count": unlocked,
        "beta_code":      (row["beta_code"] if row else "") or "",
        "now":            int(time.time()),
    }


@app.route("/event")
def event_page():
    if get_setting("event_active", "0") != "1":
        abort(404)
    db = get_conn()
    token, _ = _event_get_or_create()
    state = _event_state(db, token)
    resp = make_response(render_template("event.html",
        event_text=get_setting("event_text", DEFAULT_SETTINGS["event_text"]),
        state=state,
    ))
    return _set_event_cookie(resp, token)


@app.route("/api/event/state")
def api_event_state():
    if get_setting("event_active", "0") != "1":
        return jsonify({"error": "event_off"}), 404
    db = get_conn()
    token, _ = _event_get_or_create()
    return _set_event_cookie(jsonify(_event_state(db, token)), token)


@app.route("/api/event/unlock", methods=["POST"])
def api_event_unlock():
    if get_setting("event_active", "0") != "1":
        return jsonify({"error": "event_off"}), 404
    data = request.get_json(silent=True) or {}
    try:
        secret_id = int(data.get("secret_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "bad_id"}), 400
    answer = (data.get("answer") or "").strip().lower()
    if not answer:
        return jsonify({"error": "empty_answer"}), 400

    db = get_conn()
    token, _ = _event_get_or_create()
    s = db.execute(
        "SELECT id, riddle_answer, unlock_at FROM event_secrets WHERE id=?",
        (secret_id,),
    ).fetchone()
    if not s:
        return jsonify({"error": "not_found"}), 404

    # Проверка времени
    try:
        ua = _dt.datetime.strptime(s["unlock_at"], "%Y-%m-%d %H:%M:%S")
    except Exception:
        ua = _dt.datetime.now()
    if _dt.datetime.now() < ua:
        return _set_event_cookie(
            jsonify({**_event_state(db, token), "ok": False, "reason": "locked_time"}), token
        )

    # Уже разблокирован?
    already = db.execute(
        "SELECT 1 FROM event_secret_unlocks WHERE token=? AND secret_id=?",
        (token, secret_id),
    ).fetchone()
    if already:
        return _set_event_cookie(
            jsonify({**_event_state(db, token), "ok": True, "reason": "already"}), token
        )

    # Сравнение ответа (case+space-insensitive, без пунктуации)
    correct = s["riddle_answer"].strip().lower()
    norm = lambda x: ''.join(ch for ch in x if ch.isalnum()).lower()
    if norm(answer) != norm(correct):
        return _set_event_cookie(
            jsonify({**_event_state(db, token), "ok": False, "reason": "wrong"}), token
        )

    db.execute(
        "INSERT OR IGNORE INTO event_secret_unlocks (token, secret_id) VALUES (?, ?)",
        (token, secret_id),
    )
    db.commit()
    _maybe_grant_beta(db, token)
    return _set_event_cookie(
        jsonify({**_event_state(db, token), "ok": True}), token
    )


# ── Форум ──────────────────────────────────────────────────────────────────────

@app.route("/forum")
def forum():
    db = get_conn()
    cats = db.execute("SELECT * FROM forum_categories ORDER BY sort_order").fetchall()
    categories = []
    for c in cats:
        post_count = db.execute(
            "SELECT COUNT(*) FROM forum_posts WHERE category_id=?", (c["id"],)
        ).fetchone()[0]
        categories.append({"id": c["id"], "name": c["name"],
                            "description": c["description"], "icon": c["icon"],
                            "post_count": post_count})
    total_topics  = db.execute("SELECT COUNT(*) FROM forum_posts").fetchone()[0]
    total_replies = db.execute("SELECT COUNT(*) FROM forum_replies").fetchone()[0]
    total_views   = db.execute("SELECT COALESCE(SUM(views),0) FROM forum_posts").fetchone()[0]
    return render_template("forum.html", categories=categories,
                           total_topics=total_topics,
                           total_replies=total_replies,
                           total_views=total_views)


@app.route("/forum/<int:cat_id>")
def forum_category(cat_id):
    db = get_conn()
    category = db.execute("SELECT * FROM forum_categories WHERE id=?", (cat_id,)).fetchone()
    if not category:
        abort(404)
    posts_raw = db.execute(
        "SELECT * FROM forum_posts WHERE category_id=? ORDER BY is_pinned DESC, created_at DESC",
        (cat_id,)
    ).fetchall()
    posts = []
    for p in posts_raw:
        reply_count = db.execute(
            "SELECT COUNT(*) FROM forum_replies WHERE post_id=?", (p["id"],)
        ).fetchone()[0]
        posts.append({**dict(p), "reply_count": reply_count})
    return render_template("forum_category.html", category=category, posts=posts)


@app.route("/forum/<int:cat_id>/<int:post_id>", methods=["GET"])
def forum_post(cat_id, post_id):
    db = get_conn()
    post = db.execute("SELECT * FROM forum_posts WHERE id=? AND category_id=?",
                      (post_id, cat_id)).fetchone()
    if not post:
        abort(404)
    # Увеличиваем просмотры
    db.execute("UPDATE forum_posts SET views=views+1 WHERE id=?", (post_id,))
    db.commit()
    category = db.execute("SELECT * FROM forum_categories WHERE id=?", (cat_id,)).fetchone()
    replies = db.execute(
        "SELECT * FROM forum_replies WHERE post_id=? ORDER BY created_at", (post_id,)
    ).fetchall()
    return render_template("forum_post.html", post=post, replies=replies, category=category)


@app.route("/forum/<int:cat_id>/<int:post_id>/reply", methods=["POST"])
def forum_reply(cat_id, post_id):
    db = get_conn()
    post = db.execute("SELECT * FROM forum_posts WHERE id=?", (post_id,)).fetchone()
    if not post or post["is_locked"]:
        flash("Тема закрыта для ответов.", "error")
        return redirect(url_for("forum_post", cat_id=cat_id, post_id=post_id))
    content = request.form.get("content", "").strip()
    author = request.form.get("author_name", "Аноним").strip() or "Аноним"
    if not content:
        flash("Ответ не может быть пустым.", "error")
        return redirect(url_for("forum_post", cat_id=cat_id, post_id=post_id))
    if len(content) > 5000:
        flash("Ответ слишком длинный (макс. 5000 символов).", "error")
        return redirect(url_for("forum_post", cat_id=cat_id, post_id=post_id))
    db.execute(
        "INSERT INTO forum_replies (post_id, content, author_name) VALUES (?, ?, ?)",
        (post_id, content, author)
    )
    db.commit()
    flash("Ответ добавлен!", "success")
    return redirect(url_for("forum_post", cat_id=cat_id, post_id=post_id))


@app.route("/forum/new/<int:cat_id>", methods=["GET", "POST"])
def forum_new_post(cat_id):
    db = get_conn()
    category = db.execute("SELECT * FROM forum_categories WHERE id=?", (cat_id,)).fetchone()
    if not category:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        author = request.form.get("author_name", "Аноним").strip() or "Аноним"
        if not title or not content:
            flash("Заполните заголовок и текст.", "error")
        elif len(title) > 200:
            flash("Заголовок слишком длинный.", "error")
        else:
            cur = db.execute(
                "INSERT INTO forum_posts (category_id, title, content, author_name) VALUES (?, ?, ?, ?)",
                (cat_id, title, content, author)
            )
            db.commit()
            flash("Тема создана!", "success")
            return redirect(url_for("forum_post", cat_id=cat_id, post_id=cur.lastrowid))
    return render_template("forum_new_post.html", category=category)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN ПАНЕЛЬ
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_conn()
        admin = db.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            flash("Добро пожаловать, " + username + "!", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Неверный логин или пароль.", "error")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin/")
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_conn()
    news_count    = db.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    posts_count   = db.execute("SELECT COUNT(*) FROM forum_posts").fetchone()[0]
    replies_count = db.execute("SELECT COUNT(*) FROM forum_replies").fetchone()[0]
    total_views   = db.execute("SELECT COALESCE(SUM(views),0) FROM forum_posts").fetchone()[0]

    # Посещения
    visits_total  = db.execute("SELECT COUNT(*) FROM page_visits").fetchone()[0]
    visits_today  = db.execute(
        "SELECT COUNT(*) FROM page_visits WHERE date(created_at)=date('now')"
    ).fetchone()[0]
    visits_week   = db.execute(
        "SELECT COUNT(*) FROM page_visits WHERE created_at >= datetime('now','-7 days')"
    ).fetchone()[0]
    unique_today  = db.execute(
        "SELECT COUNT(DISTINCT ip_hash) FROM page_visits WHERE date(created_at)=date('now')"
    ).fetchone()[0]

    # Скачивания
    dl_total  = db.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
    dl_today  = db.execute(
        "SELECT COUNT(*) FROM downloads WHERE date(created_at)=date('now')"
    ).fetchone()[0]
    dl_week   = db.execute(
        "SELECT COUNT(*) FROM downloads WHERE created_at >= datetime('now','-7 days')"
    ).fetchone()[0]

    # Популярные страницы
    top_pages = db.execute(
        "SELECT path, COUNT(*) as cnt FROM page_visits "
        "GROUP BY path ORDER BY cnt DESC LIMIT 8"
    ).fetchall()

    # Посещаемость по дням (последние 7 дней)
    visits_chart = db.execute(
        "SELECT date(created_at) as day, COUNT(*) as cnt "
        "FROM page_visits "
        "WHERE created_at >= datetime('now','-7 days') "
        "GROUP BY day ORDER BY day"
    ).fetchall()

    stats = {
        "news_count":    news_count,
        "posts_count":   posts_count,
        "replies_count": replies_count,
        "total_views":   total_views,
        "visits_total":  visits_total,
        "visits_today":  visits_today,
        "visits_week":   visits_week,
        "unique_today":  unique_today,
        "dl_total":      dl_total,
        "dl_today":      dl_today,
        "dl_week":       dl_week,
    }
    recent_posts = db.execute(
        "SELECT fp.*, fc.name as cat_name FROM forum_posts fp "
        "JOIN forum_categories fc ON fp.category_id=fc.id "
        "ORDER BY fp.created_at DESC LIMIT 5"
    ).fetchall()
    return render_template("admin/dashboard.html",
                           stats=stats,
                           recent_posts=recent_posts,
                           top_pages=top_pages,
                           visits_chart=list(visits_chart))


# ── Admin: Настройки сайта ─────────────────────────────────────────────────────

@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        set_setting("summer_design", "1" if request.form.get("summer_design") else "0")
        set_setting("event_active",  "1" if request.form.get("event_active")  else "0")
        set_setting("event_title",   request.form.get("event_title", "").strip()
                                       or DEFAULT_SETTINGS["event_title"])
        set_setting("event_text",    request.form.get("event_text",  "").strip()
                                       or DEFAULT_SETTINGS["event_text"])
        set_setting("event_release_title",
                    request.form.get("event_release_title", "").strip()
                    or DEFAULT_SETTINGS["event_release_title"])
        # Парсим дату релиза (datetime-local: "YYYY-MM-DDTHH:MM")
        rel_raw = request.form.get("event_release_at", "").strip()
        if rel_raw:
            try:
                rel = _dt.datetime.fromisoformat(rel_raw)
                set_setting("event_release_at", rel.strftime("%Y-%m-%d %H:%M:%S"))
            except ValueError:
                flash("Неверный формат даты релиза.", "error")
        flash("Настройки сохранены.", "success")
        return redirect(url_for("admin_settings"))

    db = get_conn()
    ev_stats = {
        "users":         db.execute("SELECT COUNT(*) FROM event_progress").fetchone()[0],
        "with_beta":     db.execute("SELECT COUNT(*) FROM event_progress WHERE beta_code!=''").fetchone()[0],
        "secrets_total": db.execute("SELECT COUNT(*) FROM event_secrets").fetchone()[0],
        "unlocks_total": db.execute("SELECT COUNT(*) FROM event_secret_unlocks").fetchone()[0],
    }
    beta_users = db.execute(
        "SELECT token, beta_code, beta_granted_at FROM event_progress "
        "WHERE beta_code!='' ORDER BY beta_granted_at DESC LIMIT 50"
    ).fetchall()
    # Преобразуем release_at в формат datetime-local для <input>
    rel_iso = ""
    try:
        rel_iso = _parse_release_at().strftime("%Y-%m-%dT%H:%M")
    except Exception:
        pass
    return render_template("admin/settings.html",
        s={
            "summer_design":        get_setting("summer_design", "0") == "1",
            "event_active":         get_setting("event_active",  "0") == "1",
            "event_title":          get_setting("event_title",   DEFAULT_SETTINGS["event_title"]),
            "event_text":           get_setting("event_text",    DEFAULT_SETTINGS["event_text"]),
            "event_release_at":     rel_iso,
            "event_release_title":  get_setting("event_release_title", DEFAULT_SETTINGS["event_release_title"]),
        },
        ev_stats=ev_stats,
        beta_users=beta_users,
    )


# ── Admin: Секреты эвента ──────────────────────────────────────────────────────

@app.route("/admin/event")
@admin_required
def admin_event():
    db = get_conn()
    secrets = db.execute(
        "SELECT s.*, (SELECT COUNT(*) FROM event_secret_unlocks u WHERE u.secret_id=s.id) AS unlocks "
        "FROM event_secrets s ORDER BY unlock_at, sort_order, id"
    ).fetchall()
    return render_template("admin/event_secrets.html", secrets=secrets)


@app.route("/admin/event/create", methods=["POST"])
@admin_required
def admin_event_create():
    title    = request.form.get("title", "").strip()
    content  = request.form.get("content", "").strip()
    question = request.form.get("riddle_question", "").strip()
    answer   = request.form.get("riddle_answer", "").strip().lower()
    unlock   = request.form.get("unlock_at", "").strip()
    if not (title and content and question and answer and unlock):
        flash("Заполните все поля.", "error")
        return redirect(url_for("admin_event"))
    try:
        unlock_dt = _dt.datetime.fromisoformat(unlock)
    except ValueError:
        flash("Неверная дата открытия.", "error")
        return redirect(url_for("admin_event"))
    db = get_conn()
    db.execute(
        "INSERT INTO event_secrets (title, content, riddle_question, riddle_answer, unlock_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, content, question, answer, unlock_dt.strftime("%Y-%m-%d %H:%M:%S")),
    )
    db.commit()
    flash("Секрет создан.", "success")
    return redirect(url_for("admin_event"))


@app.route("/admin/event/<int:sid>/delete", methods=["POST"])
@admin_required
def admin_event_delete(sid):
    db = get_conn()
    db.execute("DELETE FROM event_secrets WHERE id=?", (sid,))
    db.commit()
    flash("Секрет удалён.", "info")
    return redirect(url_for("admin_event"))


@app.route("/admin/event/<int:sid>/edit", methods=["POST"])
@admin_required
def admin_event_edit(sid):
    title    = request.form.get("title", "").strip()
    content  = request.form.get("content", "").strip()
    question = request.form.get("riddle_question", "").strip()
    answer   = request.form.get("riddle_answer", "").strip().lower()
    unlock   = request.form.get("unlock_at", "").strip()
    if not (title and content and question and answer and unlock):
        flash("Заполните все поля.", "error")
        return redirect(url_for("admin_event"))
    try:
        unlock_dt = _dt.datetime.fromisoformat(unlock)
    except ValueError:
        flash("Неверная дата открытия.", "error")
        return redirect(url_for("admin_event"))
    db = get_conn()
    db.execute(
        "UPDATE event_secrets SET title=?, content=?, riddle_question=?, riddle_answer=?, unlock_at=? "
        "WHERE id=?",
        (title, content, question, answer, unlock_dt.strftime("%Y-%m-%d %H:%M:%S"), sid),
    )
    db.commit()
    flash("Секрет обновлён.", "success")
    return redirect(url_for("admin_event"))


# ── Admin: Новости ─────────────────────────────────────────────────────────────

@app.route("/admin/news")
@admin_required
def admin_news():
    db = get_conn()
    articles = db.execute("SELECT * FROM news ORDER BY created_at DESC").fetchall()
    return render_template("admin/news_list.html", articles=articles)


@app.route("/admin/news/create", methods=["GET", "POST"])
@admin_required
def admin_news_create():
    if request.method == "POST":
        title      = request.form.get("title", "").strip()
        excerpt    = request.form.get("excerpt", "").strip()
        content    = request.form.get("content", "").strip()
        image_url  = request.form.get("image_url", "").strip()
        is_pub     = 1 if request.form.get("is_published") else 0
        if not title or not content:
            flash("Заголовок и текст обязательны.", "error")
        else:
            db = get_conn()
            db.execute(
                "INSERT INTO news (title, excerpt, content, image_url, is_published) VALUES (?,?,?,?,?)",
                (title, excerpt, content, image_url, is_pub)
            )
            db.commit()
            flash("Новость создана!", "success")
            return redirect(url_for("admin_news"))
    return render_template("admin/news_edit.html", article=None)


@app.route("/admin/news/<int:nid>/edit", methods=["GET", "POST"])
@admin_required
def admin_news_edit(nid):
    db = get_conn()
    article = db.execute("SELECT * FROM news WHERE id=?", (nid,)).fetchone()
    if not article:
        abort(404)
    if request.method == "POST":
        title     = request.form.get("title", "").strip()
        excerpt   = request.form.get("excerpt", "").strip()
        content   = request.form.get("content", "").strip()
        image_url = request.form.get("image_url", "").strip()
        is_pub    = 1 if request.form.get("is_published") else 0
        if not title or not content:
            flash("Заголовок и текст обязательны.", "error")
        else:
            db.execute(
                "UPDATE news SET title=?, excerpt=?, content=?, image_url=?, is_published=?, "
                "updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (title, excerpt, content, image_url, is_pub, nid)
            )
            db.commit()
            flash("Новость обновлена!", "success")
            return redirect(url_for("admin_news"))
    return render_template("admin/news_edit.html", article=article)


@app.route("/admin/news/<int:nid>/delete", methods=["POST"])
@admin_required
def admin_news_delete(nid):
    db = get_conn()
    db.execute("DELETE FROM news WHERE id=?", (nid,))
    db.commit()
    flash("Новость удалена.", "info")
    return redirect(url_for("admin_news"))


# ── Admin: Форум ───────────────────────────────────────────────────────────────

@app.route("/admin/forum")
@admin_required
def admin_forum():
    db = get_conn()
    cats = db.execute("SELECT * FROM forum_categories ORDER BY sort_order").fetchall()
    categories = []
    for c in cats:
        cnt = db.execute("SELECT COUNT(*) FROM forum_posts WHERE category_id=?",
                         (c["id"],)).fetchone()[0]
        categories.append({**dict(c), "post_count": cnt})
    recent_posts = db.execute(
        "SELECT fp.*, fc.name as cat_name FROM forum_posts fp "
        "JOIN forum_categories fc ON fp.category_id=fc.id "
        "ORDER BY fp.created_at DESC LIMIT 20"
    ).fetchall()
    return render_template("admin/forum_manage.html",
                           categories=categories, recent_posts=recent_posts)


@app.route("/admin/forum/category/create", methods=["POST"])
@admin_required
def admin_forum_cat_create():
    db = get_conn()
    name = request.form.get("name", "").strip()
    desc = request.form.get("description", "").strip()
    icon = request.form.get("icon", "💬").strip() or "💬"
    if not name:
        flash("Название категории обязательно.", "error")
    else:
        order = db.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM forum_categories").fetchone()[0]
        db.execute(
            "INSERT INTO forum_categories (name, description, icon, sort_order) VALUES (?,?,?,?)",
            (name, desc, icon, order)
        )
        db.commit()
        flash("Категория создана!", "success")
    return redirect(url_for("admin_forum"))


@app.route("/admin/forum/category/<int:cid>/delete", methods=["POST"])
@admin_required
def admin_forum_cat_delete(cid):
    db = get_conn()
    db.execute("DELETE FROM forum_categories WHERE id=?", (cid,))
    db.commit()
    flash("Категория удалена.", "info")
    return redirect(url_for("admin_forum"))


@app.route("/admin/forum/post/<int:pid>/delete", methods=["POST"])
@admin_required
def admin_forum_post_delete(pid):
    db = get_conn()
    db.execute("DELETE FROM forum_posts WHERE id=?", (pid,))
    db.commit()
    flash("Пост удалён.", "info")
    return redirect(url_for("admin_forum"))


@app.route("/admin/forum/reply/<int:rid>/delete", methods=["POST"])
@admin_required
def admin_forum_reply_delete(rid):
    db = get_conn()
    reply = db.execute("SELECT * FROM forum_replies WHERE id=?", (rid,)).fetchone()
    if reply:
        post = db.execute("SELECT * FROM forum_posts WHERE id=?", (reply["post_id"],)).fetchone()
        db.execute("DELETE FROM forum_replies WHERE id=?", (rid,))
        db.commit()
        flash("Ответ удалён.", "info")
        if post:
            return redirect(url_for("forum_post",
                                    cat_id=post["category_id"], post_id=post["id"]))
    return redirect(url_for("admin_forum"))


# ── Admin: редактирование категории форума ────────────────────────────────────
@app.route("/admin/forum/category/<int:cid>/edit", methods=["POST"])
@admin_required
def admin_forum_cat_edit(cid):
    db = get_conn()
    name = request.form.get("name", "").strip()
    desc = request.form.get("description", "").strip()
    icon = request.form.get("icon", "💬").strip() or "💬"
    if not name:
        flash("Название не может быть пустым.", "error")
        return redirect(url_for("admin_forum"))
    db.execute(
        "UPDATE forum_categories SET name=?, description=?, icon=? WHERE id=?",
        (name, desc, icon, cid),
    )
    db.commit()
    flash("Категория обновлена.", "success")
    return redirect(url_for("admin_forum"))


# ── Admin: pin / lock тем ─────────────────────────────────────────────────────
@app.route("/admin/forum/post/<int:pid>/pin", methods=["POST"])
@admin_required
def admin_forum_post_pin(pid):
    db = get_conn()
    db.execute("UPDATE forum_posts SET is_pinned = NOT IFNULL(is_pinned,0) WHERE id=?", (pid,))
    db.commit()
    flash("Статус закрепа изменён.", "success")
    return redirect(request.referrer or url_for("admin_forum"))


@app.route("/admin/forum/post/<int:pid>/lock", methods=["POST"])
@admin_required
def admin_forum_post_lock(pid):
    db = get_conn()
    db.execute("UPDATE forum_posts SET is_locked = NOT IFNULL(is_locked,0) WHERE id=?", (pid,))
    db.commit()
    flash("Статус блокировки изменён.", "success")
    return redirect(request.referrer or url_for("admin_forum"))


# ── Admin: редактируемый контент сайта ────────────────────────────────────────
SITE_CONTENT_KEYS = [
    # announcement
    "ann_enabled", "ann_text", "ann_link", "ann_style",
    # hero
    "hero_eyebrow", "hero_title_lead", "hero_title_accent",
    "hero_cta_primary", "hero_cta_secondary",
    "hero_meta_1_num", "hero_meta_1_label",
    "hero_meta_2_num", "hero_meta_2_label",
    "hero_meta_3_num", "hero_meta_3_label",
    "hero_meta_4_num", "hero_meta_4_label",
    # cta
    "cta_label", "cta_title", "cta_text",
    # download
    "download_version", "download_subtitle", "download_size_mb",
    # social
    "social_telegram", "social_boosty",
    # TG gate
    "gate_tg_enabled", "gate_tg_channel_url", "gate_tg_channel_name",
    "gate_tg_title", "gate_tg_text",
    # Game
    "game_enabled", "game_title", "game_subtitle", "game_prize_text", "game_duration_ms",
]


_BOOL_SETTING_KEYS = {"ann_enabled", "gate_tg_enabled", "game_enabled"}


@app.route("/admin/site", methods=["GET", "POST"])
@admin_required
def admin_site_content():
    if request.method == "POST":
        # Чекбоксы — особый случай
        for bk in _BOOL_SETTING_KEYS:
            set_setting(bk, "1" if request.form.get(bk) else "0")
        for key in SITE_CONTENT_KEYS:
            if key in _BOOL_SETTING_KEYS:
                continue
            val = request.form.get(key, "")
            set_setting(key, val.strip())
        flash("Контент сайта обновлён.", "success")
        return redirect(url_for("admin_site_content"))

    return render_template("admin/site_content.html", s=_site_settings_dict())


# ═══════════════════════════════════════════════════════════════════════════════
#  ИГРА «Поймай орб JARVIS»
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/game")
def game_page():
    if get_setting("game_enabled", "0") != "1":
        flash("Игра сейчас выключена. Зайди позже!", "info")
        return redirect(url_for("index"))

    db = get_conn()
    top_scores = db.execute(
        "SELECT player_name, score, accuracy, combo_max, created_at "
        "FROM game_scores ORDER BY score DESC, created_at ASC LIMIT 10"
    ).fetchall()
    total_plays = db.execute("SELECT COUNT(*) FROM game_scores").fetchone()[0]
    best = db.execute("SELECT MAX(score) FROM game_scores").fetchone()[0] or 0
    return render_template("game.html",
                           top_scores=top_scores,
                           total_plays=total_plays,
                           best_score=best)


@app.route("/api/game/score", methods=["POST"])
def api_game_score():
    if get_setting("game_enabled", "0") != "1":
        return {"ok": False, "error": "Игра выключена"}, 403

    data = request.get_json(silent=True) or {}
    try:
        score    = int(data.get("score", 0))
        accuracy = int(data.get("accuracy", 0))
        combo    = int(data.get("combo_max", 0))
        duration = int(data.get("duration_ms", 30000))
    except (TypeError, ValueError):
        return {"ok": False, "error": "Bad payload"}, 400

    name = (data.get("name", "") or "").strip()[:40] or "Аноним"
    # Базовая валидация — отсеять очевидную чушь
    if score < 0 or score > 100000:
        return {"ok": False, "error": "Невозможный счёт"}, 400
    if accuracy < 0 or accuracy > 100:
        accuracy = max(0, min(100, accuracy))
    if duration < 5000 or duration > 600000:
        return {"ok": False, "error": "Bad duration"}, 400

    import hashlib
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ip_hash = hashlib.md5(ip.encode()).hexdigest()[:12]

    db = get_conn()
    # Анти-спам: не более 1 записи за 10 секунд с одного IP
    last = db.execute(
        "SELECT created_at FROM game_scores WHERE ip_hash=? "
        "ORDER BY created_at DESC LIMIT 1", (ip_hash,)
    ).fetchone()
    if last:
        prev = _dt.datetime.strptime(last["created_at"], "%Y-%m-%d %H:%M:%S")
        if (_dt.datetime.utcnow() - prev).total_seconds() < 10:
            return {"ok": False, "error": "Слишком быстро, подожди немного"}, 429

    db.execute(
        "INSERT INTO game_scores (player_name, score, accuracy, combo_max, duration_ms, ip_hash) "
        "VALUES (?,?,?,?,?,?)",
        (name, score, accuracy, combo, duration, ip_hash)
    )
    db.commit()

    # Возвращаем место в лидерборде
    rank = db.execute(
        "SELECT COUNT(*)+1 FROM game_scores WHERE score > ?", (score,)
    ).fetchone()[0]
    return {"ok": True, "rank": rank}


@app.route("/api/game/leaderboard")
def api_game_leaderboard():
    db = get_conn()
    rows = db.execute(
        "SELECT player_name, score, accuracy, combo_max, created_at "
        "FROM game_scores ORDER BY score DESC, created_at ASC LIMIT 10"
    ).fetchall()
    return {"top": [dict(r) for r in rows]}


# ── Admin: игра ───────────────────────────────────────────────────────────────
@app.route("/admin/game")
@admin_required
def admin_game():
    db = get_conn()
    scores = db.execute(
        "SELECT * FROM game_scores ORDER BY score DESC, created_at ASC LIMIT 100"
    ).fetchall()
    total = db.execute("SELECT COUNT(*) FROM game_scores").fetchone()[0]
    unique = db.execute("SELECT COUNT(DISTINCT ip_hash) FROM game_scores").fetchone()[0]
    best = db.execute("SELECT MAX(score) FROM game_scores").fetchone()[0] or 0
    return render_template("admin/game.html",
                           scores=scores, total=total,
                           unique=unique, best=best)


@app.route("/admin/game/clear", methods=["POST"])
@admin_required
def admin_game_clear():
    db = get_conn()
    db.execute("DELETE FROM game_scores")
    db.commit()
    flash("Все результаты игры удалены.", "info")
    return redirect(url_for("admin_game"))


@app.route("/admin/game/<int:sid>/delete", methods=["POST"])
@admin_required
def admin_game_score_delete(sid):
    db = get_conn()
    db.execute("DELETE FROM game_scores WHERE id=?", (sid,))
    db.commit()
    flash("Результат удалён.", "info")
    return redirect(url_for("admin_game"))


# ─── 404 ───────────────────────────────────────────────────────────────────────
# ═══ AI CHAT API ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/online")
def api_online():
    """Счётчик онлайн: считает уникальных посетителей за последние 3 минуты."""
    import time, hashlib
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ip_hash = hashlib.md5(ip.encode()).hexdigest()[:12]
    db = get_conn()
    # Обновляем/вставляем last_seen
    db.execute("""
        CREATE TABLE IF NOT EXISTS online_users (
            ip_hash TEXT PRIMARY KEY,
            last_seen REAL
        )
    """)
    db.execute(
        "INSERT INTO online_users (ip_hash, last_seen) VALUES (?, ?) "
        "ON CONFLICT(ip_hash) DO UPDATE SET last_seen=excluded.last_seen",
        (ip_hash, time.time())
    )
    # Чистим старых (> 3 минут)
    db.execute("DELETE FROM online_users WHERE last_seen < ?", (time.time() - 180,))
    count = db.execute("SELECT COUNT(*) FROM online_users").fetchone()[0]
    db.commit()
    return jsonify({"online": count})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    import requests, urllib3
    urllib3.disable_warnings()
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"error": "Сообщение пустое"}), 400
    if len(user_msg) > 800:
        return jsonify({"error": "Сообщение слишком длинное"}), 400

    token = _get_gigachat_token()
    if not token:
        return jsonify({"reply": "Извини, сервис AI временно недоступен. Попробуйте позже или задайте вопрос на форуме."})

    try:
        resp = requests.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "model": "GigaChat",
                "messages": [
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                "temperature": 0.7,
                "max_tokens": 250,
                "stream": False,
            },
            timeout=20, verify=False,
        )
        if resp.status_code == 200:
            reply = resp.json()["choices"][0]["message"]["content"].strip()
            return jsonify({"reply": reply})
        return jsonify({"reply": f"Ошибка AI ({resp.status_code}). Попробуйте позже."})
    except Exception as e:
        print(f"[Chat API] {e}")
        return jsonify({"reply": "Нет связи с AI. Проверьте интернет или задайте вопрос на \u0444оруме."})


# ═══ 404 ═════════════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    print("=" * 50)
    print(f"  JARVIS Website → http://localhost:{port}")
    print("  Админка: /admin  (логин: admin / jarvis2024)")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=debug)
