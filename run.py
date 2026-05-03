#!/usr/bin/env python3
import os
import json
import subprocess
import signal
import sys
import shutil
from datetime import datetime

# ================= 📦 CONFIG =================
REPORT_EVERY = 10

SPEED_STAGES = 4
SPEED_REPEAT = 4
SPEED_CHUNK = 8000

MERGE_STAGES = 1
MERGE_DEPTH = 130000

REPO = "sjjsnsjsj01-dev/audio-run"
BACKUP_DIR = "backup"
PROGRESS_FILE = "progress.json"

SHM = "/dev/shm" if os.path.exists("/dev/shm") else "/tmp"
CURRENT = f"{SHM}/current.wav"
TMP = f"{SHM}/tmp.wav"

os.makedirs(BACKUP_DIR, exist_ok=True)

# ================= 🪵 LOG =================
def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

# ================= 🛡️ SIGNAL =================
shutdown_requested = False
def handle_signal(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    log("⚠️ Shutdown requested", "WARN")

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# ================= 🌐 GIT =================
def git_setup():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        log("⚠️ No GITHUB_TOKEN", "WARN")
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
    except Exception as e:
        log(f"Git setup error: {e}", "ERROR")
        return False

def git_push(stage):
    try:
        subprocess.run(["git","add","."],stderr=subprocess.DEVNULL)
        subprocess.run(["git","commit","-m",f"stage {stage}"],stderr=subprocess.DEVNULL)
        subprocess.run(["git","push","origin","main","--force"],stderr=subprocess.DEVNULL)
        log("تم بنجاح")
    except:
        log("⚠️ فشل الرفع", "WARN")

# ================= 📊 PROGRESS =================
def save_progress(stage, file):
    with open(PROGRESS_FILE,"w") as f:
        json.dump({"stage":stage,"file":file},f)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                d=json.load(f)
                return d["stage"], d["file"]
        except:
            pass
    return 0, None

# ================= 🎬 FFMPEG =================
def ffmpeg_speed(inp, out):
    chain = ",".join(["atempo=2"]*SPEED_CHUNK)
    cmd = [
        "ffmpeg","-y","-loglevel","quiet",
        "-i",inp,
        "-filter:a",chain,
        "-c:a","pcm_s16le",
        out
    ]
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
def process_stage(stage_index, input_file):

    shutil.copy2(input_file, CURRENT)

    # ⚡ SPEED
    log(f"مرحلة {stage_index} بدأ التسريع")

    for s in range(SPEED_STAGES):
        for r in range(SPEED_REPEAT):

            if shutdown_requested:
                return None

            if not ffmpeg_speed(CURRENT, TMP):
                return None

            os.replace(TMP, CURRENT)

    # 🔗 MERGE
    log("بدأ الدمج")

    for s in range(MERGE_STAGES):
        for d in range(MERGE_DEPTH):

            if shutdown_requested:
                return None

            if not ffmpeg_merge(CURRENT, TMP):
                return None

            os.replace(TMP, CURRENT)

    # 💾 SAVE
    out_file = f"out{stage_index}.wav"
    shutil.copy2(CURRENT, out_file)

    log("😁")

    return out_file

# ================= 🎮 MAIN =================
def main():
    log("🔥 ENGINE START")

    git_setup()

    stage, resume_file = load_progress()

    if not resume_file or not os.path.exists(resume_file):
        if not os.path.exists("input.wav"):
            log("❌ input.wav missing","ERROR")
            sys.exit(1)

        current_input = os.path.abspath("input.wav")
        stage = 0
        log("بدأ من input.wav")
    else:
        current_input = resume_file
        log(f"استكمال من المرحلة {stage}")

    while True:

        if shutdown_requested:
            save_progress(stage, current_input)
            sys.exit(0)

        stage += 1

        out_file = process_stage(stage, current_input)

        if not out_file or not os.path.exists(out_file):
            log("❌ فشل", "ERROR")
            save_progress(stage-1, current_input)
            sys.exit(1)

        # حذف القديم
        if stage == 1 and os.path.exists("input.wav"):
            os.remove("input.wav")

        prev = f"out{stage-1}.wav"
        if os.path.exists(prev):
            os.remove(prev)

        current_input = os.path.abspath(out_file)
        save_progress(stage, current_input)

        # 📊 كل 10 مراحل
        if stage % REPORT_EVERY == 0:
            log("تم الوصول إلى المرحلة بدون مشاكل")
            git_push(stage)

# ================= ENTRY =================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        log(f"💥 {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
