import os
import functools
import json as _json
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_file, g, abort, jsonify
)
from werkzeug.security import check_password_hash
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "jarvis-rockstar-secret-2024")

# Инициализируем БД при старте (для gunicorn тоже)
with app.app_context():
    init_db()

SETUP_FILE = os.path.join(os.path.dirname(__file__), "..", "setup_output", "JARVIS_Setup_v22.exe")

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


# ═══════════════════════════════════════════════════════════════════════════════
#  ПУБЛИЧНЫЕ МАРШРУТЫ
# ═══════════════════════════════════════════════════════════════════════════════

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
    exists = os.path.isfile(SETUP_FILE)
    size_mb = round(os.path.getsize(SETUP_FILE) / 1024 / 1024, 1) if exists else 0
    return render_template("download.html", file_exists=exists, size_mb=size_mb)


@app.route("/download/file")
def download_file():
    if not os.path.isfile(SETUP_FILE):
        flash("Файл установщика временно недоступен.", "error")
        return redirect(url_for("download"))
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
    return send_file(
        SETUP_FILE,
        as_attachment=True,
        download_name="JARVIS_Setup_v22.exe"
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
    return render_template("forum.html", categories=categories)


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


# ─── 404 ───────────────────────────────────────────────────────────────────────
# ═══ AI CHAT API ═══════════════════════════════════════════════════════════════════════════════

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
