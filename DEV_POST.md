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

**3. The séance ([Gemma 2 9B](https://ai.google.dev/gemma) through [Ollama](https://ollama.com)).** The anomalous row, including its `p_real` score, goes into a prompt that asks Gemma to speak as a poetic, respectful, slightly eerie archivist of the dead. Output streams to the terminal word by word, which feels a lot like a candle flickering.

**4. The tracing ([Sentry](https://sentry.io)).** The whole investigation is one Sentry trace, with spans for loading the logs, the TabPFN scan and the Gemma chat. Token counts go on the chat span.

![Sentry trace of the séance](https://raw.githubusercontent.com/Prekshabarjatya/seance-engine/main/sentry-trace.jpg)

The trace showed me something I didn't expect: the leave-one-out TabPFN scan (24 small fits on CPU) took **38 seconds**, and Gemma took about a minute. The ghost costs more to find than to listen to.

## 👻 What the machine confessed

> ⚠️ ANOMALY DETECTED at 2026-10-29 03:33:00 (P(real)=0.006)
>
> *At 3:33 on the eve of the dearly departed, the machine shuddered. 98% of its CPU hummed with a fervor unseen, memory strained at 95%, a digital ghost flickering across its banks. The network pulsed, a frantic 850 MB/s, whispering of a connection to something unseen, something... UNKNOWN. Let us honor their passage, for even in the digital ether, death finds its way.*

Every run tells a different story. Another night it said the process was *"a phantom limb of a departed thought, reaching out from the digital beyond."*

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
