import { localeFor } from "../i18n/language";
import { messages } from "../i18n/messages";
import type { Language, MessageKey, Translate } from "../i18n/language";
import type { Recording, RecordingStatus } from "../types";

/** How often a page asks again about a recording the worker has not finished with. */
export const LIST_POLL_MS = 5000;
export const REPORT_POLL_MS = 3000;

/** Statuses the worker has not finished with: pages showing them check again. */
const PENDING: RecordingStatus[] = ["uploaded", "checking", "queued", "processing"];

export function isPending(status: RecordingStatus): boolean {
  return PENDING.includes(status);
}

/** Whole percent of a 0–1 progress, never above 100. */
export function percent(fraction: number): number {
  return Math.min(100, Math.max(0, Math.floor(fraction * 100)));
}

/** A moment in the video, to the tenth of a second: 4:43.8. */
export function formatClock(seconds: number): string {
  const tenths = Math.round(seconds * 10);
  const minutes = Math.floor(tenths / 600);
  const rest = (tenths % 600) / 10;
  return `${minutes}:${rest.toFixed(1).padStart(4, "0")}`;
}

/** A video's length: 5:07. */
export function formatDuration(seconds: number): string {
  const total = Math.round(seconds);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function formatUploadTime(timestamp: string, language: Language): string {
  return new Date(timestamp).toLocaleString(localeFor(language), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatSize(bytes: number): string {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  if (bytes >= 1024 ** 2) return `${Math.round(bytes / 1024 ** 2)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function statusLabel(recording: Recording, t: Translate): string {
  if (recording.status === "processing") {
    return t("recordingStatus.processing", { percent: percent(recording.progress) });
  }
  return t(`recordingStatus.${recording.status}` as MessageKey);
}

function known(key: string): key is MessageKey {
  return key in messages.en;
}

/** The sentence explaining a reject code; codes this frontend does not know get a general one. */
export function rejectReason(code: string | null, t: Translate): string {
  const key = `reject.${code}`;
  return t(known(key) ? key : "reject.unknown");
}

/** The message for an upload error code. */
export function uploadErrorMessage(code: string, t: Translate): string {
  const key = `upload.error.${code}`;
  return t(known(key) ? key : "upload.error.unknown");
}

/** "A, B or C" / "A、B或C". */
export function alternatives(names: string[], t: Translate): string {
  if (names.length <= 1) return names.join("");
  return t("report.alternatives", { rest: names.slice(0, -1).join(t("listSeparator")), last: names[names.length - 1] });
}
