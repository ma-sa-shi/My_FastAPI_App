FROM python:3.13-slim

WORKDIR /app

# build-essentialはpythonライブラリをインストールするためのC言語のコンパイラ
# pkg-configとdefault-libmysqlclient-devはmysqlclientやPyMySQLがmysqlと通信するためのシステムライブラリ
# rm -rf /var/lib/apt/lists/*はインストール後不要になったパッケージリストを削除
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# アプリが使用するポート
EXPOSE 8000 