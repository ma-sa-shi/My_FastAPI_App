from rag import split_text, get_embeddings

if __name__== "__main__":
    text = "RAGアプリを開発している。チャンク分割とベクトル化のテストを実施している。"

    print("---テスト開始---")

    chunks = split_text(text, 10, 3)
    print(f"チャンク数: {len(chunks)}") # 出力:5
    for i, c in enumerate(chunks):
        print(f"チャンク{i}: {c}")

    try:
        vectors = get_embeddings(chunks)
        print("ベクトル化成功")
        print(f"行数: {len(vectors)}") # 出力:1 
        print(f"列数: {len(vectors[0])}") # 出力:3072
        print(f"ベクトル: {vectors[0][:3]}")
    except Exception as e:
        print("ベクトル化失敗")
        print(e)