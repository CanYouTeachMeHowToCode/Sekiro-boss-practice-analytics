import { afterEach, describe, expect, it, vi } from "vitest";
import { getBossById, getBosses } from "./bosses";

describe("bosses api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("getBosses fetches the boss list endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [{ id: "genichiro-ashina", name: "Genichiro Ashina", location: "Ashina Castle" }],
    });
    vi.stubGlobal("fetch", fetchMock);

    const bosses = await getBosses();

    expect(fetchMock).toHaveBeenCalledWith("/api/bosses", expect.any(Object));
    expect(bosses).toHaveLength(1);
  });

  it("getBossById fetches the detail endpoint for the given boss id", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: "genichiro-ashina",
        name: "Genichiro Ashina",
        game: "sekiro",
        location: "Ashina Castle",
        phases: [],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await getBossById("genichiro-ashina");

    expect(fetchMock).toHaveBeenCalledWith("/api/bosses/genichiro-ashina", expect.any(Object));
  });
});
