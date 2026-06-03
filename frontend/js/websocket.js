// WebSocket service for Cipher Frame real-time chat updates.

function buildSocketUrl(token) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/chat?token=${encodeURIComponent(token)}`;
}

function createChatSocket(token, handlers = {}) {
  let socket = null;
  let reconnectTimer = null;
  let reconnectAttempts = 0;
  let manualClose = false;

  const connect = () => {
    socket = new WebSocket(buildSocketUrl(token));

    socket.onopen = () => {
      reconnectAttempts = 0;
      if (handlers.onOpen) handlers.onOpen();
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (handlers.onMessage) handlers.onMessage(payload);
      } catch (error) {
        console.warn("Cipher Frame websocket parse error:", error);
      }
    };

    socket.onclose = (event) => {
      if (handlers.onClose) handlers.onClose();
      if (!manualClose && event.code !== 1008) {
        scheduleReconnect();
      }
    };

    socket.onerror = (error) => {
      if (handlers.onError) handlers.onError(error);
    };
  };

  const scheduleReconnect = () => {
    reconnectAttempts += 1;
    const delay = Math.min(1000 * 2 ** reconnectAttempts, 10000);
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, delay);
  };

  const send = (data) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(data);
    }
  };

  const close = () => {
    manualClose = true;
    clearTimeout(reconnectTimer);
    if (socket) {
      socket.close();
    }
  };

  connect();

  return { close, send };
}

export { createChatSocket };