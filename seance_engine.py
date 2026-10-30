"""The Séance Engine: TabPFN finds the ghost in the logs, Gemma gives it a voice."""
import os
import sys
import numpy as np
import pandas as pd
import ollama
import sentry_sdk
from datetime import datetime, timedelta
from tabpfn import TabPFNClassifier

# No SENTRY_DSN set -> Sentry stays a silent no-op.
sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN"), traces_sample_rate=1.0)

MODEL = "gemma2:9b"
rng = np.random.default_rng(31)


def generate_ghost_logs(path="ghost_logs.csv"):
    """24 hourly rows; the user works by day, sleeps by night. One row is haunted."""
    start = datetime.now().replace(minute=33, second=0, microsecond=0) - timedelta(hours=23)
    rows = []
    for i in range(24):
        dt = start + timedelta(hours=i)
        awake = 9 <= dt.hour <= 22
        row = {
            "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "hour": dt.hour,
            "cpu_usage": int(rng.integers(20, 40) if awake else rng.integers(3, 12)),
            "memory_usage": int(rng.integers(40, 60) if awake else rng.integers(25, 35)),
            "network_io_mb": int(rng.integers(20, 120) if awake else rng.integers(0, 8)),
            "active_app": "VS Code" if awake else "System Idle",
        }
        if dt.hour == 3:  # the witching hour
            row.update(cpu_usage=98, memory_usage=95, network_io_mb=850, active_app="UNKNOWN_PROCESS")
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def find_the_ghost(df):
    """Leave-one-out density-ratio scoring with TabPFN.

    For each row, TabPFN sees the other real rows (label 1) next to uniform noise
    spanning the data's range (label 0), then says how 'real' the held-out row looks.
    The row it believes least is the ghost.
    """
    X = df.select_dtypes("number").to_numpy(float)  # every numeric column is evidence
    lo, hi = X.min(0), X.max(0)
    noise = rng.uniform(lo, hi, size=(len(X) * 2, X.shape[1]))
    scores = np.empty(len(X))
    for i in range(len(X)):
        rest = np.delete(X, i, axis=0)
        clf = TabPFNClassifier(device="cpu")
        clf.fit(np.vstack([rest, noise]), np.r_[np.ones(len(rest)), np.zeros(len(noise))])
        scores[i] = clf.predict_proba(X[i : i + 1])[0, 1]  # P(real)
    df = df.assign(p_real=scores.round(3))
    return df.loc[df.p_real.idxmin()], df


def conduct_seance(row):
    evidence = "\n".join(f"- {k}: {v}" for k, v in row.items() if str(v) not in ("", "nan"))
    prompt = f"""You are the Spirit of the Machine: a gossipy, theatrical ghost who lives in the
laptop's fan and narrates its secrets like a campfire storyteller who has had too much marigold tea.
It is Día de los Muertos. While the user slept, you noticed this in the logs:

{evidence}
(p_real = how believable this hour is: 0 impossible, 1 ordinary. battery_pct -1 = the log fell silent.)

Tell a 4-6 sentence story of who (or what) visited the machine at that moment.
- Make it FUN and QUIRKY: give the ghost a name, a petty hobby and an oddly specific detail
  (e.g. it was re-downloading a cat video from 2009, alphabetising the user's tabs).
- Make it CHILLING: end on one quiet line that makes the reader glance at their own laptop.
- Weave in every real number and process name as story details, not a report.
- Warm towards the dead, never gory. Never break character. No headings, no lists."""
    print(f"🕯️  Lighting the candles. Channeling {MODEL}...\n")
    with sentry_sdk.start_span(op="gen_ai.chat", name=f"séance with {MODEL}") as span:
        span.set_data("gen_ai.request.model", MODEL)
        span.set_data("ghost.timestamp", row["timestamp"])
        for chunk in ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}], stream=True,
                                 options={"temperature": 0.9}):
            print(chunk["message"]["content"], end="", flush=True)
            if chunk.get("done"):
                span.set_data("gen_ai.usage.input_tokens", chunk.get("prompt_eval_count"))
                span.set_data("gen_ai.usage.output_tokens", chunk.get("eval_count"))
    print()


if __name__ == "__main__":
    with sentry_sdk.start_transaction(op="agent", name="séance-engine investigation"):
        with sentry_sdk.start_span(op="data.load", name="read the logs"):
            df = pd.read_csv(sys.argv[1]) if len(sys.argv) > 1 else generate_ghost_logs()
        print(f"👻 {len(df)} rows of mundane logs loaded.")
        print("🔮 Consulting TabPFN...")
        with sentry_sdk.start_span(op="ml.inference", name="TabPFN anomaly scan") as span:
            ghost, scored = find_the_ghost(df)
            span.set_data("rows", len(df))
            span.set_data("ghost.p_real", float(ghost["p_real"]))
        print(scored.drop(columns="notes", errors="ignore").to_string(index=False))
        print(f"\n⚠️  ANOMALY DETECTED at {ghost['timestamp']} (P(real)={ghost['p_real']})\n")
        print("=" * 50 + "\nTHE MACHINE'S CONFESSION:\n" + "=" * 50)
        conduct_seance(ghost)
        print("=" * 50)
    sentry_sdk.flush()
