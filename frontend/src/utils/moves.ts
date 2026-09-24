import type { Attempt, Boss, BossMove } from "../types";

/** "English · 中文" when a Chinese name exists, for places that show a move as plain text. */
export function formatMoveName(name: string, nameZh: string | null | undefined): string {
  return nameZh ? `${name} · ${nameZh}` : name;
}

export function moveLabel(move: Pick<BossMove, "name" | "name_zh">): string {
  return formatMoveName(move.name, move.name_zh);
}

export function getMoveName(boss: Boss, moveId: string | null): string | null {
  if (!moveId) return null;
  for (const phase of boss.phases) {
    const move = phase.moves.find((m) => m.id === moveId);
    if (move) return moveLabel(move);
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
