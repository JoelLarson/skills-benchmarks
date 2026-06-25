#!/usr/bin/env python3
"""Read a Codex run log on stdin; print how many seconds to sleep before retrying
after a usage-limit block. Parses "try again at H:MM AM/PM" (Codex's message) and
returns the seconds until that local time (+2 min buffer); falls back to argv[1]
(default 1800) when no time is found.

Runs on the user's machine, so datetime.now() reflects their local clock.
"""
import datetime
import re
import sys

fallback = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
text = sys.stdin.read()

m = re.search(r"try again at\s+(\d{1,2}:\d{2}\s*(?:[AaPp][Mm])?)", text)
if m:
    raw = m.group(1).strip().upper().replace(" ", "")
    for fmt in ("%I:%M%p", "%H:%M"):
        try:
            t = datetime.datetime.strptime(raw, fmt)
        except ValueError:
            continue
        now = datetime.datetime.now()
        target = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        secs = int((target - now).total_seconds()) + 120
        print(max(60, secs))
        sys.exit(0)

print(fallback)
