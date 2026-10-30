---
title: "👻 The Séance Engine: Finding the Ghost in the Data with TabPFN & Gemma"
published: false
tags: devchallenge, hf26challenge, opensource, ai
---

## 🕯️ The idea

What does your computer do while you sleep?

Mine is supposed to do almost nothing. CPU in single digits, a few kilobytes of network, "System Idle" all night long. So when I pictured a ghost living inside a machine, I didn't imagine a skull on the screen. I imagined one row in a boring log file that shouldn't be there.

**The Séance Engine** reads a day of ordinary system logs, asks an open tabular foundation model which moment is the hardest to believe, and then hands that moment to a local LLM. The LLM, playing the Spirit of the Machine, tells us what passed through the circuits in a short *Día de los Muertos* style story.

It finds the ghost in the data, then gives it a voice.

## ⚙️ How it works

Everything runs on my laptop: one Python file, about 100 lines.

**1. The haunted log.** 24 hourly rows of `hour`, `cpu_usage`, `memory_usage` and `network_io_mb`. By day it's VS Code; by night, idle. You can also point it at your own CSV: `python seance_engine.py my_logs.csv`.

**2. The divination ([TabPFN](https://github.com/PriorLabs/TabPFN) by Prior Labs).** TabPFN is a classifier, and an anomaly detector needs a sense of what's "normal". So I used a small density-ratio trick:

- For each row, hold it out.
- Show TabPFN the *other* 23 real rows labelled `real`, next to random noise spread across the same range labelled `noise`.
- Ask: how real does the held-out row look?

Ordinary hours score between 0.66 and 0.99. The witching hour scored this:

```
2026-10-29 02:33:00    8%   4 MB/s   System Idle       p_real 0.992
2026-10-29 03:33:00   98% 850 MB/s   UNKNOWN_PROCESS   p_real 0.006
2026-10-29 04:33:00    7%   5 MB/s   System Idle       p_real 0.992
```

Because `hour` is a feature, TabPFN isn't just flagging "big numbers". It learned that this machine sleeps at 3 AM, so 98% CPU at that hour is what doesn't fit. No training loop, no tuning: TabPFN does all of it in context.

**3. The séance ([Gemma 2 9B](https://ai.google.dev/gemma) through [Ollama](https://ollama.com)).** The anomalous row, including its `p_real` score, goes into a prompt that asks Gemma to speak as a gossipy, theatrical ghost who lives in the laptop's fan (fun, quirky, and chilling by the last line). Output streams to the terminal word by word, which feels a lot like a candle flickering.

**4. The tracing ([Sentry](https://sentry.io)).** The whole investigation is one Sentry trace, with spans for loading the logs, the TabPFN scan and the Gemma chat. Token counts go on the chat span.

![Sentry trace of the séance](https://raw.githubusercontent.com/Prekshabarjatya/seance-engine/main/sentry-trace.jpg)

The trace showed me something I didn't expect: the leave-one-out TabPFN scan (24 small fits on CPU) took **38 seconds**, and Gemma took about a minute. The ghost costs more to find than to listen to.

## 👻 What the machine confessed

> ⚠️ ANOMALY DETECTED at 2026-10-29 03:33:00 (P(real)=0.006)
>
> *Ah, three thirty-three in the morning, that's when the veil thins, darlings! The fan whirred like a disco ball under a mariachi band as 98% of my beloved CPU hummed with the impossible, a process so shrouded, so strange, it registered as "UNKNOWN_PROCESS" on the logs. I saw it all, you see, every pixel flicker as 95% of the memory churned, a ghostly green glow illuminating its form. It downloaded a single video at 850 MB/s, a pixelated rendition of a chihuahua wearing a sombrero, its tiny paws drumming on a maraca. A forgotten relic, perhaps, from a life lived before this one. Now, the screen rests dark, the chihuahua frozen mid-shake, a reminder of that fleeting connection. Is it ever truly gone?*

Every run summons a different visitor. The prompt asks Gemma for a gossipy ghost who lives in the laptop fan: give the ghost a petty hobby and one oddly specific detail, weave in every real number, and end on one quiet line that makes you glance at your own laptop.

## 💡 Why open models

- **The data stays home.** These are behaviour logs from a personal machine. With open weights, TabPFN and Gemma both run locally, and nothing leaves the laptop. It works with Wi-Fi off.
- **I own the voice.** I set the system prompt and the temperature, and I can swap models freely (`MODEL = "gemma2:9b"` is one line).
- **Free to haunt every night.** A ghost should be ambient. Running a local check on last night's logs every morning costs nothing per call.
- **It runs on old hardware.** This was built on an Intel Mac stuck on PyTorch 2.2. The newest TabPFN wouldn't install, but `tabpfn==2.0.9` worked, and that's the point of open weights: you pick a version that fits the machine you actually have.

## 🛠️ Run it yourself

```bash
ollama pull gemma2:9b
pip install -r requirements.txt   # tabpfn==2.0.9, numpy<2, pandas, ollama, sentry-sdk
python seance_engine.py
# optional tracing
SENTRY_DSN="your-dsn" python seance_engine.py
```

## 🔗 Links

- Code: https://github.com/Prekshabarjatya/seance-engine
- TabPFN: https://github.com/PriorLabs/TabPFN
- Gemma: https://ai.google.dev/gemma
- Ollama: https://ollama.com
- Sentry: https://sentry.io

Happy Día de los Muertos. Leave a candle on for your machines tonight. 🕯️
