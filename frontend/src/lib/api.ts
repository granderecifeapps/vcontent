export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function parseError(response: Response) {
  try {
    const body = await response.json();
    if (Array.isArray(body.errors) && body.errors.length) return String(body.errors[0]);
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* resposta sem json */
  }
  return "Não foi possível concluir a operação.";
}

export async function api<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("X-Requested-With", "vcontent");
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`/backend${path}`, { ...options, headers, credentials: "include" });
  if (
    response.status === 401 &&
    retry &&
    !path.startsWith("/api/auth/login") &&
    !path.startsWith("/api/auth/refresh") &&
    !path.startsWith("/api/auth/forgot-password") &&
    !path.startsWith("/api/auth/reset-password")
  ) {
    const refreshed = await fetch("/backend/api/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: { "X-Requested-With": "vcontent" },
    });
    if (refreshed.ok) return api<T>(path, options, false);
  }
  if (!response.ok) throw new ApiError(await parseError(response), response.status);
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

const DIRECT_API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

async function uploadToken() {
  const grant = await api<{ access_token: string }>("/api/auth/upload-token", { method: "POST" });
  return grant.access_token;
}

export async function uploadForm<T>(path: string, body: FormData): Promise<T> {
  if (!DIRECT_API) return api<T>(path, { method: "POST", body });
  const response = await fetch(`${DIRECT_API}${path}`, {
    method: "POST",
    body,
    headers: { Authorization: `Bearer ${await uploadToken()}`, "X-Requested-With": "vcontent" },
  });
  if (!response.ok) throw new ApiError(await parseError(response), response.status);
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export async function fetchBinary(path: string): Promise<Blob> {
  if (!DIRECT_API) {
    const response = await fetch(`/backend${path}`, { credentials: "include" });
    if (!response.ok) throw new ApiError("Não foi possível abrir o arquivo.", response.status);
    return response.blob();
  }
  const response = await fetch(`${DIRECT_API}${path}`, {
    headers: { Authorization: `Bearer ${await uploadToken()}` },
  });
  if (!response.ok) throw new ApiError("Não foi possível abrir o arquivo.", response.status);
  return response.blob();
}

export function uploadWithProgress(path: string, file: File, onProgress: (value: number) => void) {
  return (async () => {
    const token = DIRECT_API ? await uploadToken() : "";
    const target = DIRECT_API ? `${DIRECT_API}${path}` : `/backend${path}`;
    return new Promise<unknown>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", target);
      if (!DIRECT_API) xhr.withCredentials = true;
      xhr.setRequestHeader("X-Requested-With", "vcontent");
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.responseText ? JSON.parse(xhr.responseText) : undefined);
          return;
        }
        let message = "Falha no upload.";
        try {
          message = JSON.parse(xhr.responseText).detail || message;
        } catch {
          /* mantém a mensagem padrão */
        }
        reject(new ApiError(message, xhr.status));
      };
      xhr.onerror = () => reject(new ApiError("Falha no upload.", 0));
      const body = new FormData();
      body.append("file", file);
      xhr.send(body);
    });
  })();
}
