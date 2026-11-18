import { afterEach, describe, expect, it, vi } from "vitest";
import { UNAUTHORIZED_EVENT } from "./client";
import {
  MAX_UPLOAD_BYTES,
  UploadError,
  clipUrl,
  deleteRecording,
  getRecordingReport,
  listRecordings,
  uploadProblem,
  uploadRecording,
} from "./recordings";

/** Just enough of XMLHttpRequest to drive uploadRecording. */
class FakeXHR {
  static last: FakeXHR;
  upload: { onprogress: ((event: { lengthComputable: boolean; loaded: number; total: number }) => void) | null } = {
    onprogress: null,
  };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onabort: (() => void) | null = null;
  status = 0;
  responseText = "";
  method = "";
  url = "";
  headers: Record<string, string> = {};
  body: unknown;

  constructor() {
    FakeXHR.last = this;
  }

  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }

  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }

  send(body: unknown) {
    this.body = body;
  }

  abort() {
    this.onabort?.();
  }

  respond(status: number, body: string) {
    this.status = status;
    this.responseText = body;
    this.onload?.();
  }
}

function video(name = "fight.mp4", size = 10) {
  return new File([new Uint8Array(size)], name, { type: "video/mp4" });
}

describe("recordings api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists, reads and deletes the user's recordings", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await listRecordings();
    await getRecordingReport("7");
    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => undefined });
    await deleteRecording("7");

    expect(fetchMock.mock.calls.map(([url, init]) => [url, init?.method ?? "GET"])).toEqual([
      ["/api/recordings", "GET"],
      ["/api/recordings/7", "GET"],
      ["/api/recordings/7", "DELETE"],
    ]);
  });

  it("points a clip at the failure's clip endpoint", () => {
    expect(clipUrl("7", "12")).toBe("/api/recordings/7/failures/12/clip");
  });

  it("finds the files the backend would refuse before sending them", () => {
    expect(uploadProblem(video("fight.MKV"))).toBeNull();
    expect(uploadProblem(video("notes.txt"))).toBe("unsupported_type");
    expect(uploadProblem(video("fight.mp4", 0))).toBe("empty");
    const big = video();
    Object.defineProperty(big, "size", { value: MAX_UPLOAD_BYTES + 1 });
    expect(uploadProblem(big)).toBe("too_large");
  });

  it("uploads the file as the request body and reports the progress", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXHR);
    const onProgress = vi.fn();
    const file = video("my fight.mp4");

    const done = uploadRecording(file, onProgress);
    const xhr = FakeXHR.last;
    expect([xhr.method, xhr.url, xhr.body]).toEqual(["POST", "/api/recordings?filename=my%20fight.mp4", file]);
    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 5, total: 10 });
    xhr.respond(201, JSON.stringify({ id: "7", status: "uploaded" }));

    await expect(done).resolves.toMatchObject({ id: "7", status: "uploaded" });
    expect(onProgress).toHaveBeenCalledWith(0.5);
  });

  it("rejects with the backend's code, or too_large for nginx's own 413 page", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXHR);

    const refused = uploadRecording(video(), vi.fn());
    FakeXHR.last.respond(400, JSON.stringify({ detail: { code: "unsupported_type", message: "..." } }));
    await expect(refused).rejects.toMatchObject({ code: "unsupported_type", status: 400 });

    const tooBig = uploadRecording(video(), vi.fn());
    FakeXHR.last.respond(413, "<html>413 Request Entity Too Large</html>");
    await expect(tooBig).rejects.toMatchObject({ code: "too_large", status: 413 });

    const lost = uploadRecording(video(), vi.fn());
    FakeXHR.last.onerror?.();
    await expect(lost).rejects.toThrow(UploadError);
  });

  it("announces an ended session on a 401", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXHR);
    const listener = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);

    const upload = uploadRecording(video(), vi.fn());
    FakeXHR.last.respond(401, JSON.stringify({ detail: "Not authenticated" }));

    await expect(upload).rejects.toMatchObject({ code: "unknown", status: 401 });
    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener(UNAUTHORIZED_EVENT, listener);
  });

  it("stops the upload when its signal is aborted", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXHR);
    const controller = new AbortController();

    const upload = uploadRecording(video(), vi.fn(), controller.signal);
    controller.abort();

    await expect(upload).rejects.toMatchObject({ code: "aborted" });
  });
});
