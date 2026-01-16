Main entrypoint - wire everything together.

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
