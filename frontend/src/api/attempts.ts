import { apiRequest } from "./client";
import type { Attempt, BossAnalytics, CreateAttemptRequest } from "../types";

export function getBossAttempts(bossId: string): Promise<Attempt[]> {
  return apiRequest<Attempt[]>(`/bosses/${bossId}/attempts`);
}

export function createAttempt(bossId: string, req: CreateAttemptRequest): Promise<Attempt> {
  return apiRequest<Attempt>(`/bosses/${bossId}/attempts`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function getBossAnalytics(bossId: string): Promise<BossAnalytics> {
  return apiRequest<BossAnalytics>(`/bosses/${bossId}/analytics`);
}
