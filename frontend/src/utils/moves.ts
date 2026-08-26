import type { Attempt, Boss } from "../types";

export function getMoveName(boss: Boss, moveId: string | null): string | null {
  if (!moveId) return null;
  for (const phase of boss.phases) {
    const move = phase.moves.find((m) => m.id === moveId);
    if (move) return move.name;
  }
  return moveId;
}

export function getFailureLabel(boss: Boss, attempt: Attempt): string {
  if (attempt.result === "victory") return "Victory";
  if (attempt.failure_move_id) return getMoveName(boss, attempt.failure_move_id) ?? attempt.failure_move_id;
  if (attempt.failure_category === "not_sure") return "Not Sure";
  if (attempt.failure_category === "other") return "Other";
  return "Unknown";
}
