Simple SQLite + SQLAlchemy-lite layer using sqlite3 for simplicity.

import sqlite3
import json
from contextlib import closing
from datetime import datetime
import threading
from config import DATABASE_PATH

_lock = threading.Lock()

def get_conn():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        # movies: id (int autoinc), title, caption, poster_chat_id, poster_message_id, message_ids(json), token, created_at
        cur.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            caption TEXT,
            poster_chat_id INTEGER,
            poster_message_id INTEGER,
            message_ids TEXT,
            token TEXT UNIQUE,
            created_at TEXT
        )
        """)
        # users: id, is_vip (0/1), banned (0/1)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            is_vip INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)
        # channels: chat_id, name, join_link
        cur.execute("""
        CREATE TABLE IF NOT EXISTS force_channels (
            chat_id INTEGER PRIMARY KEY,
            name TEXT,
            invite_link TEXT
        )
        """)
        # ads table (single latest ad)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS waiting_ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_chat_id INTEGER,
            media_message_id INTEGER,
            url TEXT,
            text TEXT,
            created_at TEXT
        )
        """)
        conn.commit()
        conn.close()

def add_movie(title, caption, message_ids, poster_chat_id=None, poster_message_id=None, token=None):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute("""
        INSERT INTO movies (title, caption, poster_chat_id, poster_message_id, message_ids, token, created_at)
        VALUES (?,?,?,?,?,?,?)
        """, (title, caption, poster_chat_id, poster_message_id, json.dumps(message_ids), token, now))
        mid = cur.lastrowid
        conn.commit()
        conn.close()
        return mid

def get_movie_by_id(movie_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def get_movie_by_token(token):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM movies WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def set_movie_poster(movie_id, chat_id, message_id):
    with _lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE movies SET poster_chat_id=?, poster_message_id=? WHERE id=?", (chat_id, message_id, movie_id))
        conn.commit()
        conn.close()

def set_movie_token(movie_id, token):
    with _lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE movies SET token=? WHERE id=?", (token, movie_id))
        conn.commit()
        conn.close()

def list_movies():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM movies ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_user_if_missing(user_id):
    with _lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE id=?", (user_id,))
        if not c.fetchone():
            now = datetime.utcnow().isoformat()
            c.execute("INSERT INTO users (id, created_at) VALUES (?,?)", (user_id, now))
            conn.commit()
        conn.close()

def set_vip(user_id, is_vip: bool):
    add_user_if_missing(user_id)
    with _lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE users SET is_vip=? WHERE id=?", (1 if is_vip else 0, user_id))
        conn.commit()
        conn.close()

def is_vip(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT is_vip FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row["is_vip"]) if row else False

def add_force_channel(chat_id, name=None, invite_link=None):
    with _lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO force_channels (chat_id, name, invite_link) VALUES (?,?,?)", (chat_id, name, invite_link))
        conn.commit()
        conn.close()

def list_force_channels():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM force_channels")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_force_channel(chat_id):
    with _lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM force_channels WHERE chat_id=?", (chat_id,))
        conn.commit()
        conn.close()

def set_waiting_ad(media_chat_id, media_message_id, url=None, text=None):
    with _lock:
        conn = get_conn()
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        c.execute("INSERT INTO waiting_ads (media_chat_id, media_message_id, url, text, created_at) VALUES (?,?,?,?,?)",
                  (media_chat_id, media_message_id, url, text, now))
        conn.commit()
        conn.close()

def get_latest_waiting_ad():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM waiting_ads ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None
```

```python name=models.py
# Lightweight models / helpers for in-memory use (optional).
# For this implementation most DB operations are in db.py.

from typing import List
import json

def parse_message_ids_field(field_value):
    if not field_value:
        return []
    if isinstance(field_value, str):
        try:
            return json.loads(field_value)
        except Exception:
            # fallback comma separated
            return [int(x.strip()) for x in field_value.split(",") if x.strip()]
    if isinstance(field_value, (list, tuple)):
        return list(field_value)
    return []
```
