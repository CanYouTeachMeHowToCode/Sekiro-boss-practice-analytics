import { apiRequest } from "./client";
import type { Boss, BossSummary } from "../types";

export function getBosses(): Promise<BossSummary[]> {
  return apiRequest<BossSummary[]>("/bosses");
}

export function getBossById(bossId: string): Promise<Boss> {
  return apiRequest<Boss>(`/bosses/${bossId}`);
}
