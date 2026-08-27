import { describe, expect, it } from "vitest";
import { getFailureLabel, getMoveName } from "./moves";
import type { Attempt, Boss } from "../types";

const boss: Boss = {
  id: "genichiro-ashina",
  name: "Genichiro Ashina",
  game: "sekiro",
  location: "Ashina Castle",
  phases: [
    {
      phase_number: 1,
      name: "Phase 1",
      moves: [
        { id: "thrust-attack", name: "Thrust Attack", move_type: "thrust", description: null, counter: null },
      ],
    },
    {
      phase_number: 3,
      name: "Phase 3",
      moves: [
        { id: "lightning-attack", name: "Lightning Attack", move_type: "lightning", description: null, counter: null },
      ],
    },
  ],
};

function makeAttempt(overrides: Partial<Attempt>): Attempt {
  return {
    id: "attempt-001",
    boss_id: boss.id,
    timestamp: "2026-08-24T21:00:00Z",
    result: "failed",
    phase_reached: 1,
    failure_move_id: null,
    failure_category: null,
    notes: "",
    ...overrides,
  };
}

describe("getMoveName", () => {
  it("finds a move regardless of which phase it belongs to", () => {
    expect(getMoveName(boss, "lightning-attack")).toBe("Lightning Attack");
  });

  it("returns null when no move id is given", () => {
    expect(getMoveName(boss, null)).toBeNull();
  });

  it("falls back to the raw id when the move can't be found", () => {
    expect(getMoveName(boss, "unknown-move")).toBe("unknown-move");
  });
});

describe("getFailureLabel", () => {
  it("labels a victory", () => {
    expect(getFailureLabel(boss, makeAttempt({ result: "victory" }))).toBe("Victory");
  });

  it("labels a known failure move by its display name", () => {
    expect(getFailureLabel(boss, makeAttempt({ failure_move_id: "thrust-attack" }))).toBe("Thrust Attack");
  });

  it("labels a not_sure failure", () => {
    expect(getFailureLabel(boss, makeAttempt({ failure_category: "not_sure" }))).toBe("Not Sure");
  });

  it("labels an other failure", () => {
    expect(getFailureLabel(boss, makeAttempt({ failure_category: "other" }))).toBe("Other");
  });
});
