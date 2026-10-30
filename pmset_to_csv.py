"""Turn the Mac's own power log (`pmset -g log`) into one row per hour for the Séance Engine.

Usage: python pmset_to_csv.py 2026-10-29T12 [hours=24] > real_night.csv
"""
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd

start = datetime.strptime(sys.argv[1], "%Y-%m-%dT%H")
hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
log = subprocess.run(["pmset", "-g", "log"], capture_output=True, text=True).stdout.splitlines()

rows = {start + timedelta(hours=h): {"events": 0, "wakes": 0, "dark_wakes": 0, "sleeps": 0,
                                     "battery_pct": None, "procs": Counter(), "notes": []}
        for h in range(hours)}
for line in log:
    m = re.match(r"(\d{4}-\d\d-\d\d \d\d):\d\d:\d\d \S+ (\S+)", line)
    if not m:
        continue
    hour = datetime.strptime(m[1], "%Y-%m-%d %H")
    if hour not in rows:
        continue
    r, kind = rows[hour], m[2]
    r["events"] += 1
    r["wakes"] += kind == "Wake"
    r["dark_wakes"] += kind == "DarkWake"
    r["sleeps"] += kind == "Sleep"
    if b := re.search(r"Charge: ?(\d+)", line):
        r["battery_pct"] = int(b[1])
    if p := re.search(r"PID \d+\(([^)]+)\) Created", line):
        r["procs"][p[1]] += 1
    if kind in ("ShutdownCause", "BatteryHealth"):
        r["notes"].append(line.split("\t", 1)[-1].strip())

out = []
for hour, r in rows.items():
    out.append({
        "timestamp": hour.strftime("%Y-%m-%d %H:00:00"),
        "hour": hour.hour,
        "log_events": r["events"],
        "wakes": r["wakes"],
        "dark_wakes": r["dark_wakes"],
        "sleeps": r["sleeps"],
        "battery_pct": r["battery_pct"] if r["battery_pct"] is not None else -1,  # -1 = log silent
        "active_app": r["procs"].most_common(1)[0][0] if r["procs"] else "(silence)",
        "notes": " | ".join(r["notes"]),
    })
pd.DataFrame(out).to_csv(sys.stdout, index=False)
