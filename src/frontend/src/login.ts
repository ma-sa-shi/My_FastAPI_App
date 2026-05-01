import { apiRequest } from "./apiUtils";
import "./styles/login.css";

export class LoginView extends HTMLElement {
  connectedCallback() {
    this.render();
  }

  render() {
    const section = document.createElement("section");
    section.className = "login-container";

    const title = document.createElement("h2");
    title.className = "login-title";
    title.textContent = "ログイン";

    const usernameInput = document.createElement("input");
    usernameInput.className = "login-input";
    const passwordInput = document.createElement("input");
    passwordInput.className = "login-input";
    const loginButton = document.createElement("button");
    loginButton.className = "login-button";

    usernameInput.placeholder = "Username";
    passwordInput.placeholder = "Password";
    passwordInput.type = "password";
    loginButton.textContent = "ログイン";

    loginButton.addEventListener("click", async () => {
      const username = usernameInput.value;
      const password = passwordInput.value;
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      try {
        await apiRequest("/api/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formData,
        });

        alert("ログイン成功");
        window.location.href = "/documents";
      } catch (error) {

        if (error instanceof Error) {
          console.error("[Login Failed]:", error);

          // ログインエラー時はFastAPIのdetailを直接表示しない
          alert("メールアドレスまたはパスワードが正しくありません");
        } else {
          console.error("[Login Failed]:", error);
        }
      }
    });
    section.append(title, usernameInput, passwordInput, loginButton);
    this.replaceChildren(section);
  }
}
customElements.define("login-view", LoginView);
