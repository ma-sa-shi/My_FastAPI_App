export class RegisterView extends HTMLElement {
  connectedCallback() {
    this.render();
  }

  render() {
    const section = document.createElement('section');
    Object.assign(section.style, {
      display: 'flex', flexDirection: 'column', gap: '10px', width: '300px'
    });

    const title = document.createElement('h2');
    title.textContent = 'ユーザー登録';

    const usernameInput = document.createElement('input');
    const passwordInput = document.createElement('input');
    const registerButton = document.createElement('button');

    usernameInput.placeholder = 'Username';
    passwordInput.placeholder = 'Password';
    passwordInput.type = 'password';
    registerButton.textContent = '登録';

    registerButton.addEventListener('click', async () => {
      const username = usernameInput.value;
      const password = passwordInput.value;

      try {
        const response = await fetch('/api/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });

        if (response.ok) {
          alert('登録成功');
          window.location.href = '/login';
        } else {
          alert('登録失敗');
        }
      } catch (e) {
        console.error(e);
      }
    });
    section.append(title, usernameInput, passwordInput, registerButton);
    this.replaceChildren(section);
  }
}
customElements.define('register-view', RegisterView);
