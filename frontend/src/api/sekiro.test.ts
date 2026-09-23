import { afterEach, describe, expect, it, vi } from "vitest";
import { getSekiroAnalytics } from "./sekiro";

describe("sekiro api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("getSekiroAnalytics fetches the game-level analytics endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await getSekiroAnalytics();

    expect(fetchMock).toHaveBeenCalledWith("/api/sekiro/analytics", expect.any(Object));
  });
});
