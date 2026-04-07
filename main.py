import os
import subprocess
import sys

REPO = "https://github.com/sjjsnsjsj01-dev/audio-run.git"

def fail():
    print("❌ فشل رفع المرحلة 1 - إيقاف التشغيل")
    sys.exit(1)

def main():

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        print("❌ GITHUB_TOKEN غير موجود")
        fail()

    # إنشاء ملف تجريبي
    os.makedirs("stages", exist_ok=True)

    with open("stages/stage_1.txt", "w") as f:
        f.write("stage 1 test")

    try:
        subprocess.run(["git","init"], check=False)

        subprocess.run([
            "git","config","--global",
            "user.email","railway@bot.com"
        ], check=True)

        subprocess.run([
            "git","config","--global",
            "user.name","Railway Bot"
        ], check=True)

        subprocess.run(["git","add","."], check=True)
        subprocess.run(["git","commit","-m","stage 1"], check=False)

        subprocess.run([
            "git","pull",
            f"https://{token}@github.com/sjjsnsjsj01-dev/audio-run.git",
            "main",
            "--rebase"
        ], check=False)

        subprocess.run([
            "git","push",
            f"https://{token}@github.com/sjjsnsjsj01-dev/audio-run.git",
            "HEAD:main"
        ], check=True)

        print("🚀 تم رفع المرحلة 1 بنجاح")

    except Exception as e:
        print("❌ خطأ:", e)
        fail()


if __name__ == "__main__":
    main()
