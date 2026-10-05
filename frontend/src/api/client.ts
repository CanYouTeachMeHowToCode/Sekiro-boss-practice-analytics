export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const UNAUTHORIZED_EVENT = "api:unauthorized";

function getBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? "/api";
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${getBaseUrl()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      // Lets the auth state notice an expired or ended session from any request.
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body?.detail ?? res.statusText);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}
