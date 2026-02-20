# 軽量で公式なPython 3.10環境を使用
FROM python:3.10-slim

# システムの必須ライブラリと「日本語処理用パッケージ(mecab等)」を追加
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus0 \
    libopus-dev \
    espeak-ng \
    git \
    build-essential \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    && rm -rf /var/lib/apt/lists/*

# ワークディレクトリの設定
WORKDIR /app

# パッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# XTTSv2の日本語解析に必要なPython辞書をインストール
RUN pip install --no-cache-dir mecab-python3 unidic-lite

# コードをすべてコピー
COPY . .

# Botの起動コマンド
CMD ["python", "cyrene.py"]