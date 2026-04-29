interface DocumentData {
  doc_id: number;
  filename: string;
  status: 'uploaded' | 'processing' | 'ingested' | 'failed';
  created_at: string;
}

export class QueryView extends HTMLElement {
  private documents: DocumentData[] = [];
  private queryResult: string = '';
  private isLoading: boolean = false;

  connectedCallback() {
    this.fetchIngestedDocuments();
  }

  async fetchIngestedDocuments() {
    try {
      const response = await fetch('/api/admin/documents', {
        credentials: 'same-origin',
      });
      if (!response.ok) {
        console.error('ドキュメント一覧の取得に失敗しました');
        return;
      }
        const allDocs: DocumentData[] = await response.json();
        this.documents = allDocs.filter((doc) => doc.status === 'ingested');
    } catch (e) {
      console.error(e);
    } finally {
      this.render();
    }
  }

  async handleQuerySubmit() {
    const queryInput = this.querySelector(
      '#query-input',
    ) as HTMLTextAreaElement;
    const query = queryInput.value.trim();

    if (!query) {
      alert('質問を入力してください');
      return;
    }

    const checkboxes = this.querySelectorAll(
      '.doc-checkbox:checked',
    ) as NodeListOf<HTMLInputElement>;
    const selectedDocIds = Array.from(checkboxes).map((cb) =>
      parseInt(cb.value),
    );

    this.isLoading = true;
    this.queryResult = '';
    this.render();

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          query: query,
          document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
        }),
      });

      if (!response.ok) {
        this.queryResult = 'サーバーエラーが発生しました';
        return
      }

      const result = await response.json();
      this.queryResult = result.answer || '回答がありません。';
    } catch (e) {
      console.error(e);
      this.queryResult = '通信エラーが発生しました。';
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  private createNoDocsMessage(): HTMLElement {
    const p = document.createElement('p');
    p.textContent = '現在、取り込み済みのドキュメントはありません。';
    Object.assign(p.style, { color: 'black', textAlign: 'center' });
    return p;
  }

  private createDocListSection(): HTMLElement {
    const container = document.createElement('div');

    const title = document.createElement('h3');
    title.textContent = '質問対象ドキュメント (任意)';
    title.style.marginBottom = '5px';

    const list = document.createElement('div');
    Object.assign(list.style, {
      display: 'flex',
      flexDirection: 'column',
      gap: '5px',
      border: '1px solid',
      padding: '10px',
      maxHeight: '200px',
      overflowY: 'auto',
    });

    this.documents.forEach((doc) => {
      const label = document.createElement('label');
      Object.assign(label.style, {
        display: 'flex',
        alignItems: 'center',
        gap: '5px',
        cursor: this.isLoading ? 'not-allowed' : 'pointer',
      });

      label.innerHTML = `
      <input type='checkbox' class='doc-checkbox' value='${doc.doc_id}' ${this.isLoading ? 'disabled' : ''}>
      ${doc.filename} (ID: ${doc.doc_id})
    `;
      list.appendChild(label);
    });

    container.append(title, list);
    return container;
  }

  render() {
    const section = document.createElement('section');
    Object.assign(section.style, {
      display: 'flex',
      flexDirection: 'column',
      gap: '15px',
      padding: '20px',
      maxWidth: '800px',
    });

    const title = document.createElement('h2');
    title.textContent = 'RAGアプリへの質問';

    const queryLabel = document.createElement('label');
    queryLabel.textContent = '質問内容:';
    const queryInput = document.createElement('textarea');
    queryInput.id = 'query-input';
    queryInput.placeholder = '質問を入力してください...';
    Object.assign(queryInput.style, {
      width: '100%',
      minHeight: '100px',
      padding: '8px',
      border: '1px solid',
      resize: 'vertical',
    });
    queryInput.disabled = this.isLoading;

    const docSelectionSection = this.documents.length > 0
    ? this.createDocListSection()
    : this.createNoDocsMessage();

    // 送信ボタン
    const submitButton = document.createElement('button');
    submitButton.textContent = this.isLoading ? '処理中...' : '質問を送信';
    Object.assign(submitButton.style, {
      padding: '10px 15px', // 文字周りのスペース
      cursor: this.isLoading ? 'not-allowed' : 'pointer', // クリック可能かどうか
    });
    submitButton.disabled = this.isLoading;
    submitButton.addEventListener('click', () => this.handleQuerySubmit());

    // 回答表示エリア
    const resultArea = document.createElement('div');
    Object.assign(resultArea.style, {
      marginTop: '20px', // 上要素とのスペース
      padding: '5px', // 枠線と中身の間の余白
      border: '1px solid',
      minHeight: '100px', // 中身がない場合の最小の高さ
      whiteSpace: 'pre-wrap', // 長いテキストを折り返す
      wordBreak: 'break-word', // 長い単語を折り返す
    });
    const resultTitle = document.createElement('h3');
    resultTitle.textContent = '回答:';
    Object.assign(resultTitle.style, {
      margin: '0 0 10px 0',
    });
    const resultContent = document.createElement('p');
    resultContent.textContent =
      this.queryResult || 'ここに回答が表示されます。';
    resultArea.append(resultTitle, resultContent);

    section.append(
      title,
      queryLabel,
      queryInput,
      docSelectionSection,
      submitButton,
      resultArea,
    );
    this.replaceChildren(section);
  }
}
customElements.define('query-view', QueryView);
