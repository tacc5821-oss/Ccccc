Utility helpers: parse message id ranges, generate tokens, admin check, format.

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
