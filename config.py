# Configuration for the bluff game bot.
import os

# SQLite DB path; override with environment variable (use persistent mount in Koyeb, e.g., /data/game.db)
DB_PATH = os.getenv("DB_PATH", "game.db")

# timeout settings (seconds)
NICKNAME_TIMEOUT = int(os.getenv("NICKNAME_TIMEOUT", "60"))  # 1 minute
VOTE_TIMEOUT = int(os.getenv("VOTE_TIMEOUT", "120"))  # 2 minutes

# delay before deleting cursed player's message (seconds)
CURSE_DELETE_DELAY = float(os.getenv("CURSE_DELETE_DELAY", "0.5"))

# Webhook config: if WEBHOOK_BASE_URL is set, the bot will attempt to set a webhook at that URL.
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")  # e.g., https://<app>.koyeb.app
WEBHOOK_PORT = int(os.getenv("PORT", "8443"))  # port used for webhook listener (Koyeb sets PORT)
