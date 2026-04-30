import { apiRequest } from './apiUtils';

export class UploadView extends HTMLElement {
  private isLoading = false;

  connectedCallback() {
    this.render();
  }

  render() {
    const section = document.createElement('section');
    Object.assign(section.style, {
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      width: '300px',
    });

    const title = document.createElement('h2');
    title.textContent = 'ファイルアップロード';

    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.pdf,.txt,.md';

    const uploadButton = document.createElement('button');
    uploadButton.textContent = 'アップロード';

    uploadButton.addEventListener('click', async () => {
      const file = fileInput.files?.[0];

      if (!file) {
        alert('ファイルを選択してください');
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        alert('5MB以下のファイルを選択してください');
        return;
      }

      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/api/admin/upload/', {
          method: 'POST',
          credentials: 'same-origin',
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          alert(`アップロード成功: ${result.fileName}`);
        } else {
          if (response.status === 401) {
            alert('ログインが必要です');
          } else {
            alert('アップロード失敗');
          }
        }
      } catch (e) {
        console.error(e);
      }
    });

    section.append(title, fileInput, uploadButton);
    this.replaceChildren(section);
  }
}
customElements.define('upload-view', UploadView);
