/**
 * クエリ実行コンポーネント
 * ユーザー入力をバックエンドに送信し、RAGによる回答を表示・管理します。
 */

import type { DocumentData } from './types';
import { apiRequest } from './apiUtils';
import './styles/query.css';

export class QueryView extends HTMLElement {
  private documents: DocumentData[] = [];
  private queryResult: string = '';
  private isLoading: boolean = false;

  async connectedCallback() {
    await this.fetchIngestedDocuments();
  }

  async fetchIngestedDocuments() {
    try {
      const allDocs = await apiRequest<DocumentData[]>('/api/admin/documents', {
        credentials: 'same-origin',
      });
      this.documents = allDocs.filter((doc) => doc.status === 'ingested');
    } catch (error) {
      console.error('[Fetch Documents Failed]:', error);
    } finally {
      // 成功・失敗に関わらず再描画してリストの状態を反映
      this.render();
    }
  }

  async handleQuerySubmit() {
    const queryInput = this.querySelector('#query-input') as HTMLTextAreaElement;
    const query = queryInput.value.trim();

    if (!query) {
      alert('質問を入力してください');
      return;
    }

    const checkboxes = this.querySelectorAll('.doc-checkbox:checked') as NodeListOf<HTMLInputElement>;
    const selectedDocIds = Array.from(checkboxes).map((cb) =>
      parseInt(cb.value),
    );

    this.isLoading = true;
    this.queryResult = '回答を生成中';
    this.render();

    try {
      const result = await apiRequest<{ answer: string }>('/api/query', {
        method: 'POST',
        body: JSON.stringify({
          query: query,
          document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
        }),
      });

      this.queryResult = result.answer || '回答がありません。';
    } catch (error) {
      const message = error instanceof Error ? error.message : '通信エラーが発生しました';
      this.queryResult = `エラー: ${message}`;
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  private createNoDocsMessage(): HTMLElement {
    const p = document.createElement('p');
    p.textContent = '現在、取込み済のドキュメントはありません。';
    Object.assign(p.style, { color: 'black', textAlign: 'center' });
    return p;
  }

  private createDocListSection(): HTMLElement {
    const container = document.createElement('div');
    const title = document.createElement('h3');
    title.textContent = '質問対象ドキュメント (任意)';
    title.style.marginBottom = '5px';

    const list = document.createElement('div');
    list.className = 'doc-list-container';

    this.documents.forEach((doc) => {
      const label = document.createElement('label');
      label.className = 'doc-label';
      label.classList.toggle('is-loading', this.isLoading);

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'doc-checkbox';
      checkbox.value = doc.doc_id.toString();
      checkbox.disabled = this.isLoading;

      const docName = document.createElement('span');
      docName.textContent = doc.filename;

      label.append(checkbox, docName);
      list.appendChild(label);
    });

    container.append(title, list);
    return container;
  }

  /**
   * メイン描画処理
   */
  render() {
    const section = document.createElement('section');
    section.className = 'query-container';

    const title = document.createElement('h2');
    title.textContent = 'RAGアプリへの質問';

    const queryInput = document.createElement('textarea');
    queryInput.id = 'query-input';
    queryInput.placeholder = '質問を入力してください';
    queryInput.className = 'query-textarea';
    queryInput.disabled = this.isLoading;

    const docSelectionSection = this.documents.length > 0
    ? this.createDocListSection()
    : this.createNoDocsMessage();

    // 送信ボタン
    const submitButton = document.createElement('button');
    submitButton.textContent = this.isLoading ? '処理中' : '質問を送信';
    submitButton.className = 'submit-button';
    submitButton.disabled = this.isLoading;
    submitButton.addEventListener('click', () => this.handleQuerySubmit());

    // 回答表示エリア
    const resultArea = document.createElement('div');
    resultArea.className = 'result-area';

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
      queryInput,
      docSelectionSection,
      submitButton,
      resultArea,
    );
    this.replaceChildren(section);
  }
}
customElements.define('query-view', QueryView);
