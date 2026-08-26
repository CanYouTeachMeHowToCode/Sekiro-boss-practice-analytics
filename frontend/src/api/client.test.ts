import { afterEach, describe, expect, it, vi } from "vitest";
import { apiRequest, ApiError } from "./client";

describe("apiRequest", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON on a successful response", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ hello: "world" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiRequest<{ hello: string }>("/bosses");

    expect(result).toEqual({ hello: "world" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/bosses",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      })
    );
  });

  it("throws an ApiError carrying the backend's detail message on failure", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Boss 'unknown' not found" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/bosses/unknown")).rejects.toThrow(ApiError);
    await expect(apiRequest("/bosses/unknown")).rejects.toThrow("Boss 'unknown' not found");
  });

  it("falls back to the status text when the error body has no detail", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => {
        throw new Error("not json");
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/bosses")).rejects.toThrow("Internal Server Error");
  });
});
