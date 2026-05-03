#!/usr/bin/env python3
import os
import json
import subprocess
import signal
import sys
import shutil
from datetime import datetime

# ================= 📦 CONFIG =================
RUNS = 999999999999999999
REPORT_EVERY = 10

# ⚡ SPEED (نفس كودك)
SPEED_STAGES = 8
SPEED_REPEAT = 5
SPEED_CHUNK = 4000

# 🔗 MERGE (🔥 تم التعديل الصحيح)
MERGE_STAGES = 2
MERGE_DEPTH = 10   # 👈 بدل REPEAT (يعني 2^10 لكل stage)

# 🌐 Git
REPO = "sjjsnsjsj01-dev/audio-run"
BACKUP_DIR = "backup"
PROGRESS_FILE = "progress.json"

# RAM
SHM = "/dev/shm" if os.path.exists("/dev/shm") else "/tmp"
INPUT = f"{SHM}/input.wav"
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

        subprocess.run(["git","add","."],stderr=subprocess.DEVNULL)
        subprocess.run(["git","commit","-m","init"],stderr=subprocess.DEVNULL)
        subprocess.run(["git","push","-u","origin","main","--force"],stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        log(f"Git setup error: {e}", "ERROR")
        return False

def git_push(stage):
    try:
        subprocess.run(["git","add","."],stderr=subprocess.DEVNULL)
        subprocess.run(["git","commit","-m",f"stage {stage}"],stderr=subprocess.DEVNULL)
        subprocess.run(["git","push","origin","main","--force"],stderr=subprocess.DEVNULL)
        log(f"🚀 pushed stage {stage}")
    except:
        pass

# ================= 📊 PROGRESS =================
def save_progress(run, file):
    with open(PROGRESS_FILE,"w") as f:
        json.dump({"run":run,"file":file},f)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                d=json.load(f)
                return d["run"], d["file"]
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

# ================= 🚀 CORE ENGINE =================
def run_full_process(run_index, input_file):

    shutil.copy2(input_file, CURRENT)

    speed_ok = True
    merge_ok = True

    # =========================
    # ⚡ SPEED
    # =========================
    for s in range(SPEED_STAGES):
        for r in range(SPEED_REPEAT):
            if not ffmpeg_speed(CURRENT, TMP):
                speed_ok = False
                break
            os.replace(TMP, CURRENT)
        if not speed_ok:
            break

    # =========================
    # 🔗 MERGE (🔥 DOUBLE EXPONENTIAL)
    # =========================
    for s in range(MERGE_STAGES):

        for d in range(MERGE_DEPTH):

            if not ffmpeg_merge(CURRENT, TMP):
                merge_ok = False
                break

            os.replace(TMP, CURRENT)

        if not merge_ok:
            break

    # =========================
    # 💾 SAVE
    # =========================
    out_file = f"out_{run_index}.wav"
    shutil.copy2(CURRENT, out_file)

    return out_file, speed_ok, merge_ok

# ================= 🎮 MAIN =================
def main():
    log("🔥 START ENGINE")

    git_setup()

    run_index, resume_file = load_progress()

    if not resume_file or not os.path.exists(resume_file):
        if not os.path.exists("input.wav"):
            log("❌ input.wav missing","ERROR")
            sys.exit(1)
        current_input = os.path.abspath("input.wav")
        run_index = 0
        log("🆕 starting from input.wav")
    else:
        current_input = resume_file
        log(f"🔄 resume from run {run_index}")

    while True:

        if shutdown_requested:
            save_progress(run_index, current_input)
            sys.exit(0)

        run_index += 1

        out_file, speed_ok, merge_ok = run_full_process(run_index, current_input)

        if not os.path.exists(out_file):
            log("❌ failed", "ERROR")
            save_progress(run_index-1, current_input)
            sys.exit(1)

        # حذف input أول مرة
        if run_index == 1 and os.path.exists("input.wav"):
            os.remove("input.wav")

        # حذف السابق دائماً
        prev = f"out_{run_index-1}.wav"
        if os.path.exists(prev):
            os.remove(prev)

        current_input = os.path.abspath(out_file)
        save_progress(run_index, current_input)

        # =========================
        # 📊 REPORT + PUSH
        # =========================
        if run_index % REPORT_EVERY == 0:

            s = "✔️ SPEED OK" if speed_ok else "❌ SPEED FAIL"
            m = "✔️ MERGE OK" if merge_ok else "❌ MERGE FAIL"

            size = os.path.getsize(out_file)/(1024**2)

            log(f"RUN {run_index}")
            log(f"{s} | {m}")
            log(f"📦 size: {size:.2f} MB")

            git_push(run_index)

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