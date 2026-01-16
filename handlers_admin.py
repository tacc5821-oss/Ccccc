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
