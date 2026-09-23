import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ProgressionChart from "./ProgressionChart";
import type { Boss, ProgressionPoint } from "../types";

const boss: Boss = {
  id: "owl-father",
  name: "Owl (Father)",
  name_zh: null,
  game: "sekiro",
  location: "Hirata Estate",
  source_name: null,
  source_url: null,
  phases: [
    { phase_number: 1, name: "Phase 1", moves: [] },
    { phase_number: 2, name: "Phase 2", moves: [] },
  ],
};

function point(attempt_number: number, phase_reached: number, result: "failed" | "victory" = "failed"): ProgressionPoint {
  return {
    attempt_number,
    attempt_id: String(attempt_number + 100),
    timestamp: "2026-09-22T23:00:00Z",
    result,
    phase_reached,
    failure_move_id: null,
  };
}

describe("ProgressionChart", () => {
  it("plots one point per attempt, marking victories", () => {
    render(<ProgressionChart boss={boss} points={[point(1, 1), point(2, 2), point(3, 2, "victory")]} />);

    expect(screen.getByRole("img", { name: "Phase reached across 3 attempts, 1 of them victories" })).toBeInTheDocument();
    expect(screen.getByLabelText("Attempt 1: Phase 1, failed")).toBeInTheDocument();
    expect(screen.getByLabelText("Attempt 2: Phase 2, failed")).toBeInTheDocument();
    expect(screen.getByLabelText("Attempt 3: Phase 2, victory")).toHaveClass("victory");
  });

  it("places later phases higher on the chart", () => {
    render(<ProgressionChart boss={boss} points={[point(1, 1), point(2, 2)]} />);

    const phase1 = Number(screen.getByLabelText("Attempt 1: Phase 1, failed").getAttribute("cy"));
    const phase2 = Number(screen.getByLabelText("Attempt 2: Phase 2, failed").getAttribute("cy"));
    expect(phase2).toBeLessThan(phase1);
  });

  it("labels a phase row for every phase of the boss", () => {
    render(<ProgressionChart boss={boss} points={[point(1, 1)]} />);

    expect(screen.getByText("P1")).toBeInTheDocument();
    expect(screen.getByText("P2")).toBeInTheDocument();
  });

  it("thins out attempt-number labels on long histories", () => {
    const points = Array.from({ length: 40 }, (_, i) => point(i + 1, 1));
    render(<ProgressionChart boss={boss} points={points} />);

    expect(screen.getAllByLabelText(/^Attempt \d+:/)).toHaveLength(40);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.queryByText("2")).not.toBeInTheDocument();
  });

  it("shows a placeholder before any attempts", () => {
    render(<ProgressionChart boss={boss} points={[]} />);

    expect(screen.getByText(/record an attempt to see your progression/i)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
