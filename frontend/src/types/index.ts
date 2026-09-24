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
  /** Chinese versions of the text above: translations of the sourced English text. */
  description_zh: string | null;
  telegraph_zh: string | null;
  counter_zh: string | null;
  common_mistakes_zh: string | null;
  /** Chinese name: from a Chinese wiki ("wiki", see name_zh_source_url) or a translation. */
  name_zh: string | null;
  name_zh_source: ChineseNameSource | null;
  name_zh_source_url: string | null;
}

export type ChineseNameSource = "wiki" | "translation";

export interface BossPhase {
  phase_number: number;
  name: string;
  name_zh: string | null;
  moves: BossMove[];
}

export interface Boss {
  id: string;
  name: string;
  name_zh: string | null;
  game: string;
  location: string;
  location_zh: string | null;
  phases: BossPhase[];
  source_name: string | null;
  source_url: string | null;
}

export interface BossSummary {
  id: string;
  name: string;
  name_zh: string | null;
  location: string;
  location_zh: string | null;
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

export interface BossComparisonRow {
  id: string;
  name: string;
  name_zh: string | null;
  total_phases: number;
  attempts: number;
  best_phase: number | null;
  defeated: boolean;
  attempts_until_first_victory: number | null;
  last_attempt_at: string | null;
}

export interface RecentAttempt {
  attempt_id: string;
  boss_id: string;
  boss_name: string;
  timestamp: string;
  result: AttemptResult;
  phase_reached: number;
  failure_move_id: string | null;
  failure_move_name: string | null;
  failure_move_name_zh: string | null;
  boss_name_zh: string | null;
  failure_category: FailureCategory | null;
}

export interface SekiroAnalytics {
  total_bosses: number;
  bosses_attempted: number;
  bosses_defeated: number;
  total_attempts: number;
  /** Boss ids with the most attempts; more than one when tied. */
  most_practiced_bosses: string[];
  /** The highest attempts_until_first_victory among defeated bosses. */
  most_attempts_to_defeat: number | null;
  /** Defeated boss ids whose first victory took most_attempts_to_defeat attempts. */
  bosses_requiring_most_attempts: string[];
  recent_window_days: number;
  attempts_in_recent_window: number;
  /** Newest first, across all bosses. */
  recent_attempts: RecentAttempt[];
  bosses: BossComparisonRow[];
}

export interface User {
  id: string;
  username: string;
  /** Interface language saved in the account; null until the user picks one. */
  preferred_language: "en" | "zh" | null;
}

export interface Credentials {
  username: string;
  password: string;
}
