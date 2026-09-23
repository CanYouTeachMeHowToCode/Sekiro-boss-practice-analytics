import { apiRequest } from "./client";
import type { SekiroAnalytics } from "../types";

export function getSekiroAnalytics(): Promise<SekiroAnalytics> {
  return apiRequest<SekiroAnalytics>("/sekiro/analytics");
}
