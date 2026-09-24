import { afterEach, describe, expect, it, vi } from "vitest";
import { getCurrentUser, login } from "./auth";
import { UNAUTHORIZED_EVENT } from "./client";

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("auth api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts credentials to the login endpoint", async () => {
    const fetchMock = mockFetch(200, { id: "1", username: "wolf" });

    const user = await login({ username: "wolf", password: "kusabimaru" });

    expect(user).toEqual({ id: "1", username: "wolf" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ username: "wolf", password: "kusabimaru" }) })
    );
  });

  it("returns null from getCurrentUser when there is no session", async () => {
    mockFetch(401, { detail: "Not logged in" });

    await expect(getCurrentUser()).resolves.toBeNull();
  });

  it("still throws other errors from getCurrentUser", async () => {
    mockFetch(500, { detail: "boom" });

    await expect(getCurrentUser()).rejects.toThrow("boom");
  });

  it("announces a 401 from any request so the app can drop the stale login", async () => {
    mockFetch(401, { detail: "Not logged in" });
    const listener = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);

    await getCurrentUser();

    window.removeEventListener(UNAUTHORIZED_EVENT, listener);
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
