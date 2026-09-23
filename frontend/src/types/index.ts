export type AttemptResult = "failed" | "victory";

export type FailureCategory = "not_sure" | "other";

export interface BossMove {
  id: string;
  name: string;
  move_type: string;
  description: string | null;
  telegraph: string | null;
  counter: string | null;
  common_mistakes: string | null;
}

export interface BossPhase {
  phase_number: number;
  name: string;
  moves: BossMove[];
}

export interface Boss {
  id: string;
  name: string;
  name_zh: string | null;
  game: string;
  location: string;
  phases: BossPhase[];
  source_name: string | null;
  source_url: string | null;
}

export interface BossSummary {
  id: string;
  name: string;
  name_zh: string | null;
  location: string;
}

export interface Attempt {
  id: string;
  boss_id: string;
  timestamp: string;
  result: AttemptResult;
  phase_reached: number;
  failure_move_id: string | null;
  failure_category: FailureCategory | null;
  notes: string;
}

export interface CreateAttemptRequest {
  result: AttemptResult;
  phase_reached: number | null;
  failure_move_id: string | null;
  failure_category: FailureCategory | null;
  notes: string;
}

export interface RecentAnalytics {
  /** How many recent attempts were requested. */
  window_size: number;
  /** How many attempts the window actually covers; fewer than window_size early on. */
  total_attempts: number;
  main_bottleneck_phase: number | null;
  most_common_failure_move: string | null;
  failure_by_phase: Record<string, number>;
  failure_by_move: Record<string, number>;
}

/** Top-level statistics cover the full attempt history; `recent` covers the latest attempts. */
export interface BossAnalytics {
  total_attempts: number;
  defeated: boolean;
  best_phase: number | null;
  main_bottleneck_phase: number | null;
  most_common_failure_move: string | null;
  failure_by_phase: Record<string, number>;
  failure_by_move: Record<string, number>;
  /** Attempts up to and including the first victory; null if never defeated. */
  attempts_until_first_victory: number | null;
  recent: RecentAnalytics;
}

export interface ProgressionPoint {
  /** 1 for the boss's first attempt, counting up chronologically. */
  attempt_number: number;
  attempt_id: string;
  timestamp: string;
  result: AttemptResult;
  phase_reached: number;
  failure_move_id: string | null;
}
