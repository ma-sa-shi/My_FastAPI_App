import { apiRequest } from './apiUtils';
import type { DocumentData } from './types';
import './styles/manageDocs.css';

export class ManageDocsView extends HTMLElement {
  private documents: DocumentData[] = [];
  private logs: string[] = [];
  private isProcessing: boolean = false;
  private isUploading: boolean = false;

  connectedCallback() {
    this.fetchDocuments();
  }

  /**
   * ドキュメント一覧の更新
   */
  async fetchDocuments() {
    try {
        this.documents = await apiRequest<DocumentData[]>('/api/admin/documents', {
        credentials: 'same-origin',
      });
    } catch (error) {
      console.error('[Fetch Documents Failed]:', error);
    } finally {
      this.render();
    }
  }

 /**
   * ファイルアップロード処理
   */
  async handleUpload(fileInput: HTMLInputElement) {
    const file = fileInput.files?.[0];
    if (!file) return alert('ファイルを選択してください');

    if (file.size > 5 * 1024 * 1024) return alert('5MB以下のファイルを選択してください');

    this.isUploading = true;
    this.render();

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/admin/upload/', {
          method: 'POST',
          credentials: 'same-origin',
          body: formData,
        });

        if (!response.ok) {
          alert(response.status === 401 ? 'ログインが必要です' : 'アップロード失敗');
          } else {
          const result = await response.json();
          alert(`アップロード成功: ${result.fileName}`);
          fileInput.value = '';
          await this.fetchDocuments();
        }
      } catch (error) {
        console.error('[Upload Failed]:', error);
      } finally {
        this.isUploading = false;
        this.render();
      }
    }

  /**
   * 一括取込み処理
   */
  async handleBatchIngest() {
    const checkboxes = this.querySelectorAll('.doc-checkbox:checked') as NodeListOf<HTMLInputElement>;

    const selectedIds = Array.from(checkboxes).map((cb) => parseInt(cb.value));

    if (selectedIds.length === 0) return alert('ドキュメントを選択してください');

    this.isProcessing = true;
    this.logs = [];
    this.render();

    for (const docId of selectedIds) {
      const doc = this.documents.find((d) => d.doc_id === docId);
      try {
        await apiRequest(`/api/admin/documents/${docId}/ingest`, {
          method: 'POST',
          credentials: 'same-origin',
        });
        this.logs.push(`${doc?.filename}: 処理を開始しました`);
      } catch (error) {
        console.error(`[Ingest Failed for ${doc?.filename}]:`, error);
        this.logs.push(`${doc?.filename}: エラーが発生しました`);
      }
      this.render();
    }
    this.isProcessing = false;
    await this.fetchDocuments();
  }

  render() {
    const container = document.createElement('div');
    container.className = 'manage-docs-container';

    // アップロード処理
    const uploadDiv = document.createElement('section');
    uploadDiv.className = 'manage-docs-section';

    const uploadTitle = document.createElement('h3');
    uploadTitle.textContent = 'アップロード';

    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.pdf,.txt,.md';

    const uploadButton = document.createElement('button');
    uploadButton.textContent = this.isUploading ? '送信中' : 'アップロード';
    uploadButton.disabled = this.isUploading;
    uploadButton.addEventListener('click', () => this.handleUpload(fileInput));
    uploadDiv.append(uploadTitle, fileInput, uploadButton);

    // ドキュメント一覧と一括処理
    const listDiv = document.createElement('section');

    const documentTitle = document.createElement('h3');
    documentTitle.textContent = 'ドキュメント一覧';

    const table = this.createTable();

    const ingestButton = document.createElement('button');
    ingestButton.textContent = this.isProcessing ? '処理中' : '一括処理';
    ingestButton.disabled = this.isProcessing;
    ingestButton.onclick = () => this.handleBatchIngest();

    const logDiv = document.createElement('div');
    logDiv.className = 'log-container';

    this.logs.forEach(msg => {
      const p = document.createElement('p');
      p.textContent = msg;
      p.className = 'log-message';
      logDiv.appendChild(p);
    });

    listDiv.append(documentTitle, table, ingestButton, logDiv);
    container.append(uploadDiv, listDiv);
    this.replaceChildren(container);
  }

  private createTable() {
    const table = document.createElement('table');
    table.className = 'docs-table';

    const thead = document.createElement('thead');

    const headerRow = document.createElement('tr');

    ['選択', 'ID', 'ファイル名', 'ステータス'].forEach(text => {
      const th = document.createElement('th');
      th.textContent = text;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    this.documents.forEach(doc => {
      const tr = document.createElement('tr');

      const createCell = (content: string | HTMLElement) => {
        const td = document.createElement('td');
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
      checkbox.disabled = this.isProcessing;

      tr.append(
        createCell(checkbox),
        createCell(doc.doc_id.toString()),
        createCell(doc.filename),
        createCell(doc.status)
      );
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
  }
}
customElements.define('manage-docs-view', ManageDocsView);