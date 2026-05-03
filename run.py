#!/usr/bin/env python3
import os
import subprocess
import signal
import sys
import shutil
from datetime import datetime

# ================= 📦 CONFIG =================
MAX_STAGES = 999999999999999999
PUSH_EVERY = 10

SPEED_STAGES = 4
SPEED_REPEAT = 4
SPEED_CHUNK = 8000

MERGE_STAGES = 1
MERGE_DEPTH = 13000   # 👈 مهم (ليس 130000)

REPO = "sjjsnsjsj01-dev/audio-run"

SHM = "/dev/shm" if os.path.exists("/dev/shm") else "/tmp"
CURRENT = f"{SHM}/current.wav"
TMP = f"{SHM}/tmp.wav"

# ================= 🪵 LOG =================
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ================= 🛡️ SIGNAL =================
shutdown_requested = False
def handle_signal(signum, frame):
    global shutdown_requested
    shutdown_requested = True

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# ================= 🌐 GIT =================
def git_setup():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return False
    try:
        if not os.path.exists(".git"):
            subprocess.run(["git","init"],check=True)
            subprocess.run(["git","branch","-M","main"],check=True)

        subprocess.run(["git","remote","remove","origin"],stderr=subprocess.DEVNULL)

        subprocess.run([
            "git","remote","add","origin",
            f"https://{token}@github.com/{REPO}.git"
        ],check=True)

        subprocess.run(["git","config","user.email","bot@railway"],check=True)
        subprocess.run(["git","config","user.name","AudioBot"],check=True)

        return True
    except:
        return False

def git_push(stage):
    try:
        subprocess.run(["git","add","."],stderr=subprocess.DEVNULL)
        subprocess.run(["git","commit","-m",f"stage {stage}"],stderr=subprocess.DEVNULL)
        subprocess.run(["git","push","origin","main","--force"],stderr=subprocess.DEVNULL)
        log("تم بنجاح")
    except:
        log("فشل الرفع")

# ================= 🎬 FFMPEG =================
def ffmpeg_speed(inp, out):
    chain = ",".join(["atempo=2"]*SPEED_CHUNK)
    cmd = ["ffmpeg","-y","-loglevel","quiet","-i",inp,"-filter:a",chain,"-c:a","pcm_s16le",out]
    return subprocess.run(cmd).returncode==0

def ffmpeg_merge(inp, out):
    cmd = [
        "ffmpeg","-y","-loglevel","quiet",
        "-i",inp,"-i",inp,
        "-filter_complex","[0:a][1:a]concat=n=2:v=0:a=1[out]",
        "-map","[out]",
        "-c:a","pcm_s16le",
        out
    ]
    return subprocess.run(cmd).returncode==0

# ================= 🚀 PROCESS =================
def process_stage(stage, input_file):

    log(f"مرحلة {stage} بدأت")

    shutil.copy2(input_file, CURRENT)

    # ⚡ SPEED
    log("بدأ التسريع")
    for _ in range(SPEED_STAGES):
        for _ in range(SPEED_REPEAT):
            if not ffmpeg_speed(CURRENT, TMP):
                return None
            os.replace(TMP, CURRENT)

    # 🔗 MERGE
    log("بدأ الدمج")
    for _ in range(MERGE_STAGES):
        for _ in range(MERGE_DEPTH):
            if not ffmpeg_merge(CURRENT, TMP):
                return None
            os.replace(TMP, CURRENT)

    # 💾 SAVE
    out_file = f"out{stage}.wav"
    shutil.copy2(CURRENT, out_file)

    log("😁 انتهت المرحلة")

    return out_file

# ================= 🎮 MAIN =================
def main():
    log("🚀 تشغيل")

    git_setup()

    if not os.path.exists("input.wav"):
        log("❌ input.wav غير موجود")
        sys.exit(1)

    current_input = os.path.abspath("input.wav")

    stage = 1

    while stage <= MAX_STAGES:

        if shutdown_requested:
            sys.exit(0)

        out_file = process_stage(stage, current_input)

        if not out_file or not os.path.exists(out_file):
            log("❌ فشل")
            sys.exit(1)

        # حذف السابق
        if stage == 1:
            if os.path.exists("input.wav"):
                os.remove("input.wav")
        else:
            prev = f"out{stage-1}.wav"
            if os.path.exists(prev):
                os.remove(prev)

        current_input = os.path.abspath(out_file)

        # 🚀 رفع كل 10 مراحل
        if stage % PUSH_EVERY == 0:
            git_push(stage)

        stage += 1

# ================= ENTRY =================
if __name__ == "__main__":
    main()
