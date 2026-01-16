Lightweight models / helpers for in-memory use (optional).
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
