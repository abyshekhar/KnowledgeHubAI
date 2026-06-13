const API_BASE = "/api";

export async function api<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem("knowledgehub_token");
      localStorage.removeItem("knowledgehub_page");
      window.location.reload();
    }
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

