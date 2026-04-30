import { apiRequest } from './apiUtils';
import "./styles/register.css";

export class RegisterView extends HTMLElement {
  connectedCallback() {
    this.render();
  }

  render() {
    const section = document.createElement('section');
    section.className = 'register-container';

    const title = document.createElement('h2');
    title.className = 'register-title';
    title.textContent = 'ユーザー登録';

    const usernameInput = document.createElement('input');
    usernameInput.className = 'register-input';
    const passwordInput = document.createElement('input');
    passwordInput.className = 'register-input';
    const registerButton = document.createElement('button');
    registerButton.className = 'register-button';

    usernameInput.placeholder = 'Username';
    passwordInput.placeholder = 'Password';
    passwordInput.type = 'password';
    registerButton.textContent = '登録';

    registerButton.addEventListener('click', async () => {
      const username = usernameInput.value;
      const password = passwordInput.value;

      try {
        await apiRequest('/api/register', {
          method: 'POST',
          body: JSON.stringify({ username, password })
        });
        alert('登録成功');
        window.location.href = '/login';
      } catch (error) {
        alert(error instanceof Error ? error.message : '登録に失敗しました');
      }
    });
    section.append(title, usernameInput, passwordInput, registerButton);
    this.replaceChildren(section);
  }
}
customElements.define('register-view', RegisterView);
