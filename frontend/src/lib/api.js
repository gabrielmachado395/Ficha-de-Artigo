import { Capacitor, CapacitorHttp } from "@capacitor/core";

function normalizeBase(baseUrl) {
  return String(baseUrl ?? "").replace(/\/+$/, "");
}

export function getApiBaseUrl() {
  const fromEnv = String(import.meta.env.VITE_API_BASE_URL ?? "").trim();
  return fromEnv ? normalizeBase(fromEnv) : "/api";
}

export function apiUrl(pathname) {
  const base = getApiBaseUrl();
  const path = String(pathname ?? "").trim();

  if (!path) return base;
  if (/^https?:\/\//i.test(path)) return path;

  const withLeadingSlash = path.startsWith("/") ? path : `/${path}`;
  return `${normalizeBase(base)}${withLeadingSlash}`;
}

let desktopTokenPromise = null;

async function getDesktopApiToken() {
  if (typeof window === "undefined") return "";
  const fn = window?.electronAPI?.getApiToken;
  if (typeof fn !== "function") return "";

  if (!desktopTokenPromise) {
    desktopTokenPromise = Promise.resolve()
      .then(() => fn())
      .then((t) => String(t || ""))
      .catch(() => "");
  }
  return desktopTokenPromise;
}

function isNativePlatform() {
  try {
    return typeof window !== "undefined" && Capacitor?.isNativePlatform?.();
  } catch {
    return false;
  }
}

function toPlainHeaders(headers) {
  if (!headers) return {};

  if (headers instanceof Headers) {
    const obj = {};
    headers.forEach((value, key) => {
      obj[key] = value;
    });
    return obj;
  }

  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }

  if (typeof headers === "object") return headers;
  return {};
}

async function capacitorFetch(url, init) {
  const method = String(init?.method ?? "GET").toUpperCase();
  const headers = toPlainHeaders(init?.headers);

  let data = undefined;
  if (init?.body != null) {
    if (typeof init.body === "string") {
      const contentType = String(headers["Content-Type"] || headers["content-type"] || "");
      if (contentType.includes("application/json")) {
        try {
          data = JSON.parse(init.body);
        } catch {
          data = init.body;
        }
      } else {
        data = init.body;
      }
    } else {
      data = init.body;
    }
  }

  const resp = await CapacitorHttp.request({
    url,
    method,
    headers,
    data,
  });

  const status = Number(resp?.status ?? 0);
  const ok = status >= 200 && status < 300;
  const responseHeaders = new Headers(resp?.headers ?? {});
  const responseData = resp?.data;

  return {
    ok,
    status,
    headers: responseHeaders,
    async json() {
      return responseData;
    },
    async text() {
      if (typeof responseData === "string") return responseData;
      try {
        return JSON.stringify(responseData);
      } catch {
        return String(responseData ?? "");
      }
    },
  };
}

export async function apiFetch(pathname, init) {
  const url = apiUrl(pathname);
  if (isNativePlatform()) {
    return capacitorFetch(url, init);
  }

  const headers = new Headers(init?.headers || {});
  const token = await getDesktopApiToken();
  if (token) headers.set("X-Etiquetas-Token", token);

  return fetch(url, {
    ...(init || {}),
    headers,
  });
}
