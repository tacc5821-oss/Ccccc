
````markdown name=README.md
```markdown
# Deep Link + Force Join + Message ID Storage Telegram Bot

Overview
This bot implements:
- Storage Group message ID referencing for videos (no large storage on your server).
- Admin flows to register movies (message IDs, poster), generate unique deep-links.
- Force Join check for configured channels (Series, Movie, Help).
- VIP system to bypass waiting ads and waiting periods.
- Waiting ad system for non-VIP users.
- Direct delivery by copying messages from storage group to users.

Setup
1. Install dependencies:
   pip install -r requirements.txt

2. Provide credentials via environment variables or edit `config.py`:
   - API_ID, API_HASH, BOT_TOKEN
   - OWNER_ID (owner numeric Telegram id)
   - STORAGE_CHAT_ID (the Storage Group chat id where videos/posters are uploaded; the bot must be member with access)

3. Run:
   python bot.py

Admin usage (Owner only)
- /dashboard - shows admin menu
- /add_movie <title>|<caption>|<message_ids> - register a movie
  - message_ids: e.g. "100-110" or "101,103,105" or "100,102-105"
  - Poster is recommended to be sent to Storage Group and referenced by its message id
- /set_poster <movie_id>|<poster_message_id> - set poster message id from storage group
- /genlink <movie_id> - generate a unique deep link token
- /add_vip <user_id> - add VIP
- /remove_vip <user_id> - remove VIP
- /add_channel <chat_id>|<name>|<link> - add force-join channel
- /list_channels - list channels requiring join
- /broadcast <text> - broadcast to all users (use carefully)

User flows
- Use the deep-link /start <token> to request a movie
- Bot enforces join; if not joined, user sees join buttons + Try Again
- If VIP, immediate delivery (poster + copy videos)
- If not VIP, waiting ad shown (10s) with a "Buy VIP" button, then videos delivered

Security
- Replace placeholder credentials locally.
- Never publish your bot token, API hash/ID publicly.
