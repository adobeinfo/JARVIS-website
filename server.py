#!/usr/bin/env python3
"""AE Marketplace Web App — standalone server."""
import sqlite3, os
from pathlib import Path
from aiohttp import web

DB = Path("marketplace.db")
WEB = Path("web")
PORT = int(os.getenv("PORT", "8080"))


def db():
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    return c


def enrich(rows):
    con = db()
    out = []
    for r in rows:
        d = dict(r)
        cat = con.execute("SELECT name,icon FROM categories WHERE id=?", (d.get("category_id"),)).fetchone()
        d["category_name"] = cat["name"] if cat else ""
        d["category_icon"] = cat["icon"] if cat else ""
        out.append(d)
    con.close()
    return out


def init():
    con = sqlite3.connect(str(DB))
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT, is_admin INTEGER DEFAULT 0, is_blocked INTEGER DEFAULT 0, language TEXT DEFAULT 'ru', referrer_id INTEGER, balance INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, icon TEXT DEFAULT '📁', description TEXT DEFAULT '', sort_order INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '', category_id INTEGER, tags TEXT DEFAULT '', price INTEGER DEFAULT 0, is_free INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 0, is_new INTEGER DEFAULT 1, is_active INTEGER DEFAULT 1, cover_url TEXT DEFAULT '', file_id TEXT DEFAULT '', preview_video TEXT DEFAULT '', file_size TEXT DEFAULT '', ae_version TEXT DEFAULT '', resolution TEXT DEFAULT '', fps TEXT DEFAULT '', plugins TEXT DEFAULT '', downloads INTEGER DEFAULT 0, views INTEGER DEFAULT 0, rating REAL DEFAULT 0.0, discount_percent INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, project_id INTEGER, amount INTEGER DEFAULT 0, payment_id TEXT DEFAULT '', status TEXT DEFAULT 'completed', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, project_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, project_id));
    CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, project_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, project_id));
    CREATE TABLE IF NOT EXISTS promo_codes (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, discount_percent INTEGER DEFAULT 0, max_uses INTEGER DEFAULT 0, used_count INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, expires_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS lots (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '', price INTEGER DEFAULT 0, quantity INTEGER DEFAULT 1, sold INTEGER DEFAULT 0, file_id TEXT DEFAULT '', image_url TEXT DEFAULT '', discount_percent INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, expires_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, project_id INTEGER, rating INTEGER DEFAULT 5, text TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS banners (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT DEFAULT '', image_url TEXT DEFAULT '', link TEXT DEFAULT '', is_active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT DEFAULT '');
    """)
    for n, i in [("Logo Animation","🎯"),("Typography","🔤"),("Promo","📣"),("Corporate","🏢"),("HUD","🖥"),("Glitch","⚡"),("Minimal","✨"),("Titles","📝"),("Transitions","🔄"),("Instagram","📱"),("TikTok","🎵"),("YouTube","▶️"),("Slideshow","🖼"),("Pack","📦"),("3D","🧊")]:
        con.execute("INSERT OR IGNORE INTO categories(name,icon) VALUES(?,?)", (n,i))
    con.commit()
    con.close()


# ─── Handlers ────────────────────────────────────────────────

async def index(r): return web.FileResponse(WEB/"index.html")
async def css(r): return web.FileResponse(WEB/"style.css")
async def js(r): return web.FileResponse(WEB/"script.js")

async def api_projects(r):
    con=db(); rows=con.execute("SELECT * FROM projects WHERE is_active=1 ORDER BY created_at DESC LIMIT 50").fetchall(); con.close()
    return web.json_response(enrich(rows))

async def api_categories(r):
    con=db(); rows=con.execute("SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order,name").fetchall(); con.close()
    return web.json_response([dict(x) for x in rows])

async def api_project(r):
    con=db(); row=con.execute("SELECT * FROM projects WHERE id=?",(int(r.match_info["id"]),)).fetchone()
    if not row: con.close(); return web.json_response({"error":"not found"},status=404)
    d=dict(row)
    cat=con.execute("SELECT name,icon FROM categories WHERE id=?",((d["category_id"],))).fetchone()
    d["category_name"]=cat["name"] if cat else ""
    d["category_icon"]=cat["icon"] if cat else ""
    con.close()
    return web.json_response(d)

async def api_search(r):
    d=await r.json(); q=d.get("query",""); cid=d.get("category_id")
    con=db()
    qq="SELECT * FROM projects WHERE is_active=1 AND (title LIKE ? OR tags LIKE ? OR description LIKE ?)"
    pp=[f"%{q}%",f"%{q}%",f"%{q}%"]
    if cid: qq+=" AND category_id=?"; pp.append(cid)
    qq+=" ORDER BY created_at DESC LIMIT 30"
    rows=con.execute(qq,pp).fetchall(); con.close()
    return web.json_response(enrich(rows))

async def api_popular(r):
    con=db(); rows=con.execute("SELECT * FROM projects WHERE is_active=1 ORDER BY downloads DESC LIMIT 20").fetchall(); con.close()
    return web.json_response(enrich(rows))

async def api_new(r):
    con=db(); rows=con.execute("SELECT * FROM projects WHERE is_active=1 AND is_new=1 ORDER BY created_at DESC LIMIT 20").fetchall(); con.close()
    return web.json_response(enrich(rows))

async def api_premium(r):
    con=db(); rows=con.execute("SELECT * FROM projects WHERE is_active=1 AND is_premium=1 ORDER BY created_at DESC LIMIT 20").fetchall(); con.close()
    return web.json_response(enrich(rows))

async def api_favorites(r):
    d=await r.json(); uid=d.get("user_id",0)
    con=db(); rows=con.execute("SELECT f.*,pr.title,pr.cover_url,pr.price,pr.is_free,pr.discount_percent FROM favorites f JOIN projects pr ON f.project_id=pr.id WHERE f.user_id=? ORDER BY f.created_at DESC",(uid,)).fetchall(); con.close()
    return web.json_response([dict(x) for x in rows])

async def api_toggle_fav(r):
    d=await r.json(); uid=d.get("user_id",0); pid=d.get("project_id",0)
    con=db(); ex=con.execute("SELECT 1 FROM favorites WHERE user_id=? AND project_id=?",((uid,pid))).fetchone()
    if ex: con.execute("DELETE FROM favorites WHERE user_id=? AND project_id=?",((uid,pid))); a=False
    else: con.execute("INSERT INTO favorites(user_id,project_id) VALUES(?,?)",((uid,pid))); a=True
    con.commit(); con.close()
    return web.json_response({"added":a})

async def api_purchases(r):
    d=await r.json(); uid=d.get("user_id",0)
    con=db(); rows=con.execute("SELECT p.*,pr.title,pr.cover_url,pr.price,pr.file_id FROM purchases p JOIN projects pr ON p.project_id=pr.id WHERE p.user_id=? ORDER BY p.created_at DESC",(uid,)).fetchall(); con.close()
    return web.json_response([dict(x) for x in rows])

async def api_reviews(r):
    pid=int(r.match_info["id"])
    con=db(); rows=con.execute("SELECT r.*,u.first_name,u.username FROM reviews r JOIN users u ON r.user_id=u.id WHERE r.project_id=? ORDER BY r.created_at DESC",(pid,)).fetchall(); con.close()
    return web.json_response([dict(x) for x in rows])

async def api_add_review(r):
    d=await r.json(); uid=d.get("user_id",0); pid=d.get("project_id",0); rating=d.get("rating",5); txt=d.get("text","")
    con=db(); con.execute("INSERT INTO reviews(user_id,project_id,rating,text) VALUES(?,?,?,?)",(uid,pid,rating,txt))
    avg=con.execute("SELECT AVG(rating) FROM reviews WHERE project_id=?",((pid,))).fetchone()[0]
    con.execute("UPDATE projects SET rating=? WHERE id=?",(round(avg,1) if avg else 0,pid))
    con.commit(); con.close()
    return web.json_response({"ok":True})

async def api_cart(r):
    d=await r.json(); uid=d.get("user_id",0)
    con=db(); rows=con.execute("SELECT c.*,pr.title,pr.cover_url,pr.price,pr.discount_percent,pr.is_free FROM cart c JOIN projects pr ON c.project_id=pr.id WHERE c.user_id=?",(uid,)).fetchall(); con.close()
    return web.json_response([dict(x) for x in rows])

async def api_add_cart(r):
    d=await r.json(); uid=d.get("user_id",0); pid=d.get("project_id",0)
    con=db(); ex=con.execute("SELECT 1 FROM cart WHERE user_id=? AND project_id=?",((uid,pid))).fetchone()
    if ex: con.close(); return web.json_response({"added":False})
    con.execute("INSERT INTO cart(user_id,project_id) VALUES(?,?)",((uid,pid))); con.commit(); con.close()
    return web.json_response({"added":True})

async def api_rm_cart(r):
    d=await r.json(); uid=d.get("user_id",0); pid=d.get("project_id",0)
    con=db(); con.execute("DELETE FROM cart WHERE user_id=? AND project_id=?",((uid,pid))); con.commit(); con.close()
    return web.json_response({"ok":True})

async def api_profile(r):
    d=await r.json(); uid=d.get("user_id",0)
    con=db(); u=con.execute("SELECT * FROM users WHERE id=?",((uid,))).fetchone()
    if not u: con.close(); return web.json_response({"error":"not found"},status=404)
    u=dict(u)
    u["purchases_count"]=con.execute("SELECT COUNT(*) FROM purchases WHERE user_id=?",((uid,))).fetchone()[0]
    u["total_spent"]=con.execute("SELECT COALESCE(SUM(amount),0) FROM purchases WHERE user_id=?",((uid,))).fetchone()[0]
    u["favorites_count"]=con.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?",((uid,))).fetchone()[0]
    con.close()
    return web.json_response(u)


app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/index.html", index)
app.router.add_get("/style.css", css)
app.router.add_get("/script.js", js)
app.router.add_get("/api/projects", api_projects)
app.router.add_get("/api/categories", api_categories)
app.router.add_get("/api/projects/{id}", api_project)
app.router.add_post("/api/search", api_search)
app.router.add_get("/api/popular", api_popular)
app.router.add_get("/api/new", api_new)
app.router.add_get("/api/premium", api_premium)
app.router.add_post("/api/favorites", api_favorites)
app.router.add_post("/api/toggle_favorite", api_toggle_fav)
app.router.add_post("/api/purchases", api_purchases)
app.router.add_get("/api/reviews/{id}", api_reviews)
app.router.add_post("/api/reviews", api_add_review)
app.router.add_post("/api/cart", api_cart)
app.router.add_post("/api/cart/add", api_add_cart)
app.router.add_post("/api/cart/remove", api_rm_cart)
app.router.add_post("/api/profile", api_profile)

if __name__ == "__main__":
    init()
    print(f"Server: http://0.0.0.0:{PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
