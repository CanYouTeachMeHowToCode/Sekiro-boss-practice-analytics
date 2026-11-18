import { apiRequest, getBaseUrl } from "./client";
import type { AdminRecording, AdminRecordingReport } from "../types";

/** The read-only admin view: every user's recordings. For anyone but an admin the backend answers 404. */
export function listAdminRecordings(): Promise<AdminRecording[]> {
  return apiRequest<AdminRecording[]>("/admin/recordings");
}

export function getAdminRecordingReport(recordingId: string): Promise<AdminRecordingReport> {
  return apiRequest<AdminRecordingReport>(`/admin/recordings/${encodeURIComponent(recordingId)}`);
}

/** A failure's clip of any user's recording, for a <video> element. */
export function adminClipUrl(recordingId: string, failureId: string): string {
  return `${getBaseUrl()}/admin/recordings/${encodeURIComponent(recordingId)}/failures/${encodeURIComponent(failureId)}/clip`;
}
