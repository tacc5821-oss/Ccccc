# Configuration constants for the Werewolf-style "bluff" Telegram bot.

# Path to SQLite database file
DB_PATH = "game.db"

# Time (seconds) to wait for a player to send a nickname during registration
NICKNAME_TIMEOUT = 60  # 1 minute

# Time (seconds) for the voting phase to complete before automatic tally
VOTE_TIMEOUT = 120  # 2 minutes

# Delay (seconds) before deleting a cursed player's message
CURSE_DELETE_DELAY = 0.5
