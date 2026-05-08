FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# 🔥 صلاحيات ffmpeg المعدل
RUN chmod +x tiny/ffmpeg

# 🔥 إذا يوجد ffprobe
RUN chmod +x tiny/ffprobe || true

# 🔥 start.sh
RUN dos2unix start.sh
RUN chmod +x start.sh

CMD ["./start.sh"]