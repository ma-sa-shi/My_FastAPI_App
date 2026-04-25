import chromadb
from typing import Any
from chromadb.api.models.Collection import Collection
from chromadb.api.models.Collection import QueryResult
from rag import split_text, get_embeddings, upsert_to_chromadb

if __name__== "__main__":
    text: str = """最新のLLM（大規模言語モデル）は、Transformerアーキテクチャに基づいている。\
自然言語処理の分野ではアテンション機構が文脈における意味の決定に重要な役割を果たすが、文章が長くなるにつれて計算量がO(L^2)で増加する点が欠点だ。\
一方で、Mambaアーキテクチャは計算量が文章の長さに比例するO(L)で済む。\
生成AIのアーキテクチャは今後、これら2つの強みを組み合わせるハイブリッド型へと進化する可能性がある。"""

    # chromadb初期化
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection: Collection = chroma_client.get_or_create_collection(name="test_collection")
    
    print("---テスト開始---")

    # print("---Embedding確認---")
    chunks: list[str] = split_text(text, 50, 10)
    # print(f"チャンク数: {len(chunks)}")
    # for i, c in enumerate(chunks):
    #     print(f"チャンク{i}: {c}")

    try:
        vectors: list[list[float]] = get_embeddings(chunks)
        # print("ベクトル化成功")
        # print(f"行数: {len(vectors)}") # 出力:
        # print(f"列数: {len(vectors[0])}") # 出力:
        # print(f"先頭ベクトル: {vectors[0][:3]}")
        ids: list[str] = [f"id_{i}" for i in range(len(chunks))]
        metadatas: list[dict[str, Any]] = [{"source": "test_text", "index": i} for i in range(len(chunks))]
        upsert_to_chromadb(
            collection=collection,
            ids=ids,
            embeddings=vectors,
            documents=chunks,
            metadatas=metadatas
        )

        print("---登録内容の確認---")   
        count: int = collection.count()
        print(f"データ数: {count}") 
        # result = collection.get(ids=[ids[0]])
        # if len(result['ids']) > 0:
        #     print(f"ID: {[ids[0]]}")
        #     print(f"ドキュメント: {result["documents"][0]}")
        #     print(f"メタデータ: {result["metadatas"][0]}")
        
        print("---検索確認---")
        query_text: str = "計算量が少ない"
        query_vector: list[float] = get_embeddings([query_text])[0]
        search_results: QueryResult = collection.query(
            query_embeddings=[query_vector],
            n_results=3
        )
        
        for i in range(len(search_results['ids'][0])):
            doc: str = search_results['documents'][0][i]
            dist: float = search_results['distances'][0][i]
            print(f"順位 {i+1}: {doc} (Distance: {dist:.4f})")
        
    except Exception as e:
        print("処理中にエラー発生")
        print(e)