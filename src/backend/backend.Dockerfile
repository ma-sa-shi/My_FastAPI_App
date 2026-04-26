FROM python:3.13-slim

WORKDIR /app

# build-essentialはpythonライブラリをインストールするためのC言語のコンパイラ
# pkg-configとdefault-libmysqlclient-devはmysqlclientやPyMySQLがmysqlと通信するためのシステムライブラリ
# rm -rf /var/lib/apt/lists/*はインストール後不要になったパッケージリストを削除
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetryのインストール
ENV POETRY_HOME="/opt/poetry"
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# venvを作らずコンテナに直接インストールする設定
RUN poetry config virtualenvs.create false

# 依存関係のファイルコピー
COPY pyproject.toml poetry.lock* ./

# 依存関係のインストール
RUN poetry install --no-interaction --no-ansi --only main --no-root

COPY . .

# アプリが使用するポート
EXPOSE 8000