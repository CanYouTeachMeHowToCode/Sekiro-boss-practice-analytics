import { UNAUTHORIZED_EVENT, apiRequest, getBaseUrl } from "./client";
import type { Recording, RecordingReport } from "../types";

/** The backend's upload limit and file types (recording_service.py). Checked here too, so that a file the backend
 * would refuse is not sent first; the backend still checks both. */
export const MAX_UPLOAD_BYTES = 2 * 1024 ** 3;
export const VIDEO_EXTENSIONS = [".mp4", ".mkv", ".mov"];

/** Why an upload did not go through: the backend's code ("unsupported_type", "too_large", "empty"), or "network",
 * "aborted" or "unknown". */
export class UploadError extends Error {
  code: string;
  status: number;

  constructor(code: string, status = 0) {
    super(code);
    this.name = "UploadError";
    this.code = code;
    this.status = status;
  }
}

export function listRecordings(): Promise<Recording[]> {
  return apiRequest<Recording[]>("/recordings");
}

/** The recording with its status and, once it is analysed, its failures. */
export function getRecordingReport(recordingId: string): Promise<RecordingReport> {
  return apiRequest<RecordingReport>(`/recordings/${encodeURIComponent(recordingId)}`);
}

export function deleteRecording(recordingId: string): Promise<void> {
  return apiRequest<void>(`/recordings/${encodeURIComponent(recordingId)}`, { method: "DELETE" });
}

/** A failure's short clip, for a <video> element; the session cookie goes with it. */
export function clipUrl(recordingId: string, failureId: string): string {
  return `${getBaseUrl()}/recordings/${encodeURIComponent(recordingId)}/failures/${encodeURIComponent(failureId)}/clip`;
}

/** Where a video is uploaded: the request body is the file itself, its name in the query. */
export function uploadUrl(filename: string): string {
  return `${getBaseUrl()}/recordings?filename=${encodeURIComponent(filename)}`;
}

/** The code the backend would refuse the file with, or null. */
export function uploadProblem(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!VIDEO_EXTENSIONS.some((ext) => name.endsWith(ext))) return "unsupported_type";
  if (file.size === 0) return "empty";
  if (file.size > MAX_UPLOAD_BYTES) return "too_large";
  return null;
}

/** Sends the file and reports the fraction sent so far. XMLHttpRequest rather than fetch, because fetch cannot
 * report upload progress. Rejects with an UploadError. */
export function uploadRecording(
  file: File,
  onProgress: (fraction: number) => void,
  signal?: AbortSignal
): Promise<Recording> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new UploadError("aborted"));
      return;
    }
    const xhr = new XMLHttpRequest();
    xhr.open("POST", uploadUrl(file.name));
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) onProgress(event.loaded / event.total);
    };
    xhr.onload = () => {
      if (xhr.status === 201) {
        resolve(JSON.parse(xhr.responseText) as Recording);
        return;
      }
      if (xhr.status === 401) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
      // nginx answers an oversized body with its own HTML page; the backend with {"detail": {"code": ...}}
      let code = xhr.status === 413 ? "too_large" : "unknown";
      try {
        const body = JSON.parse(xhr.responseText);
        if (typeof body?.detail?.code === "string") code = body.detail.code;
      } catch {
        // not JSON
      }
      reject(new UploadError(code, xhr.status));
    };
    xhr.onerror = () => reject(new UploadError("network"));
    xhr.onabort = () => reject(new UploadError("aborted"));
    signal?.addEventListener("abort", () => xhr.abort(), { once: true });
    xhr.send(file);
  });
}
