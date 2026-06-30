#!/usr/bin/env python3
"""AE Marketplace — Web App Server (отдельный от бота)
Запуск: python server.py
"""
import sqlite3
import os
from pathlib import Path
from aiohttp import web

DB_PATH = Path(__file__).parent.parent / "marketplace.db"
WEB_DIR = Path(__file__).parent / "web"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def enrich(rows):
    conn = get_db()
    result = []
    for r in rows:
        d = dict(r)
        cat = conn.execute("SELECT name,icon FROM categories WHERE id=?", (d["category_id"],)).fetchone()
        d["category_name"] = cat["name"] if cat else ""
        d["category_icon"] = cat["icon"] if cat else ""
        result.append(d)
    conn.close()
    return result


# ─── Static ─────────────────────────────────────────────────────

async def handle_index(request):
    return web.FileResponse(WEB_DIR / "index.html")

async def handle_css(request):
    return web.FileResponse(WEB_DIR / "style.css")

async def handle_js(request):
    return web.FileResponse(WEB_DIR / "script.js")


# ─── API ────────────────────────────────────────────────────────

async def api_projects(request):
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects WHERE is_active=1 ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    return web.json_response(enrich(rows))

async def api_categories(request):
    conn = get_db()
    rows = conn.execute("SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order, name").fetchall()
    conn.close()
    return web.json_response([dict(r) for r in rows])

async def api_project(request):
    pid = int(request.match_info["id"])
    conn = get_db()
    r = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    if not r:
        conn.close()
        return web.json_response({"error": "not found"}, status=404)
    d = dict(r)
    cat = conn.execute("SELECT name,icon FROM categories WHERE id=?", (d["category_id"],)).fetchone()
    d["category_name"] = cat["name"] if cat else ""
    d["category_icon"] = cat["icon"] if cat else ""
    conn.close()
    return web.json_response(d)

async def api_search(request):
    data = await request.json()
    q = data.get("query", "")
    cat_id = data.get("category_id")
    conn = get_db()
    query = "SELECT * FROM projects WHERE is_active=1 AND (title LIKE ? OR tags LIKE ? OR description LIKE ?)"
    params = [f"%{q}%", f"%{q}%", f"%{q}%"]
    if cat_id:
        query += " AND category_id=?"
        params.append(cat_id)
    query += " ORDER BY created_at DESC LIMIT 30"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return web.json_response(enrich(rows))

async def api_popular(request):
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects WHERE is_active=1 ORDER BY downloads DESC LIMIT 20").fetchall()
    conn.close()
    return web.json_response(enrich(rows))

async def api_new(request):
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects WHERE is_active=1 AND is_new=1 ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return web.json_response(enrich(rows))

async def api_premium(request):
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects WHERE is_active=1 AND is_premium=1 ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return web.json_response(enrich(rows))

async def api_favorites(request):
    data = await request.json()
    user_id = data.get("user_id", 0)
    conn = get_db()
    rows = conn.execute("""
        SELECT f.*, pr.title, pr.cover_url, pr.price, pr.is_free, pr.discount_percent
        FROM favorites f JOIN projects pr ON f.project_id=pr.id
        WHERE f.user_id=? ORDER BY f.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return web.json_response([dict(r) for r in rows])

async def api_toggle_favorite(request):
    data = await request.json()
    user_id = data.get("user_id", 0)
    project_id = data.get("project_id", 0)
    conn = get_db()
    r = conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND project_id=?", (user_id, project_id)).fetchone()
    if r:
        conn.execute("DELETE FROM favorites WHERE user_id=? AND project_id=?", (user_id, project_id))
        added = False
    else:
        conn.execute("INSERT INTO favorites(user_id,project_id) VALUES(?,?)", (user_id, project_id))
        added = True
    conn.commit()
    conn.close()
    return web.json_response({"added": added})

async def api_purchases(request):
    data = await request.json()
    user_id = data.get("user_id", 0)
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, pr.title, pr.cover_url, pr.price, pr.file_id, pr.description
        FROM purchases p JOIN projects pr ON p.project_id=pr.id
        WHERE p.user_id=? ORDER BY p.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return web.json_response([dict(r) for r in rows])

async def api_reviews(request):
    pid = int(request.match_info["id"])
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*, u.first_name, u.username FROM reviews r
        JOIN users u ON r.user_id=u.id WHERE r.project_id=? ORDER BY r.created_at DESC
    """, (pid,)).fetchall()
    conn.close()
    return web.json_response([dict(r) for r in rows])

async def api_add_review(request):
    data = await request.json()
    user_id = data.get("user_id", 0)
    project_id = data.get("project_id", 0)
    rating = data.get("rating", 5)
    text = data.get("text", "")
    if not user_id or not project_id:
        return web.json_response({"error": "missing fields"}, status=400)
    conn = get_db()
    conn.execute("INSERT INTO reviews(user_id,project_id,rating,text) VALUES(?,?,?,?)",
                 (user_id, project_id, rating, text))
    avg = conn.execute("SELECT AVG(rating) FROM reviews WHERE project_id=?", (project_id,)).fetchone()[0]
    conn.execute("UPDATE projects SET rating=? WHERE id=?", (round(avg, 1) if avg else 0, project_id))
    conn.commit()
    conn.close()
    return web.json_response({"ok": True})

async def api_cart(request):
    data = await request.json()
    user_id = data.get("user_id", 0)
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, pr.title, pr.cover_url, pr.price, pr.discount_percent, pr.is_free
        FROM cart c JOIN projects pr ON c.project_id=pr.id
        WHERE c.user_id=? ORDER BY c.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return web.json_response([dict(r) for r in rows])

async def api_add_cart(request):
    data = await request.json()
    user_id = data.get("user_id", 0)
    project_id = data.get("project_id", 0)
    conn = get_db()
    r = conn.execute("SELECT 1 FROM cart WHERE user_id=? AND project_id=?", (user_id, project_id)).fetchone()
    if r:
        conn.close()
        return web.json_response({"added": False})
    conn.execute("INSERT INTO cart(user_id,project_id) VALUES(?,?)", (user_id, project_id))
    conn.commit()
    conn.close()
    return web.json_response({"added": True})

async def api_remove_cart(request):
    data = await request.json()
    user_id = data.get("user_id", 0)
    project_id = data.get("project_id", 0)
    conn = get_db()
    conn.execute("DELETE FROM cart WHERE user_id=? AND project_id=?", (user_id, project_id))
    conn.commit()
    conn.close()
    return web.json_response({"ok": True})

async def api_profile(request):
    data = await request.json()
    user_id = data.get("user_id", 0)
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return web.json_response({"error": "not found"}, status=404)
    u = dict(user)
    u["purchases_count"] = conn.execute("SELECT COUNT(*) FROM purchases WHERE user_id=?", (user_id,)).fetchone()[0]
    u["total_spent"] = conn.execute("SELECT COALESCE(SUM(amount),0) FROM purchases WHERE user_id=?", (user_id,)).fetchone()[0]
    u["favorites_count"] = conn.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?", (user_id,)).fetchone()[0]
    conn.close()
    return web.json_response(u)


# ─── App ────────────────────────────────────────────────────────

def create_app():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/index.html", handle_index)
    app.router.add_get("/style.css", handle_css)
    app.router.add_get("/script.js", handle_js)
    app.router.add_get("/api/projects", api_projects)
    app.router.add_get("/api/categories", api_categories)
    app.router.add_get("/api/projects/{id}", api_project)
    app.router.add_post("/api/search", api_search)
    app.router.add_get("/api/popular", api_popular)
    app.router.add_get("/api/new", api_new)
    app.router.add_get("/api/premium", api_premium)
    app.router.add_post("/api/favorites", api_favorites)
    app.router.add_post("/api/toggle_favorite", api_toggle_favorite)
    app.router.add_post("/api/purchases", api_purchases)
    app.router.add_get("/api/reviews/{id}", api_reviews)
    app.router.add_post("/api/reviews", api_add_review)
    app.router.add_post("/api/cart", api_cart)
    app.router.add_post("/api/cart/add", api_add_cart)
    app.router.add_post("/api/cart/remove", api_remove_cart)
    app.router.add_post("/api/profile", api_profile)
    return app


CATEGORIES = [
    ("Logo Animation", "🎯"), ("Typography", "🔤"), ("Promo", "📣"),
    ("Corporate", "🏢"), ("HUD", "🖥"), ("Glitch", "⚡"),
    ("Minimal", "✨"), ("Titles", "📝"), ("Transitions", "🔄"),
    ("Instagram", "📱"), ("TikTok", "🎵"), ("YouTube", "▶️"),
    ("Slideshow", "🖼"), ("Pack", "📦"), ("3D", "🧊"),
]

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT,
        is_admin INTEGER DEFAULT 0, is_blocked INTEGER DEFAULT 0,
        language TEXT DEFAULT 'ru', referrer_id INTEGER,
        balance INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
        icon TEXT DEFAULT '📁', description TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        description TEXT DEFAULT '', category_id INTEGER, tags TEXT DEFAULT '',
        price INTEGER DEFAULT 0, is_free INTEGER DEFAULT 0,
        is_premium INTEGER DEFAULT 0, is_new INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1, cover_url TEXT DEFAULT '',
        file_id TEXT DEFAULT '', preview_video TEXT DEFAULT '',
        file_size TEXT DEFAULT '', ae_version TEXT DEFAULT '',
        resolution TEXT DEFAULT '', fps TEXT DEFAULT '',
        plugins TEXT DEFAULT '', downloads INTEGER DEFAULT 0,
        views INTEGER DEFAULT 0, rating REAL DEFAULT 0.0,
        discount_percent INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS project_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER, file_id TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, project_id INTEGER,
        amount INTEGER DEFAULT 0, payment_id TEXT DEFAULT '',
        status TEXT DEFAULT 'completed',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, project_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, project_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, project_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, project_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );
    CREATE TABLE IF NOT EXISTS promo_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL, discount_percent INTEGER DEFAULT 0,
        discount_amount INTEGER DEFAULT 0, max_uses INTEGER DEFAULT 0,
        used_count INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
        expires_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS lots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, description TEXT DEFAULT '',
        price INTEGER DEFAULT 0, quantity INTEGER DEFAULT 1,
        sold INTEGER DEFAULT 0, file_id TEXT DEFAULT '',
        image_url TEXT DEFAULT '', discount_percent INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1, expires_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, project_id INTEGER,
        rating INTEGER DEFAULT 5, text TEXT DEFAULT '',
        is_approved INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );
    CREATE TABLE IF NOT EXISTS banners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT DEFAULT '', image_url TEXT DEFAULT '',
        link TEXT DEFAULT '', is_active INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT DEFAULT ''
    );
    """)
    for name, icon in CATEGORIES:
        conn.execute("INSERT OR IGNORE INTO categories(name, icon) VALUES(?, ?)", (name, icon))
    conn.commit()
    conn.close()
    print(f"[OK] Database created: {DB_PATH}")


if __name__ == "__main__":
    init_db()
    print(f"[INFO] AE Marketplace Web App")
    print(f"[INFO] http://{HOST}:{PORT}")
    print(f"[INFO] DB: {DB_PATH}")
    web.run_app(create_app(), host=HOST, port=PORT)
