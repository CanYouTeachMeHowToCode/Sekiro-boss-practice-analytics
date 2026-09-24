import { createContext, useContext } from "react";
import type { Credentials, User } from "../types";

export interface AuthState {
  /** "loading" until the first check of the session cookie finishes. */
  status: "loading" | "ready";
  user: User | null;
  login: (credentials: Credentials) => Promise<void>;
  register: (credentials: Credentials) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside <AuthProvider>");
  return auth;
}
