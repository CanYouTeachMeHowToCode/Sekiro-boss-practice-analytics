import { ApiError, apiRequest } from "./client";
import type { Credentials, User } from "../types";

export function register(credentials: Credentials): Promise<User> {
  return apiRequest<User>("/auth/register", { method: "POST", body: JSON.stringify(credentials) });
}

export function login(credentials: Credentials): Promise<User> {
  return apiRequest<User>("/auth/login", { method: "POST", body: JSON.stringify(credentials) });
}

export function logout(): Promise<void> {
  return apiRequest<void>("/auth/logout", { method: "POST" });
}

/** The logged-in user, or null when there is no valid session. */
export async function getCurrentUser(): Promise<User | null> {
  try {
    return await apiRequest<User>("/auth/me");
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}
