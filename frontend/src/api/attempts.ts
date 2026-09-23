import { apiRequest } from "./client";
import type { Attempt, BossAnalytics, CreateAttemptRequest, ProgressionPoint } from "../types";

export function getBossAttempts(bossId: string): Promise<Attempt[]> {
  return apiRequest<Attempt[]>(`/bosses/${bossId}/attempts`);
}

export function createAttempt(bossId: string, req: CreateAttemptRequest): Promise<Attempt> {
  return apiRequest<Attempt>(`/bosses/${bossId}/attempts`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/** `recentWindow` is how many recent attempts to compare against the full history (backend default 10). */
export function getBossAnalytics(bossId: string, recentWindow?: number): Promise<BossAnalytics> {
  const query = recentWindow === undefined ? "" : `?recent=${recentWindow}`;
  return apiRequest<BossAnalytics>(`/bosses/${bossId}/analytics${query}`);
}

export function getBossProgression(bossId: string): Promise<ProgressionPoint[]> {
  return apiRequest<ProgressionPoint[]>(`/bosses/${bossId}/progression`);
}
