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
    # 3072次元のベクトルに変換するモデル
    model = "models/gemini-embedding-2-preview" 
    # result()
    try:
        result = client.models.embed_content(
            model=model,
            contents=chunks,
            # ドキュメント登録用に最適化
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )

        # 構造確認用
        # with open("debug_response.json", "w", encoding="utf-8") as f:
        #     json.dump(result.model_dump(), f, indent=4, ensure_ascii=False)
        
        return [e.values for e in result.embeddings]
    except Exception as e:
        print(e)
        raise