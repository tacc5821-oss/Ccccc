
```python name=config.py
# Configuration file - keep secrets out of source control.
# Optionally use environment variables (.env) - python-dotenv is in requirements.

import os
from dotenv import load_dotenv
load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))            # e.g. 19703932
API_HASH = os.getenv("API_HASH", "")              # e.g. "2fe31e84..."
BOT_TOKEN = os.getenv("BOT_TOKEN", "")            # e.g. "8580...:AAFoo..."
OWNER_ID = int(os.getenv("OWNER_ID", "0"))        # e.g. 1735522859
STORAGE_CHAT_ID = int(os.getenv("STORAGE_CHAT_ID", "0"))  # e.g. -1002849045181

# General settings
DEFAULT_SEND_DELAY = float(os.getenv("DEFAULT_SEND_DELAY", "2.0"))  # seconds between copied messages
WAIT_AD_SECONDS = int(os.getenv("WAIT_AD_SECONDS", "10"))
VIP_PRICE_LABEL = os.getenv("VIP_PRICE_LABEL", "Contact @osamu1123 to buy VIP")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")  # Optional: Bot username for deep links

DATABASE_PATH = os.getenv("DATABASE_PATH", "data.db")
```

```python name=db.py
# Simple SQLite + SQLAlchemy-lite layer using sqlite3 for simplicity.

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

```python name=utils.py
# Utility helpers: parse message id ranges, generate tokens, admin check, format.

import re
import secrets
import json
from typing import List

def parse_ids_text(text: str) -> List[int]:
    # Supports comma separated and ranges like 100-105 and combos
    parts = re.split(r"[,\s]+", text.strip())
    ids = []
    for p in parts:
        if not p:
            continue
        if "-" in p:
            try:
                a,b = p.split("-",1)
                a,b = int(a), int(b)
                if a <= b:
                    ids.extend(list(range(a, b+1)))
                else:
                    ids.extend(list(range(b, a+1)))
            except:
                pass
        else:
            try:
                ids.append(int(p))
            except:
                pass
    # remove duplicates and keep order
    seen = set()
    out = []
    for x in ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def gen_token(nbytes=6):
    return secrets.token_urlsafe(nbytes)

def stringify_ids(ids):
    return json.dumps(ids)
```

```python name=handlers_admin.py
# Admin handlers: add_movie, set_poster, genlink, vip control, channel management, broadcast.
# This module is imported by bot.py.

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID, STORAGE_CHAT_ID, BOT_USERNAME
from db import add_movie, set_movie_poster, set_movie_token, add_user_if_missing, set_vip, add_force_channel, list_force_channels, delete_force_channel, list_movies, get_movie_by_id
from utils import parse_ids_text, gen_token
import json
import asyncio

def register_admin_handlers(app):
    @app.on_message(filters.command("dashboard") & filters.private & filters.user(OWNER_ID))
    async def dashboard(_, m: Message):
        text = "Admin Dashboard"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Add Movie (usage)", callback_data="admin:help_add")],
            [InlineKeyboardButton("List Movies", callback_data="admin:list_movies")],
            [InlineKeyboardButton("Add VIP", callback_data="admin:add_vip"), InlineKeyboardButton("Remove VIP", callback_data="admin:remove_vip")],
            [InlineKeyboardButton("Manage Channels", callback_data="admin:list_channels")],
            [InlineKeyboardButton("Set Waiting Ad", callback_data="admin:waiting_ad")]
        ])
        await m.reply(text, reply_markup=kb)

    @app.on_message(filters.command("add_movie") & filters.private & filters.user(OWNER_ID))
    async def cmd_add_movie(_, m: Message):
        # Usage example:
        # /add_movie Movie Title|Caption text|100-120
        if len(m.text.split(" ",1)) < 2:
            await m.reply("Usage:\n/add_movie <title>|<caption>|<message_ids>\nmessage_ids e.g. 100-120 or 101,103,105 or combo")
            return
        try:
            payload = m.text.split(" ",1)[1]
            title, caption, ids_text = [p.strip() for p in payload.split("|",2)]
        except:
            await m.reply("Invalid format. Use:\n/add_movie <title>|<caption>|<message_ids>")
            return
        message_ids = parse_ids_text(ids_text)
        if not message_ids:
            await m.reply("No valid message IDs parsed.")
            return
        # we store message IDs only; poster can be set with set_poster
        mid = add_movie(title=title, caption=caption, message_ids=message_ids)
        await m.reply(f"Movie added with id: {mid}\nUse /set_poster {mid}|<poster_message_id_from_storage_group>\nUse /genlink {mid} to create deep link token")

    @app.on_message(filters.command("set_poster") & filters.private & filters.user(OWNER_ID))
    async def cmd_set_poster(_, m: Message):
        # /set_poster <movie_id>|<poster_message_id>
        if len(m.text.split(" ",1)) < 2:
            await m.reply("Usage:\n/set_poster <movie_id>|<poster_message_id>")
            return
        try:
            payload = m.text.split(" ",1)[1]
            movie_id_s, poster_msg_s = [p.strip() for p in payload.split("|",1)]
            movie_id = int(movie_id_s)
            poster_msg = int(poster_msg_s)
        except:
            await m.reply("Invalid input.")
            return
        movie = get_movie_by_id(movie_id)
        if not movie:
            await m.reply("Movie not found.")
            return
        # verify poster exists in storage chat
        try:
            await app.get_messages(STORAGE_CHAT_ID, [poster_msg])
        except Exception as e:
            await m.reply(f"Couldn't find that message in storage group: {e}")
            return
        set_movie_poster(movie_id, STORAGE_CHAT_ID, poster_msg)
        await m.reply("Poster set successfully.")

    @app.on_message(filters.command("genlink") & filters.private & filters.user(OWNER_ID))
    async def cmd_genlink(_, m: Message):
        # /genlink <movie_id>
        if len(m.text.split(" ",1)) < 2:
            await m.reply("Usage:\n/genlink <movie_id>")
            return
        try:
            movie_id = int(m.text.split(" ",1)[1].strip())
        except:
            await m.reply("Invalid movie id")
            return
        movie = get_movie_by_id(movie_id)
        if not movie:
            await m.reply("Movie not found.")
            return
        token = gen_token()
        set_movie_token(movie_id, token)
        # Build deep link
        if BOT_USERNAME:
            link = f"https://t.me/{BOT_USERNAME}?start={token}"
        else:
            link = f"Use: /start {token}"
        await m.reply(f"Token generated for movie {movie_id}:\n{token}\nDeep link: {link}")

    @app.on_message(filters.command("add_vip") & filters.private & filters.user(OWNER_ID))
    async def cmd_add_vip(_, m: Message):
        if len(m.text.split(" ",1)) < 2:
            await m.reply("Usage: /add_vip <user_id>")
            return
        try:
            uid = int(m.text.split(" ",1)[1].strip())
        except:
            await m.reply("Invalid user id")
            return
        set_vip(uid, True)
        await m.reply(f"User {uid} set as VIP.")

    @app.on_message(filters.command("remove_vip") & filters.private & filters.user(OWNER_ID))
    async def cmd_remove_vip(_, m: Message):
        if len(m.text.split(" ",1)) < 2:
            await m.reply("Usage: /remove_vip <user_id>")
            return
        try:
            uid = int(m.text.split(" ",1)[1].strip())
        except:
            await m.reply("Invalid user id")
            return
        set_vip(uid, False)
        await m.reply(f"User {uid} VIP removed.")

    @app.on_message(filters.command("add_channel") & filters.private & filters.user(OWNER_ID))
    async def cmd_add_channel(_, m: Message):
        # /add_channel <chat_id>|<name>|<invite_link>
        if len(m.text.split(" ",1)) < 2:
            await m.reply("Usage: /add_channel <chat_id>|<name>|<invite_link>")
            return
        try:
            payload = m.text.split(" ",1)[1]
            chat_id_s, name, invite = [p.strip() for p in payload.split("|",2)]
            chat_id = int(chat_id_s)
        except:
            await m.reply("Invalid params.")
            return
        add_force_channel(chat_id, name, invite)
        await m.reply("Channel added.")

    @app.on_message(filters.command("list_channels") & filters.private & filters.user(OWNER_ID))
    async def cmd_list_channels(_, m: Message):
        rows = list_force_channels()
        if not rows:
            await m.reply("No force-join channels configured.")
            return
        text = "Force Join Channels:\n"
        for r in rows:
            text += f"- {r['name'] or r['chat_id']} | {r.get('invite_link')}\n"
        await m.reply(text)

    @app.on_message(filters.command("broadcast") & filters.private & filters.user(OWNER_ID))
    async def cmd_broadcast(_, m: Message):
        if len(m.text.split(" ",1)) < 2:
            await m.reply("Usage: /broadcast <text>")
            return
        text = m.text.split(" ",1)[1]
        # naive broadcast: iterate all users
        from db import get_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users")
        rows = cur.fetchall()
        conn.close()
        count = 0
        for r in rows:
            try:
                await app.send_message(r["id"], text)
                count += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
        await m.reply(f"Broadcast sent to {count} users.")
```

```python name=handlers_user.py
# User-facing handlers: /start deep link, force-join check, try again, delivery pipeline.

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import STORAGE_CHAT_ID, OWNER_ID, DEFAULT_SEND_DELAY, WAIT_AD_SECONDS, VIP_PRICE_LABEL
from db import get_movie_by_token, get_movie_by_id, add_user_if_missing, is_vip, list_force_channels, get_latest_waiting_ad
from utils import parse_ids_text
import asyncio

def register_user_handlers(app):
    @app.on_message(filters.command("start") & filters.private)
    async def start_handler(client, m):
        # /start or /start token
        args = m.text.split(maxsplit=1)
        token = None
        if len(args) > 1:
            token = args[1].strip()
        if not token:
            await m.reply("Welcome! Send me a valid movie link to start.")
            return
        movie = get_movie_by_token(token)
        if not movie:
            await m.reply("Invalid or expired link.")
            return
        uid = m.from_user.id
        add_user_if_missing(uid)
        # force join check
        chan_rows = list_force_channels()
        not_joined = []
        for ch in chan_rows:
            try:
                mem = await client.get_chat_member(ch["chat_id"], uid)
                if mem.status not in ("member","administrator","creator"):
                    not_joined.append(ch)
            except Exception:
                not_joined.append(ch)
        if not_joined:
            # show join prompt
            buttons = []
            for ch in not_joined:
                link = ch.get("invite_link") or f"https://t.me/{ch['chat_id']}"
                buttons.append([InlineKeyboardButton(f"Join {ch.get('name') or ch['chat_id']}", url=link)])
            buttons.append([InlineKeyboardButton("Try Again", callback_data=f"tryagain:{movie['id']}")])
            await m.reply("Channel Join required. Please join the channels below and press Try Again.", reply_markup=InlineKeyboardMarkup(buttons))
            return
        # user joined all
        await deliver_movie(client, m.chat.id, movie)

    @app.on_callback_query()
    async def callbacks(client, cq: CallbackQuery):
        data = cq.data or ""
        if data.startswith("tryagain:"):
            movie_id = int(data.split(":",1)[1])
            movie = get_movie_by_id(movie_id)
            if not movie:
                await cq.answer("Movie not found.", show_alert=True)
                return
            uid = cq.from_user.id
            # re-check force join
            chan_rows = list_force_channels()
            not_joined = []
            for ch in chan_rows:
                try:
                    mem = await client.get_chat_member(ch["chat_id"], uid)
                    if mem.status not in ("member","administrator","creator"):
                        not_joined.append(ch)
                except Exception:
                    not_joined.append(ch)
            if not_joined:
                await cq.answer("You still haven't joined required channels.", show_alert=True)
                return
            await cq.message.delete()
            await deliver_movie(client, cq.from_user.id, movie)

    async def deliver_movie(client, chat_id, movie_row):
        # Main entry point for delivery flow
        movie = movie_row
        uid = chat_id
        # If banned - simple check could be added
        # Check VIP
        vip = is_vip(uid)
        # Send poster + inline menu (as per spec: not showing poster to VIP? The spec says: VIP -> direct delivery. Non-VIP show ad and poster?
        # We'll show poster and caption with buttons for both; videos are delivered after ad / immediately for VIP.
        if movie.get("poster_chat_id") and movie.get("poster_message_id"):
            try:
                await client.copy_message(chat_id, movie["poster_chat_id"], movie["poster_message_id"], caption=movie.get("caption") or "")
            except Exception:
                # fallback to send text
                await client.send_message(chat_id, movie.get("caption") or movie.get("title") or "Here's your movie.")
        else:
            await client.send_message(chat_id, movie.get("caption") or movie.get("title") or "Here's your movie.")

        # build inline menu below caption
        menu = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ SERIES CHANNEL", url="https://t.me/your_series_channel_here")],
            [InlineKeyboardButton("🍿 MOVIE CHANNEL", url="https://t.me/your_movie_channel_here")],
            [InlineKeyboardButton("🔗 အကူအညီ", url="https://t.me/your_help_link")],
            [InlineKeyboardButton("ℹ️ ABOUT", callback_data="about_bot")],
            [InlineKeyboardButton("👨‍💻 Owner", url=f"https://t.me/{OWNER_ID}")],
        ])
        await client.send_message(chat_id, "Choose:", reply_markup=menu)

        # Delivery logic
        msg_ids = []
        try:
            import json
            msg_ids = json.loads(movie.get("message_ids") or "[]")
        except:
            msg_ids = []
        if not msg_ids:
            await client.send_message(chat_id, "No video segments found for this movie.")
            return

        if vip:
            await client.send_message(chat_id, "VIP detected — starting delivery...")
            # immediate delivery, short interval
            for mid in msg_ids:
                try:
                    await client.copy_message(chat_id, STORAGE_CHAT_ID, int(mid))
                    await asyncio.sleep(DEFAULT_SEND_DELAY)
                except Exception as e:
                    # skip problematic message
                    pass
            await client.send_message(chat_id, "Delivery finished.")
            return

        # Non-VIP: show waiting ad first
        ad = get_latest_waiting_ad()
        if ad:
            # try to show ad media if present
            try:
                if ad.get("media_message_id") and ad.get("media_chat_id"):
                    await client.copy_message(chat_id, ad["media_chat_id"], ad["media_message_id"], caption=ad.get("text", "Advertisement"))
                else:
                    await client.send_message(chat_id, ad.get("text", "Advertisement"))
            except Exception:
                try:
                    if ad.get("text"):
                        await client.send_message(chat_id, ad.get("text"))
                except:
                    pass
        else:
            # generic waiting message
            await client.send_message(chat_id, f"Please wait... advertisement (you can buy VIP to bypass). {VIP_PRICE_LABEL}")

        # Show Buy VIP button under ad
        buy_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Buy VIP", url=f"https://t.me/osamu1123")],
            [InlineKeyboardButton("Try Again", callback_data=f"deliver_now:{movie['id']}")]
        ])
        sent = await client.send_message(chat_id, f"Waiting for {WAIT_AD_SECONDS} seconds before delivery. Or buy VIP to skip.", reply_markup=buy_kb)
        # Sleep WAIT_AD_SECONDS then deliver
        await asyncio.sleep(WAIT_AD_SECONDS)
        # Check again VIP status in case user bought
        if is_vip(chat_id):
            await client.send_message(chat_id, "VIP detected now — starting delivery...")
            for mid in msg_ids:
                try:
                    await client.copy_message(chat_id, STORAGE_CHAT_ID, int(mid))
                    await asyncio.sleep(DEFAULT_SEND_DELAY)
                except:
                    pass
            await client.send_message(chat_id, "Delivery finished.")
            return
        # final delivery for non-VIP
        for mid in msg_ids:
            try:
                await client.copy_message(chat_id, STORAGE_CHAT_ID, int(mid))
                await asyncio.sleep(DEFAULT_SEND_DELAY)
            except:
                pass
        await client.send_message(chat_id, "Delivery finished.")

    # extra callback to immediately deliver if user clicks deliver_now
    @app.on_callback_query(filters.regex(r"^deliver_now:"))
    async def deliver_now_cb(client, cq: CallbackQuery):
        movie_id = int(cq.data.split(":",1)[1])
        movie = get_movie_by_id(movie_id)
        if not movie:
            await cq.answer("Movie not found.", show_alert=True)
            return
        await cq.answer("Starting delivery...", show_alert=False)
        await cq.message.delete()
        await deliver_movie(client, cq.from_user.id, movie)
```

```python name=bot.py
# Main entrypoint - wire everything together.

import asyncio
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from db import init_db
from handlers_admin import register_admin_handlers
from handlers_user import register_user_handlers

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise SystemExit("Please set API_ID, API_HASH and BOT_TOKEN in environment or config.py")

# Initialize DB
init_db()

app = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Register handlers
register_admin_handlers(app)
register_user_handlers(app)

if __name__ == "__main__":
    print("Bot started. Press Ctrl+C to stop.")
    app.run()
```

How this implementation maps to your spec
- Storage Group: the bot copies poster and video segments using STORAGE_CHAT_ID message IDs stored in the DB. This means the bot doesn't store video files locally.
- Admin flows: /add_movie, /set_poster, /genlink, /add_vip, /remove_vip, /add_channel, /list_channels implemented for owner only.
- Deep link: token stored in movie.token; /start <token> retrieves movie and enforces flow.
- Force Join: checks configured channels via list_force_channels and get_chat_member; sends Join buttons + Try Again.
- VIP vs Normal: VIP bypasses waiting ads; normal users see waiting ad (latest waiting ad from DB) and get sent video segments after WAIT_AD_SECONDS.
- Poster + caption displayed, with inline menu buttons (you should replace channel links with real ones).
- Message copying: uses copy_message(STORAGE_CHAT_ID, message_id) — this keeps Telegram servers delivering the file, not your server.
- Admin dashboard stub via /dashboard that shows inline options.

Notes and next steps / improvements you might want
- Add proper conversation flows (state machine) for richer admin interactions and file uploads.
- Add pagination, better error handling, logging, and rate-limiting to avoid Telegram limits.
- Add protection for broadcast (confirmation step).
- Protect owner-only commands; I used OWNER_ID check, but consider an admins table.
- Consider storing full channel invite info automatically by asking the bot to export links.
- Consider optimizing copy speed and handling for very large lists (queue worker).

If you want, I can:
- Expand the admin dashboard to be fully interactive (button-driven).
- Convert DB layer to SQLAlchemy for schema migrations.
- Add an admin web dashboard.
- Implement an upload helper that parses ranges automatically from Storage Group forwarded messages (so admin can forward a range and bot auto-detects).
Tell me which next feature to expand and I will provide updated files or a patch.
