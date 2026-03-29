FROM python:3.11-slim

# Playwright用のブラウザ依存パッケージ
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Python依存パッケージ
RUN pip install --no-cache-dir flask waitress requests rich click playwright yt-dlp

# Playwrightブラウザインストール
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

COPY . .

EXPOSE 3000

CMD ["python", "-c", "from waitress import serve; from app import app; print('Server running on port 3000'); serve(app, host='0.0.0.0', port=3000)"]
