// Authentication logic for Cipher Frame login and register pages.

import { login, register, setCurrentUser, setToken } from "./api.js";

function showError(element, message) {
  if (element) {
    element.textContent = message || "";
  }
}

function passwordStrengthValid(password) {
  return password.length >= 12;
}

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");

  if (loginForm) {
    const loginError = document.getElementById("login-error");
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      showError(loginError, "");
      const username = document.getElementById("login-username").value.trim();
      const password = document.getElementById("login-password").value;
      try {
        await login(username, password);
        window.location.href = "/chat.html";
      } catch (error) {
        showError(loginError, error.message);
      }
    });
  }

  if (registerForm) {
    const registerError = document.getElementById("register-error");
    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      showError(registerError, "");

      const username = document.getElementById("register-username").value.trim();
      const email = document.getElementById("register-email").value.trim();
      const password = document.getElementById("register-password").value;
      const confirmPassword = document.getElementById("register-confirm-password").value;

      if (password !== confirmPassword) {
        showError(registerError, "Passwords do not match.");
        return;
      }
      if (!passwordStrengthValid(password)) {
        showError(registerError, "Password must be at least 12 characters long.");
        return;
      }

      try {
        await register(username, email, password);
        const { token, user } = await login(username, password);
        setToken(token);
        setCurrentUser(user);
        window.location.href = "/chat.html";
      } catch (error) {
        showError(registerError, error.message);
      }
    });
  }
});