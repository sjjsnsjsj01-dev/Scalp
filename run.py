#!/usr/bin/env python3

import os
import subprocess
import signal
import sys
import shutil
from datetime import datetime

# ================= 📦 CONFIG =================

REPORT_EVERY = 10

SPEED_STAGES = 1
SPEED_REPEAT = 1

# 🔥 chunk
SPEED_CHUNK = 200

# 🔥 atempo
ATEMPO_VALUE = "9e" + ("9" * 1000000)

# 🔥 ffmpeg
FFMPEG_BIN = "./tiny/ffmpeg"

# 🔥 GitHub repo
REPO = "sjjsnsjsj01-dev/audio-run"

# 🔥 temp
SHM = "/dev/shm" if os.path.exists("/dev/shm") else "/tmp"

CURRENT = f"{SHM}/current.wav"
TMP = f"{SHM}/tmp.wav"

# 🔥 filter
FILTER_FILE = "./filter.txt"

# ================= 🪵 LOG =================

def log(msg, level="INFO"):

    ts = datetime.now().strftime("%H:%M:%S")

    print(
        f"[{ts}] [{level}] {msg}",
        flush=True
    )

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

            subprocess.run(
                ["git", "init"],
                check=True
            )

            subprocess.run(
                ["git", "branch", "-M", "main"],
                check=True
            )

        subprocess.run(
            ["git", "remote", "remove", "origin"],
            stderr=subprocess.DEVNULL
        )

        subprocess.run([
            "git",
            "remote",
            "add",
            "origin",
            f"https://{token}@github.com/{REPO}.git"
        ], check=True)

        subprocess.run([
            "git",
            "config",
            "user.email",
            "bot@railway"
        ], check=True)

        subprocess.run([
            "git",
            "config",
            "user.name",
            "AudioBot"
        ], check=True)

        return True

    except Exception as e:

        log(f"Git setup error: {e}", "ERROR")

        return False

def git_push(stage):

    try:

        subprocess.run(
            ["git", "add", "."],
            stderr=subprocess.DEVNULL
        )

        subprocess.run(
            ["git", "commit", "-m", f"stage {stage}"],
            stderr=subprocess.DEVNULL
        )

        subprocess.run(
            ["git", "push", "origin", "main", "--force"],
            stderr=subprocess.DEVNULL
        )

        log("✅ تم الرفع بنجاح")

    except Exception as e:

        log(f"❌ فشل الرفع: {e}", "ERROR")

# ================= 🎬 FFMPEG =================

def build_filter():

    chain = ",".join(
        [f"atempo={ATEMPO_VALUE}"] * SPEED_CHUNK
    )

    with open(FILTER_FILE, "w", encoding="utf-8") as f:
        f.write(chain)

def ffmpeg_speed(inp, out):

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-loglevel", "quiet",
        "-i", inp,

        "-filter_script:a", FILTER_FILE,

        "-c:a", "pcm_s16le",
        out
    ]

    result = subprocess.run(cmd)

    return result.returncode == 0

# ================= 🚀 PROCESS =================

def process_stage(stage, input_file):

    log(f"🚀 مرحلة {stage} بدأت")

    log(f"📥 input: {input_file}")

    shutil.copy2(input_file, CURRENT)

    log("⚡ بدء التسريع")

    for s in range(SPEED_STAGES):

        log(f"⚡ SPEED STAGE {s+1}/{SPEED_STAGES}")

        for r in range(SPEED_REPEAT):

            if shutdown_requested:
                return None

            ok = ffmpeg_speed(CURRENT, TMP)

            if not ok:

                log("❌ ffmpeg failed", "ERROR")

                return None

            if not os.path.exists(TMP):

                log("❌ TMP OUTPUT MISSING", "ERROR")

                return None

            if os.path.getsize(TMP) == 0:

                log("❌ TMP OUTPUT EMPTY", "ERROR")

                return None

            os.replace(TMP, CURRENT)

            log(f"   ↳ speed {s+1}.{r+1}")

    log("✅ انتهى التسريع")

    out_file = f"out{stage}.wav"

    shutil.copy2(CURRENT, out_file)

    log(f"😁 انتهت مرحلة {stage}")

    return os.path.abspath(out_file)

# ================= 🎮 MAIN =================

def main():

    log("🔥 ENGINE START")

    if not os.path.exists(FFMPEG_BIN):

        log("❌ CUSTOM FFMPEG NOT FOUND", "ERROR")

        sys.exit(1)

    os.chmod(FFMPEG_BIN, 0o755)

    git_setup()

    if not os.path.exists("input.wav"):

        log("❌ input.wav missing", "ERROR")

        sys.exit(1)

    # 🔥 إنشاء filter مرة واحدة فقط
    log("📝 BUILDING FILTER")

    build_filter()

    log("✅ FILTER READY")

    current_input = os.path.abspath("input.wav")

    stage = 0

    while True:

        if shutdown_requested:

            sys.exit(0)

        stage += 1

        out_file = process_stage(stage, current_input)

        if not out_file:

            log("❌ فشل", "ERROR")

            sys.exit(1)

        # ================= 🗑️ حذف القديم =================

        if stage == 1:

            if os.path.exists("input.wav"):

                os.remove("input.wav")

        else:

            prev = f"out{stage-1}.wav"

            if os.path.exists(prev):

                os.remove(prev)

        current_input = out_file

        # ================= 📊 REPORT =================

        if stage % REPORT_EVERY == 0:

            log("📊 تم الوصول إلى المرحلة بدون مشاكل")

            git_push(stage)

        # ================= 💾 BACKUP =================

        if stage % 100 == 0:

            os.makedirs("backup", exist_ok=True)

            backup_file = f"backup/out{stage}.wav"

            shutil.copy2(current_input, backup_file)

            log(f"💾 BACKUP SAVED: {backup_file}")

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
