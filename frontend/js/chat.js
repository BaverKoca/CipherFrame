// Chat dashboard behavior for Cipher Frame.

import {
  getCurrentUser,
  getInbox,
  getMessage,
  getOnlineUsers,
  getSent,
  logout,
  sendImage,
  verifyMessage,
} from "./api.js";
import { createChatSocket } from "./websocket.js";

const state = {
  socket: null,
  currentUser: null,
  selectedMessageId: null,
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function addNotification(message, tone = "neutral") {
  const list = document.getElementById("notification-list");
  if (!list) return;
  const item = document.createElement("li");
  item.className = tone;
  item.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
  list.prepend(item);
}

function setSignatureBadge(valid) {
  const badge = document.getElementById("signature-badge");
  if (!badge) return;
  if (valid === true) {
    badge.textContent = "Signature Valid";
    badge.className = "status-pill";
  } else if (valid === false) {
    badge.textContent = "Signature Invalid";
    badge.className = "status-pill warning";
  } else {
    badge.textContent = "Signature Unknown";
    badge.className = "status-pill neutral";
  }
}

function setViewerDetails(text) {
  const details = document.getElementById("message-details");
  if (details) {
    details.textContent = text;
  }
}

function renderOnlineUsers(users) {
  const list = document.getElementById("online-users");
  const select = document.getElementById("receiver-select");
  if (!list || !select) return;

  list.innerHTML = "";
  select.innerHTML = "";

  users.forEach((user) => {
    const userItem = document.createElement("li");
    userItem.innerHTML = `<strong>${escapeHtml(user.username)}</strong><br><small>${escapeHtml(user.last_activity)}</small>`;
    list.appendChild(userItem);

    if (state.currentUser && user.user_id === state.currentUser.id) {
      return;
    }

    const option = document.createElement("option");
    option.value = user.username;
    option.textContent = user.username;
    select.appendChild(option);
  });
}

function renderTable(tbodyId, rows, type) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!rows.length) {
    const row = document.createElement("tr");
    row.innerHTML = `<td class="empty-state" colspan="5">No messages yet.</td>`;
    tbody.appendChild(row);
    return;
  }

  rows.forEach((rowData) => {
    const row = document.createElement("tr");
    const actor = type === "inbox" ? rowData.sender : rowData.receiver;
    const actionLabel = type === "inbox" ? "Open message" : "Verify";
    row.innerHTML = `
      <td>${rowData.message_id}</td>
      <td>${escapeHtml(actor.username)}</td>
      <td>${escapeHtml(rowData.timestamp)}</td>
      <td>${escapeHtml(rowData.status)}</td>
      <td><button class="link-button" data-message-id="${rowData.message_id}" data-action="${type}">${actionLabel}</button></td>
    `;
    tbody.appendChild(row);
  });
}

async function loadOnlineUsers() {
  const users = await getOnlineUsers();
  renderOnlineUsers(users);
}

async function loadInbox() {
  const inbox = await getInbox();
  renderTable("inbox-table", inbox, "inbox");
}

async function loadSent() {
  const sent = await getSent();
  renderTable("sent-table", sent, "sent");
}

async function openMessage(messageId) {
  state.selectedMessageId = messageId;
  const payload = await getMessage(messageId);
  const image = document.getElementById("received-image");
  const meta = document.getElementById("viewer-meta");
  if (image) {
    const filename = (payload.filename || "").toLowerCase();
    const mimeType = filename.endsWith(".jpg") || filename.endsWith(".jpeg")
      ? "image/jpeg"
      : filename.endsWith(".gif")
        ? "image/gif"
        : filename.endsWith(".webp")
          ? "image/webp"
          : filename.endsWith(".bmp")
            ? "image/bmp"
            : "image/png";
    image.src = `data:${mimeType};base64,${payload.image_base64}`;
  }
  if (meta) {
    meta.textContent = `Message #${payload.message_id} from ${payload.sender.username} at ${payload.timestamp}`;
  }
  setSignatureBadge(payload.signature_valid);
  setViewerDetails(JSON.stringify(payload, null, 2));
}

function attachTableHandlers() {
  document.body.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-message-id]");
    if (!button) return;
    try {
      if (button.dataset.action === "sent") {
        const result = await verifyMessage(button.dataset.messageId);
        setSignatureBadge(result.signature_valid);
        setViewerDetails(JSON.stringify(result, null, 2));
        addNotification(`Message ${button.dataset.messageId} verified`, "text-success");
        return;
      }

      await openMessage(button.dataset.messageId);
    } catch (error) {
      addNotification(error.message, "text-danger");
    }
  });
}

async function refreshAll() {
  await Promise.all([loadOnlineUsers(), loadInbox(), loadSent()]);
}

async function verifySelectedMessage() {
  if (!state.selectedMessageId) return;
  const result = await verifyMessage(state.selectedMessageId);
  setSignatureBadge(result.signature_valid);
}

function bindForms() {
  const logoutButton = document.getElementById("logout-button");
  const refreshInboxButton = document.getElementById("refresh-inbox");
  const adminDashboardButton = document.getElementById("admin-dashboard-button");
  const sendForm = document.getElementById("send-image-form");

  if (adminDashboardButton && state.currentUser?.role === "admin") {
    adminDashboardButton.classList.remove("hidden");
    adminDashboardButton.addEventListener("click", () => {
      window.location.href = "/admin.html";
    });
  }

  logoutButton?.addEventListener("click", () => {
    logout();
    window.location.href = "/login.html";
  });

  refreshInboxButton?.addEventListener("click", async () => {
    await refreshAll();
    addNotification("Inbox refreshed", "text-success");
  });

  sendForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorBox = document.getElementById("send-error");
    errorBox.textContent = "";
    const receiver = document.getElementById("receiver-select").value;
    const file = document.getElementById("image-file").files[0];
    try {
      const result = await sendImage(receiver, file);
      addNotification(`Image sent to ${receiver} (message ${result.message_id})`, "text-success");
      await refreshAll();
      await verifySelectedMessage();
    } catch (error) {
      errorBox.textContent = error.message;
      addNotification(error.message, "text-danger");
    }
  });
}

function connectWebSocket() {
  const token = localStorage.getItem("cipherframe_token");
  if (!token) {
    window.location.href = "/login.html";
    return;
  }

  const statusPill = document.getElementById("ws-status");
  state.socket = createChatSocket(token, {
    onOpen: () => {
      if (statusPill) {
        statusPill.textContent = "Online";
        statusPill.className = "status-pill";
      }
    },
    onClose: () => {
      if (statusPill) {
        statusPill.textContent = "Offline";
        statusPill.className = "status-pill neutral";
      }
    },
    onMessage: async (payload) => {
      const event = payload.event;
      const data = payload.data || {};
      if (event === "online_users") {
        renderOnlineUsers(data.users || []);
      }
      if (event === "user_connected") {
        addNotification(`${data.username} connected`, "text-success");
        await loadOnlineUsers();
      }
      if (event === "user_disconnected") {
        addNotification(`${data.username} disconnected`, "text-danger");
        await loadOnlineUsers();
      }
      if (event === "message_notification") {
        addNotification(`New image received from ${data.sender?.username || "unknown"}`, "text-success");
        await loadInbox();
      }
      if (event === "image_sent") {
        addNotification(`Image sent to ${data.receiver?.username || "unknown"}`);
        await loadSent();
      }
      if (event === "image_delivered") {
        addNotification(`Image delivered to ${data.receiver?.username || "unknown"}`, "text-success");
        await loadSent();
      }
      if (event === "signature_verification_failed") {
        addNotification("Signature verification failed", "text-danger");
        setSignatureBadge(false);
      }
    },
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  const currentUser = getCurrentUser();
  if (!localStorage.getItem("cipherframe_token") || !currentUser) {
    window.location.href = "/login.html";
    return;
  }

  state.currentUser = currentUser;
  const usernameNode = document.getElementById("current-username");
  if (usernameNode) {
    usernameNode.textContent = currentUser.username;
  }

  attachTableHandlers();
  bindForms();
  connectWebSocket();

  try {
    await refreshAll();
  } catch (error) {
    addNotification(error.message, "text-danger");
  }

  setSignatureBadge(null);
  setViewerDetails("Select a message to view details, signature status, and decrypted image.");
});