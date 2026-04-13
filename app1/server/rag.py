from google import genai
from google.genai import types
import chromadb
import os
from dotenv import load_dotenv
# import pprint
# import json

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# 再帰的文字分割へ後にアップグレードする
# 固定長チャンク関数
def split_text(text, chunk_size, overlap):
    chunks = []
    start = 0

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
def get_embeddings(chunks):
    if not chunks:
        return []

    # 3072次元のベクトルに変換するモデル
    model = "models/gemini-embedding-2-preview" 
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

        # 入力数(chunks)と出力(result.embeddings)の長さが違う場合のエラーハンドリング
        if len(result.embeddings) != len(chunks):
            raise ValueError(f"Embedding error: chunks num:{len(chunks)}, embeddings num {len(result.embeddings)}")
        
        return [e.values for e in result.embeddings]
    
    except Exception as e:
        print(e)
        raise

# ids:List[str] ["id1", "id2", "id3"]
# embeddings:List[List[float]] [[0.1, 0.2, ...], [0.3, -0.4, ...]]
# documents:List[str]  ["ragを実装してます。", "chromadbをsetupします。"]
# metadatas:List[dict] [{"source": "pdf"}, {"page": 5, "author": "Shimizu"}]
def upsert_to_chromadb(collection, ids, embeddings, documents, metadatas):
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )