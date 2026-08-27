import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AttemptHistory from "./AttemptHistory";
import type { Attempt, Boss } from "../types";

const boss: Boss = {
  id: "genichiro-ashina",
  name: "Genichiro Ashina",
  game: "sekiro",
  location: "Ashina Castle",
  phases: [
    {
      phase_number: 2,
      name: "Phase 2",
      moves: [
        { id: "floating-passage", name: "Floating Passage", move_type: "combo", description: null, counter: null },
      ],
    },
  ],
};

const attempts: Attempt[] = [
  {
    id: "attempt-002",
    boss_id: boss.id,
    timestamp: "2026-08-24T21:15:00Z",
    result: "failed",
    phase_reached: 2,
    failure_move_id: "floating-passage",
    failure_category: null,
    notes: "",
  },
  {
    id: "attempt-001",
    boss_id: boss.id,
    timestamp: "2026-08-24T21:00:00Z",
    result: "victory",
    phase_reached: 3,
    failure_move_id: null,
    failure_category: null,
    notes: "",
  },
];

describe("AttemptHistory", () => {
  it("shows the failure move's display name and phase for a failed attempt", () => {
    render(<AttemptHistory boss={boss} attempts={attempts} />);

    expect(screen.getByText("Floating Passage")).toBeInTheDocument();
    expect(screen.getByText(/failed — phase 2/i)).toBeInTheDocument();
  });

  it("shows Victory without a failure cause for a successful attempt", () => {
    render(<AttemptHistory boss={boss} attempts={attempts} />);

    expect(screen.getByText("Victory")).toBeInTheDocument();
  });

  it("shows a placeholder when there is no history yet", () => {
    render(<AttemptHistory boss={boss} attempts={[]} />);

    expect(screen.getByText(/no attempts recorded yet/i)).toBeInTheDocument();
  });
});
