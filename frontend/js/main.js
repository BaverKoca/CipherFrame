// Client-side status script for the Cipher Frame frontend shell.

document.addEventListener("DOMContentLoaded", () => {
  const yearElement = document.getElementById("year");
  const healthLabel = document.getElementById("health-label");
  const healthDot = document.getElementById("health-dot");
  const healthTime = document.getElementById("health-time");
  const statusDetail = document.getElementById("status-detail");

  if (yearElement) {
    yearElement.textContent = String(new Date().getFullYear());
  }

  const updateStatus = (label, tone, detail) => {
    if (healthLabel) {
      healthLabel.textContent = label;
    }
    if (healthDot) {
      healthDot.style.background = tone;
      healthDot.style.boxShadow = `0 0 0 0 ${tone}66`;
    }
    if (statusDetail && detail) {
      statusDetail.textContent = detail;
    }
    if (healthTime) {
      healthTime.textContent = new Date().toLocaleString();
    }
  };

  fetch("/health")
    .then(async (response) => {
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || "Health endpoint returned an error.");
      }
      updateStatus(
        `${payload.application} is online`,
        "#34d399",
        "The backend is reachable and ready for future encryption workflows."
      );
      console.info("Cipher Frame health check:", payload);
    })
    .catch((error) => {
      updateStatus(
        "Backend status unavailable",
        "#f59e0b",
        "The frontend shell loaded, but the API health check could not be completed."
      );
      console.warn("Cipher Frame health check failed:", error);
    });
});
