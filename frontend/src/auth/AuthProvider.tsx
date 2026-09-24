import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import * as authApi from "../api/auth";
import { UNAUTHORIZED_EVENT } from "../api/client";
import type { Credentials, User } from "../types";
import { AuthContext } from "./authContext";
import type { AuthState } from "./authContext";

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthState["status"]>("loading");

  useEffect(() => {
    let cancelled = false;
    authApi
      .getCurrentUser()
      .catch(() => null)
      .then((current) => {
        if (cancelled) return;
        setUser(current);
        setStatus("ready");
      });

    const handleUnauthorized = () => setUser(null);
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      cancelled = true;
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, []);

  const login = useCallback(async (credentials: Credentials) => {
    setUser(await authApi.login(credentials));
  }, []);

  const register = useCallback(async (credentials: Credentials) => {
    setUser(await authApi.register(credentials));
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(() => ({ status, user, login, register, logout }), [status, user, login, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
