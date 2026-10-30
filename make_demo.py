"""Build demo.mp4: five slides, each narrated by an ElevenLabs voice. Needs ELEVENLABS_API_KEY in .env."""
import subprocess
import textwrap
from pathlib import Path

import imageio_ffmpeg
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv(".env")  # before importing elevenlabs: it reads ELEVENLABS_API_KEY at import time
from elevenlabs import ElevenLabs, VoiceSettings  # noqa: E402

client = ElevenLabs()

VOICE = "qhH5VOAvpCwvNpmn2srO"
W, H = 1920, 1080
BG, FG, DIM, RED, GOLD = "#0d0b14", "#efe9ff", "#8a80a8", "#ff4d6d", "#ffb347"
OUT = Path("demo_build")
OUT.mkdir(exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

sans = lambda s: ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", s)
mono = lambda s: ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", s)

STORY = ("Ah, three thirty-three in the morning, that's when the veil thins, darlings! The fan whirred like "
         "a disco ball under a mariachi band as 98% of my beloved CPU hummed with the impossible, a process "
         "so strange it registered as UNKNOWN_PROCESS. 95% of the memory churned, a ghostly green glow. "
         "It downloaded a single video at 850 MB/s: a chihuahua in a sombrero, tiny paws drumming on a maraca. "
         "Now the screen rests dark, the chihuahua frozen mid-shake. Is it ever truly gone?")

ROWS = [("01:33", 4, 3, "System Idle", 0.966), ("02:33", 8, 4, "System Idle", 0.992),
        ("03:33", 98, 850, "UNKNOWN_PROCESS", 0.006), ("04:33", 7, 5, "System Idle", 0.992),
        ("05:33", 10, 7, "System Idle", 0.987), ("09:33", 39, 77, "VS Code", 0.791),
        ("14:33", 27, 59, "VS Code", 0.985)]


def canvas():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def title():
    img, d = canvas()
    d.text((W / 2, 420), "What does your computer do", font=sans(84), fill=FG, anchor="mm")
    d.text((W / 2, 520), "while you sleep?", font=sans(84), fill=GOLD, anchor="mm")
    d.text((W / 2, 680), "The Séance Engine", font=sans(44), fill=DIM, anchor="mm")
    return img


def table():
    img, d = canvas()
    d.text((120, 110), "TabPFN scores every hour: how real does it look?", font=sans(54), fill=FG)
    d.text((120, 190), "synthetic logs · one haunting planted · TabPFN is not told which", font=sans(32), fill=DIM)
    y = 300
    d.text((120, y), f"{'time':<7}{'cpu%':>6}{'MB/s':>7}  {'process':<17}{'p_real':>7}", font=mono(42), fill=DIM)
    for t, cpu, net, app, p in ROWS:
        y += 80
        ghost = p < 0.1
        if ghost:
            d.rectangle((100, y - 12, W - 100, y + 62), fill="#3a0d1a")
        d.text((120, y), f"{t:<7}{cpu:>6}{net:>7}  {app:<17}{p:>7.3f}", font=mono(42), fill=RED if ghost else FG)
    d.text((120, 960), "ANOMALY DETECTED at 03:33   P(real) = 0.006", font=sans(44), fill=RED)
    return img


def story():
    img, d = canvas()
    d.text((120, 100), "The machine's confession  ·  Gemma 2 9B, running locally", font=sans(46), fill=GOLD)
    d.multiline_text((120, 210), "\n".join(textwrap.wrap(STORY, 62)), font=sans(44), fill=FG, spacing=18)
    return img


def sentry():
    img, d = canvas()
    shot = Image.open("sentry-trace.jpg")
    shot.thumbnail((1200, 900))
    img.paste(shot, ((W - shot.width) // 2, 150))
    d.text((W / 2, 80), "Traced end to end with Sentry · runs 100% locally", font=sans(46), fill=FG, anchor="mm")
    return img


def outro():
    img, d = canvas()
    d.text((W / 2, 400), "The Séance Engine", font=sans(90), fill=FG, anchor="mm")
    d.text((W / 2, 520), "TabPFN finds the ghost · Gemma gives it a voice", font=sans(48), fill=GOLD, anchor="mm")
    d.text((W / 2, 680), "github.com/Prekshabarjatya/seance-engine", font=mono(40), fill=DIM, anchor="mm")
    return img


# Narration uses Eleven v4 audio tags ([whispers] etc.); the slide text stays clean.
SLIDES = [
    (title, "[whispers] What does your computer do... while you sleep? [normal] Mine is supposed to do "
            "nothing. [mischievously] So I held a séance."),
    (table, "Twenty-four hours of system logs, with one haunting planted somewhere. TabPFN, an open tabular "
            "foundation model, scores how believable each hour is. Ordinary. Ordinary. Ordinary... "
            "[pause] [whispers] except three thirty-three A.M. Zero point zero zero six."),
    (story, "[theatrical] " + STORY.replace("Is it ever truly gone?", "[whispers] Is it ever... truly gone?")),
    (sentry, "Everything runs locally. TabPFN and Gemma on my own laptop, traced end to end with Sentry."),
    (outro, "The Séance Engine. [whispers] Leave a candle on for your machines tonight."),
]


def speak(text, path):
    if path.exists() and path.stat().st_size:
        return
    audio = client.text_to_speech.convert(text=text, voice_id=VOICE, model_id="eleven_v4",
                                          output_format="mp3_44100_128",
                                          voice_settings=VoiceSettings(stability=0.4, similarity_boost=0.75))
    path.write_bytes(b"".join(audio))  # only written once the whole clip arrived


parts = []
for i, (draw, line) in enumerate(SLIDES):
    png, mp3, mp4 = OUT / f"{i}.png", OUT / f"{i}.mp3", OUT / f"{i}.mp4"
    draw().save(png)
    speak(line, mp3)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", mp3,
                    "-af", "apad=pad_dur=0.8", "-shortest", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-ar", "44100", mp4], check=True)
    parts.append(f"file '{mp4.name}'")
(OUT / "list.txt").write_text("\n".join(parts))
subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-i", OUT / "list.txt", "-c", "copy",
                "demo.mp4"], check=True)
print("demo.mp4 ready")
