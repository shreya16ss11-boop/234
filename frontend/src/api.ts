const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8006";

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const payload = await response.json();
      message = typeof payload.detail === "string" ? payload.detail : message;
    } catch {
      // Keep the fallback message when the API does not return JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
