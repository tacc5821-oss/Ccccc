User-facing handlers: /start deep link, force-join check, try again, delivery pipeline.

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
