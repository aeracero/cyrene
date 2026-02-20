# 軽量で公式なPython 3.10環境を使用
FROM python:3.10-slim

# システムの必須ライブラリ（FFmpeg, Opus, espeakなど）を通常のUbuntu標準パスに確実にインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus0 \
    libopus-dev \
    espeak-ng \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ワークディレクトリの設定
WORKDIR /app

# パッケージのインストール（ここで要件ファイルを先に処理）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# コードをすべてコピー
COPY . .

# Botの起動コマンド
CMD ["python", "cyrene.py"]