// Sysadmin dashboard behavior for Cipher Frame.

import {
  getAdminKeys,
  getAdminLogs,
  getAdminMessages,
  getAdminOverview,
  getAdminUsers,
  getMe,
  logout,
  rotateAdminUserKeys,
  setCurrentUser,
  updateAdminUserStatus,
} from "./api.js";

const state = {
  currentUser: null,
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function addNotification(message, tone = "neutral") {
  const list = document.getElementById("admin-notifications");
  if (!list) return;
  const item = document.createElement("li");
  item.className = tone;
  item.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
  list.prepend(item);
}

function renderOverview(overview) {
  const grid = document.getElementById("overview-grid");
  if (!grid) return;

  const cards = [
    ["Total Users", overview.total_users],
    ["Active Users", overview.active_users],
    ["Total Messages", overview.total_messages],
    ["Delivered Messages", overview.delivered_messages],
    ["Online Users", overview.online_users_count],
    ["Server Logs", overview.total_server_logs],
  ];

  grid.innerHTML = cards
    .map(
      ([label, value]) => `
        <article class="stat-card">
          <span class="stat-label">${label}</span>
          <strong class="stat-value">${value}</strong>
        </article>
      `,
    )
    .join("");
}

function renderUsers(users) {
  const tbody = document.getElementById("admin-users-table");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!users.length) {
    tbody.innerHTML = '<tr><td class="empty-state" colspan="6">No users found.</td></tr>';
    return;
  }

  users.forEach((user) => {
    const nextState = !user.is_active;
    const actionLabel = user.is_active ? "Disable" : "Enable";
    const actionDisabled = user.id === state.currentUser?.id && user.is_active;

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(user.username)}</td>
      <td>${escapeHtml(user.email)}</td>
      <td>${escapeHtml(user.role)}</td>
      <td><span class="inline-pill ${user.is_active ? "positive" : "negative"}">${user.is_active ? "Active" : "Disabled"}</span></td>
      <td>${escapeHtml(formatDate(user.last_login))}</td>
      <td>
        <div class="action-group">
          <button class="table-action" data-user-action="toggle-status" data-user-id="${user.id}" data-next-state="${nextState}" ${actionDisabled ? "disabled" : ""}>${actionLabel}</button>
          <button class="table-action" data-user-action="rotate-keys" data-user-id="${user.id}">Rotate RSA Keys</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function renderMessages(messages) {
  const tbody = document.getElementById("admin-messages-table");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!messages.length) {
    tbody.innerHTML = '<tr><td class="empty-state" colspan="7">No messages found.</td></tr>';
    return;
  }

  messages.forEach((message) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(message.sender_username)}</td>
      <td>${escapeHtml(message.receiver_username)}</td>
      <td>${escapeHtml(message.original_filename)}</td>
      <td>${escapeHtml(message.status)}</td>
      <td>${escapeHtml(formatDate(message.created_at))}</td>
      <td>${escapeHtml(formatDate(message.delivered_at))}</td>
      <td>${escapeHtml(message.encryption_algorithm)} / ${escapeHtml(message.signature_algorithm)}</td>
    `;
    tbody.appendChild(row);
  });
}

function renderLogs(logs) {
  const tbody = document.getElementById("admin-logs-table");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!logs.length) {
    tbody.innerHTML = '<tr><td class="empty-state" colspan="6">No logs found.</td></tr>';
    return;
  }

  logs.forEach((logEntry) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(logEntry.level)}</td>
      <td>${escapeHtml(logEntry.event_type)}</td>
      <td>${escapeHtml(logEntry.message)}</td>
      <td>${escapeHtml(logEntry.actor || "-")}</td>
      <td>${escapeHtml(logEntry.ip_address || "-")}</td>
      <td>${escapeHtml(formatDate(logEntry.created_at))}</td>
    `;
    tbody.appendChild(row);
  });
}

function renderKeys(keys) {
  const tbody = document.getElementById("admin-keys-table");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!keys.length) {
    tbody.innerHTML = '<tr><td class="empty-state" colspan="5">No RSA keys found.</td></tr>';
    return;
  }

  keys.forEach((keyEntry) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(keyEntry.username)}</td>
      <td>${escapeHtml(keyEntry.key_version)}</td>
      <td><span class="inline-pill ${keyEntry.is_active ? "positive" : "negative"}">${keyEntry.is_active ? "Active" : "Inactive"}</span></td>
      <td>${escapeHtml(formatDate(keyEntry.created_at))}</td>
      <td>${escapeHtml(formatDate(keyEntry.expires_at))}</td>
    `;
    tbody.appendChild(row);
  });
}

async function loadAll() {
  const [overview, users, messages, logs, keys] = await Promise.all([
    getAdminOverview(),
    getAdminUsers(),
    getAdminMessages(),
    getAdminLogs({ limit: 100 }),
    getAdminKeys(),
  ]);

  renderOverview(overview);
  renderUsers(users);
  renderMessages(messages);
  renderLogs(logs);
  renderKeys(keys);
}

function bindActions() {
  document.body.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-user-action]");
    if (!button) return;

    const userId = Number(button.dataset.userId);
    try {
      if (button.dataset.userAction === "toggle-status") {
        await updateAdminUserStatus(userId, button.dataset.nextState === "true");
        addNotification(`Updated user ${userId} status`, "text-success");
      }
      if (button.dataset.userAction === "rotate-keys") {
        await rotateAdminUserKeys(userId);
        addNotification(`Rotated RSA keys for user ${userId}`, "text-success");
      }
      await loadAll();
    } catch (error) {
      addNotification(error.message, "text-danger");
    }
  });
}

function bindToolbar() {
  document.getElementById("admin-logout")?.addEventListener("click", () => {
    logout();
    window.location.href = "/login.html";
  });

  document.getElementById("back-to-chat")?.addEventListener("click", () => {
    window.location.href = "/chat.html";
  });

  document.getElementById("refresh-admin")?.addEventListener("click", async () => {
    try {
      await loadAll();
      addNotification("Dashboard refreshed", "text-success");
    } catch (error) {
      addNotification(error.message, "text-danger");
    }
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!localStorage.getItem("cipherframe_token")) {
    window.location.href = "/login.html";
    return;
  }

  try {
    const user = await getMe();
    setCurrentUser(user);
    if (user.role !== "admin") {
      window.location.href = "/chat.html";
      return;
    }

    state.currentUser = user;
    document.getElementById("admin-username").textContent = user.username;
    bindActions();
    bindToolbar();
    await loadAll();
  } catch (error) {
    logout();
    window.location.href = "/login.html";
  }
});