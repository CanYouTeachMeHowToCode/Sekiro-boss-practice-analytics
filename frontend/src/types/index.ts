export type AttemptResult = "failed" | "victory";

export type FailureCategory = "not_sure" | "other";

export interface BossMove {
  id: string;
  name: string;
  move_type: string;
  description: string | null;
  recommended_response: string | null;
}

export interface BossPhase {
  phase_number: number;
  name: string;
  moves: BossMove[];
}

export interface Boss {
  id: string;
  name: string;
  game: string;
  location: string;
  phases: BossPhase[];
}

export interface BossSummary {
  id: string;
  name: string;
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

export interface BossAnalytics {
  total_attempts: number;
  defeated: boolean;
  best_phase: number | null;
  main_bottleneck_phase: number | null;
  most_common_failure_move: string | null;
  failure_by_phase: Record<string, number>;
  failure_by_move: Record<string, number>;
}
