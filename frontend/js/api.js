// API service layer for Cipher Frame.

const API_BASE = "";

function getToken() {
  return localStorage.getItem("cipherframe_token") || "";
}

function setToken(token) {
  localStorage.setItem("cipherframe_token", token);
}

function clearToken() {
  localStorage.removeItem("cipherframe_token");
  localStorage.removeItem("cipherframe_user");
}

function getCurrentUser() {
  const raw = localStorage.getItem("cipherframe_user");
  return raw ? JSON.parse(raw) : null;
}

function setCurrentUser(user) {
  localStorage.setItem("cipherframe_user", JSON.stringify(user));
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();

  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", headers.get("Content-Type") || "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    payload = await response.text();
  }

  if (!response.ok) {
    const message = typeof payload === "string" ? payload : payload?.detail || payload?.message || "Request failed.";
    throw new Error(message);
  }

  return payload;
}

async function login(username, password) {
  const tokenResponse = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(tokenResponse.access_token);
  const user = await request("/api/auth/me");
  setCurrentUser(user);
  return { token: tokenResponse.access_token, user };
}

async function register(username, email, password) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}

async function getMe() { return request("/api/auth/me"); }
async function getOnlineUsers() { return request("/api/chat/online-users"); }
async function getInbox() { return request("/api/messages/inbox"); }
async function getSent() { return request("/api/messages/sent"); }
async function getAdminOverview() { return request("/api/admin/overview"); }
async function getAdminUsers() { return request("/api/admin/users"); }
async function updateAdminUserStatus(userId, isActive) {
  return request(`/api/admin/users/${userId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ is_active: isActive }),
  });
}
async function getAdminMessages() { return request("/api/admin/messages"); }
async function getAdminLogs(params = {}) {
  const query = new URLSearchParams();
  if (params.level) query.set("level", params.level);
  if (params.event_type) query.set("event_type", params.event_type);
  if (params.limit) query.set("limit", String(params.limit));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request(`/api/admin/logs${suffix}`);
}
async function getAdminKeys() { return request("/api/admin/keys"); }
async function rotateAdminUserKeys(userId) { return request(`/api/admin/users/${userId}/rotate-keys`, { method: "POST" }); }

async function sendImage(receiverUsername, file) {
  const formData = new FormData();
  formData.append("receiver_username", receiverUsername);
  formData.append("file", file);
  return request("/api/messages/send-image", {
    method: "POST",
    body: formData,
  });
}

async function getMessage(messageId) { return request(`/api/messages/${messageId}`); }
async function verifyMessage(messageId) { return request(`/api/messages/${messageId}/verify`); }

function logout() {
  clearToken();
}

export {
  clearToken,
  getCurrentUser,
  getInbox,
  getAdminKeys,
  getAdminLogs,
  getAdminMessages,
  getAdminOverview,
  getAdminUsers,
  getMe,
  getMessage,
  getOnlineUsers,
  getSent,
  login,
  logout,
  register,
  rotateAdminUserKeys,
  sendImage,
  setCurrentUser,
  setToken,
  updateAdminUserStatus,
  verifyMessage,
};