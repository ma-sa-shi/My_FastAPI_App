from google import genai
from google.genai import types
import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Embeddings, Metadatas
import os
from dotenv import load_dotenv
from typing import cast
from chromadb.api.models.Collection import Collection
import pymupdf
from pathlib import Path
from database import get_db_connection
from datetime import datetime
# import pprint
# import json

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# 再帰的文字分割へ後にアップグレードする
# 固定長チャンク関数
def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start: int = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        # 次のスタート位置
        start += (chunk_size - overlap)

        # 残り文字数がoverlap以下ならループ終了
        if start >= len(text) - overlap and len(text) > chunk_size:
            break

    return chunks

# Gemini APIによりテキストをベクトル化(embedding)
# 文字列のリスト(chunks)を渡して3072次元のベクトルを返す
def get_embeddings(chunks: list[str]) -> Embeddings:
    if not chunks:
        return []

    # 3072次元のベクトルに変換するモデル
    model: str = "models/gemini-embedding-2-preview"

    try:
        requests = [types.Content(parts=[types.Part(text=c)]) for c in chunks]
        result = client.models.embed_content(
            model=model,
            contents=requests,
            # ドキュメント登録用に最適化
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )

        # 構造確認用
        # with open("debug_response.json", "w", encoding="utf-8") as f:
        #     json.dump(result.model_dump(), f, indent=4, ensure_ascii=False)

        embeddings = result.embeddings
        if embeddings is None:
            raise ValueError("API returned None for embeddings")
        # 入力数(chunks)と出力(result.embeddings)の長さが違う場合のエラーハンドリング
        if len(embeddings) != len(chunks):
            raise ValueError(f"Embedding error: chunks num:{len(chunks)}, embeddings num {len(embeddings)}")

        output: list[list[float]] = []
        for e in embeddings:
            if e.values is not None:
                output.append(e.values)
            else:
                raise ValueError("One of the embeddings values is None")

        return cast(Embeddings, output)

    except Exception as e:
        print(e)
        raise

def upsert_to_chromadb(
    collection: Collection,
    ids: list[str],
    embeddings: Embeddings,
    documents: list[str],
    metadatas: Metadatas
) -> None:
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

def extract_text(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} is not found")
    ext = file_path.suffix.lower()

    if ext in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8")

    elif ext == ".pdf":
        text_parts = []
        with pymupdf.open(file_path) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        return "".join(text_parts)
    raise ValueError(f"Unsupported file extension {ext}")

def run_ingest_pipeline(doc_id: int, file_path: Path, user_id: int, created_at:datetime):
    connection = get_db_connection()
    try:
        text = extract_text(file_path)
        with connection.cursor() as cursor:
            cursor.execute("UPDATE docs SET extracted_text = %s WHERE doc_id = %s", (text, doc_id))
            connection.commit()

        chunks = split_text(text, chunk_size=1000, overlap=100)

        embeddings:Embeddings = get_embeddings(chunks)

        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection: Collection = chroma_client.get_or_create_collection(name="rag_app")


        ids: list[str] = [f"{doc_id}_{i}" for i in range(len(chunks))]
        created_at_str = created_at.isoformat()
        metadatas: Metadatas = [
            {
                "doc_id": doc_id,
                "user_id": user_id,
                "filename": file_path.name,
                "chunk_index": i,
                "created_at": created_at_str
            }
            for i in range(len(chunks))
        ]
        upsert_to_chromadb(
            collection=collection,
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )

        with connection.cursor() as cursor:
            cursor.execute("UPDATE docs SET status = 'completed' WHERE doc_id = %s", (doc_id,))
            connection.commit()
    except Exception as e:
        print(e)
        with connection.cursor() as cursor:
            cursor.execute("UPDATE docs SET status = 'failed' WHERE doc_id = %s", (doc_id,))
            connection.commit()
    finally:
        connection.close()