import { afterEach, describe, expect, it, vi } from "vitest";
import { createAttempt, getBossAnalytics, getBossAttempts } from "./attempts";

describe("attempts api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("createAttempt POSTs the request body to the boss's attempts endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: "attempt-001" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await createAttempt("genichiro-ashina", {
      result: "failed",
      phase_reached: 2,
      failure_move_id: "floating-passage",
      failure_category: null,
      notes: "",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bosses/genichiro-ashina/attempts",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          result: "failed",
          phase_reached: 2,
          failure_move_id: "floating-passage",
          failure_category: null,
          notes: "",
        }),
      })
    );
  });

  it("getBossAttempts fetches the boss's attempt history endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await getBossAttempts("genichiro-ashina");

    expect(fetchMock).toHaveBeenCalledWith("/api/bosses/genichiro-ashina/attempts", expect.any(Object));
  });

  it("getBossAnalytics fetches the boss's analytics endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await getBossAnalytics("genichiro-ashina");

    expect(fetchMock).toHaveBeenCalledWith("/api/bosses/genichiro-ashina/analytics", expect.any(Object));
  });
});
