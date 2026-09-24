import type { ReactElement } from "react";
import { vi } from "vitest";
import type { User } from "../types";
import { AuthContext } from "./authContext";
import type { AuthState } from "./authContext";

export const testUser: User = { id: "1", username: "wolf" };

/** Wraps `ui` in a fixed auth state for component tests, without touching the network. */
export function withAuth(ui: ReactElement, overrides: Partial<AuthState> = {}): ReactElement {
  const value: AuthState = {
    status: "ready",
    user: testUser,
    login: vi.fn().mockResolvedValue(undefined),
    register: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
  return <AuthContext.Provider value={value}>{ui}</AuthContext.Provider>;
}
