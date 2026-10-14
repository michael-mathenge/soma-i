import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});
let csrfRequest;
let csrfToken;

async function accountCacheReady() {
  const worker = navigator.serviceWorker?.controller;
  if (!worker) return;
  await new Promise((resolve, reject) => {
    const channel = new MessageChannel();
    const timer = setTimeout(() => {
      channel.port1.close();
      reject(
        new Error(
          "Reload after the offline shell updates before using accounts.",
        ),
      );
    }, 3000);
    channel.port1.onmessage = ({ data }) => {
      clearTimeout(timer);
      channel.port1.close();
      if (data === "public-shell-v2") resolve();
      else reject(new Error("Offline shell update required."));
    };
    worker.postMessage("account-cache-version", [channel.port2]);
  });
}

api.interceptors.request.use(async (config) => {
  if (config.url.startsWith("/account/")) await accountCacheReady();
  if (!["get", "head", "options"].includes(config.method)) {
    // Read the current cookie because Django rotates it on login/logout.
    const cookie = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    if (!cookie && !csrfToken) {
      csrfRequest ||= api.get("/csrf/").finally(() => {
        csrfRequest = null;
      });
      csrfToken = (await csrfRequest).data.csrf_token;
    }
    config.headers["X-CSRFToken"] = cookie
      ? decodeURIComponent(cookie[1])
      : csrfToken;
  }
  return config;
});
api.interceptors.response.use(
  (response) => {
    if (response.data?.csrf_token) csrfToken = response.data.csrf_token;
    return response;
  },
  (error) => {
    if (error.response?.status === 403) csrfToken = null;
    return Promise.reject(error);
  },
);
export default api;
