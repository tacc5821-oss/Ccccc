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
