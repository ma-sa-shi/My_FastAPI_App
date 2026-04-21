export class LoginView extends HTMLElement {
  connectedCallback() {
    this.render();
  }

  render() {
    const section = document.createElement('section');
    section.style.display = 'flex';
    section.style.flexDirection = 'column';
    section.style.gap = '10px';
    section.style.width = '300px';
    const title = document.createElement('h2');
    title.textContent = 'ログイン';

    const usernameInput = document.createElement('input');
    const passwordInput = document.createElement('input');
    const loginButton = document.createElement('button');

    usernameInput.placeholder = 'Username';
    passwordInput.placeholder = 'Password';
    passwordInput.type = 'password';
    loginButton.textContent = 'ログイン';

    loginButton.addEventListener('click', async () => {
      const username = usernameInput.value;
      const password = passwordInput.value;

      try {
        const response = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ username, password }).toString()
        });

        if (response.ok) {
          alert('ログイン成功');
        } else {
          alert('ログイン失敗');
        }
      } catch (e) {
        console.error(e);
      }
    });
    section.append(title, usernameInput, passwordInput, loginButton);
    this.replaceChildren(section);
  }
}
customElements.define('login-view', LoginView);
