interface DocumentData {
  doc_id: number;
  filename: string;
  status: 'uploaded' | 'processing' | 'ingested' | 'failed';
  created_at: string;
}

export class IngestView extends HTMLElement {
  private documents: DocumentData[] = [];
  private logs: string[] = [];
  private isProcessing: boolean = false;

  connectedCallback() {
    this.fetchDocuments();
  }

  async fetchDocuments() {
    try {
      const response = await fetch('/api/admin/documents', {
        credentials: 'same-origin',
      });
      if (!response.ok) {
        console.error('ドキュメント一覧の取得に失敗しました');
        return;
      }
      this.documents = await response.json();
    } catch (e) {
      console.error(e);
    } finally {
      this.render();
    }
  }

  async handleBatchIngest() {
    // コンポーネント(ingestView)から条件に合う要素を全て探す。as NodeListOf<HTMLInputElement>は型アサーション。
    const checkboxes = this.querySelectorAll(
      '.doc-checkbox:checked',
    ) as NodeListOf<HTMLInputElement>;
    // NodeListをArrayに変換しintに変換
    const selectedIds = Array.from(checkboxes).map((cb) => parseInt(cb.value));

    if (selectedIds.length === 0) {
      alert('取込むドキュメントを選択してください');
      return;
    }

    this.isProcessing = true;
    this.logs = [];
    this.render();

    for (const docId of selectedIds) {
      const doc = this.documents.find((d) => d.doc_id === docId);
      try {
        // awaitによりサーバー負荷の安定を維持
        const response = await fetch(`/api/admin/documents/${docId}/ingest`, {
          method: 'POST',
          credentials: 'same-origin',
        });
        if (!response.ok) {
          this.logs.push(`${doc?.filename}: サーバーエラーが発生しました`);
          continue;
        }
        const result = await response.json();
        // オプショナルチェイニングによりdocが見つからない場合でもエラー回避
        this.logs.push(`${doc?.filename}: 取込み処理を開始しました `);
      } catch (e) {
        this.logs.push(`${doc?.filename}: 通信エラーが発生しました`);
      }
      this.render();
    }

    this.isProcessing = false;
    await this.fetchDocuments();
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
    title.textContent = 'ドキュメント管理・取込み';

    const table = document.createElement('table');
    table.style.borderCollapse = 'collapse';
    table.style.width = '100%';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headerRow.style.backgroundColor = 'white';
    ['選択', 'ID', 'ファイル名', 'ステータス'].forEach((text) => {
      const th = document.createElement('th');
      th.textContent = text;
      Object.assign(th.style, {
        border: '1px solid white',
        padding: '8px',
        textAlign: 'left',
      });
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    this.documents.forEach((doc) => {
      const tr = document.createElement('tr');

      // 文字列ならテキスト、HTMLElementなら子要素に追加する関数
      const createCell = (content: HTMLElement | string) => {
        const td = document.createElement('td');
        Object.assign(td.style, { border: '1px solid #ddd', padding: '8px' });
        if (typeof content === 'string') {
          td.textContent = content;
        } else {
          td.appendChild(content);
        }
        return td;
      };

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'doc-checkbox';
      checkbox.value = doc.doc_id.toString();
      checkbox.style.textAlign = 'center';
      checkbox.disabled = this.isProcessing;

      [checkbox, doc.doc_id.toString(), doc.filename, doc.status].forEach(
        (content) => tr.appendChild(createCell(content)),
      );
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    const ingestButton = document.createElement('button');
    ingestButton.textContent = this.isProcessing
      ? '処理中'
      : '選択したファイルを一括取込み';
    ingestButton.style.padding = '10px';
    ingestButton.disabled = this.isProcessing;
    ingestButton.addEventListener('click', () => this.handleBatchIngest());

    const logArea = document.createElement('div');
    Object.assign(logArea.style, {
      marginTop: '10px',
    });
    this.logs.forEach((msg) => {
      const logItem = document.createElement('div');
      logItem.textContent = msg;
      logArea.appendChild(logItem);
    });

    section.append(title, table, ingestButton, logArea);
    this.replaceChildren(section);
  }
}
customElements.define('ingest-view', IngestView);
