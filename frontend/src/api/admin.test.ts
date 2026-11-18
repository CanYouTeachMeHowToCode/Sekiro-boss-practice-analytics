import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./client";
import { adminClipUrl, getAdminRecordingReport, listAdminRecordings } from "./admin";

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

describe("admin api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists every recording and gets any report from the admin paths", async () => {
    const fetchMock = mockFetch(200, []);
    await listAdminRecordings();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/admin/recordings");

    await getAdminRecordingReport("7");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/admin/recordings/7");
  });

  it("builds the clip URL on the admin path", () => {
    expect(adminClipUrl("7", "3")).toBe("/api/admin/recordings/7/failures/3/clip");
  });

  it("rejects with the backend's 404 for anyone but an admin", async () => {
    mockFetch(404, { detail: "Not Found" });
    await expect(listAdminRecordings()).rejects.toEqual(new ApiError(404, "Not Found"));
  });
});
