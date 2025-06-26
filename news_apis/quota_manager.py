# news_apis/quota_manager.py

import json
import os
from datetime import datetime, timedelta
import threading
import pytz  # pip install pytz

# Path for persistent quota tracking
QUOTA_STATE_FILE = "quota_state.json"
TOKYO_TZ = pytz.timezone("Asia/Tokyo")
FETCHER_KEYS = ["google_cse", "gnews", "brave_news"]

DEFAULT_QUOTA = {
    "google_cse": 100,
    "gnews": 100,
    "brave_news": 67
}

class NewsQuotaManager:
    def __init__(self, state_file=QUOTA_STATE_FILE):
        self.state_file = state_file
        self.lock = threading.Lock()
        self._init_file()

    def _init_file(self):
        """Create the quota file if missing or incomplete."""
        if not os.path.exists(self.state_file):
            self._write_state(self._default_state())
        else:
            state = self._read_state()
            changed = False
            for k in FETCHER_KEYS:
                if k not in state:
                    state[k] = self._default_entry(k)
                    changed = True
            if changed:
                self._write_state(state)

    def _default_entry(self, key):
        return {
            "queries_today": 0,
            "last_reset": None
        }

    def _default_state(self):
        return {k: self._default_entry(k) for k in FETCHER_KEYS}

    def _read_state(self):
        with self.lock:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)

    def _write_state(self, state):
        with self.lock:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

    def _now_jst(self):
        return datetime.now(TOKYO_TZ)

    def _quota_day(self, dt):
        # All times >= 9:00 JST are "today"; < 9:00 are "yesterday"
        nine_am = dt.replace(hour=9, minute=0, second=0, microsecond=0)
        if dt < nine_am:
            return (dt - timedelta(days=1)).date()
        return dt.date()

    def get_remaining_quota(self, key):
        state = self._read_state()
        now = self._now_jst()
        entry = state.get(key, self._default_entry(key))
        last_reset = entry.get("last_reset")
        # Reset logic
        if not last_reset or self._quota_day(now) != self._quota_day(self._parse_iso(last_reset)):
            # Reset counter for new quota day
            entry["queries_today"] = 0
            entry["last_reset"] = now.isoformat()
            state[key] = entry
            self._write_state(state)
        return max(0, DEFAULT_QUOTA[key] - entry["queries_today"])

    def log_query(self, key):
        state = self._read_state()
        now = self._now_jst()
        entry = state.get(key, self._default_entry(key))
        # Reset if new day
        if not entry["last_reset"] or self._quota_day(now) != self._quota_day(self._parse_iso(entry["last_reset"])):
            entry["queries_today"] = 0
            entry["last_reset"] = now.isoformat()
        entry["queries_today"] += 1
        state[key] = entry
        self._write_state(state)

    def _parse_iso(self, s):
        return datetime.fromisoformat(s).astimezone(TOKYO_TZ)

    def reset_all(self):
        """Force reset for all fetchers (e.g., admin use)."""
        now = self._now_jst().isoformat()
        state = self._read_state()
        for k in FETCHER_KEYS:
            state[k] = {"queries_today": 0, "last_reset": now}
        self._write_state(state)
