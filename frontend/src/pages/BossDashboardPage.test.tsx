import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import BossDashboardPage from "./BossDashboardPage";
import * as bossesApi from "../api/bosses";
import * as attemptsApi from "../api/attempts";
import { ApiError } from "../api/client";
import type { Boss, BossAnalytics } from "../types";

vi.mock("../api/bosses");
vi.mock("../api/attempts");

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
  ],
};

const emptyAnalytics: BossAnalytics = {
  total_attempts: 0,
  defeated: false,
  best_phase: null,
  main_bottleneck_phase: null,
  most_common_failure_move: null,
  failure_by_phase: {},
  failure_by_move: {},
};

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={["/bosses/genichiro-ashina"]}>
      <Routes>
        <Route path="/bosses/:bossId" element={<BossDashboardPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("BossDashboardPage", () => {
  it("loads the boss, attempts, and analytics and renders the dashboard", async () => {
    vi.mocked(bossesApi.getBossById).mockResolvedValue(boss);
    vi.mocked(attemptsApi.getBossAttempts).mockResolvedValue([]);
    vi.mocked(attemptsApi.getBossAnalytics).mockResolvedValue(emptyAnalytics);

    renderDashboard();

    expect(await screen.findByRole("heading", { name: "Genichiro Ashina" })).toBeInTheDocument();
    expect(screen.getByText("Ashina Castle")).toBeInTheDocument();
  });

  it("shows a not-found message for an unknown boss", async () => {
    vi.mocked(bossesApi.getBossById).mockRejectedValue(new ApiError(404, "Boss not found"));
    vi.mocked(attemptsApi.getBossAttempts).mockResolvedValue([]);
    vi.mocked(attemptsApi.getBossAnalytics).mockResolvedValue(emptyAnalytics);

    renderDashboard();

    expect(await screen.findByText(/boss not found/i)).toBeInTheDocument();
  });

  it("refreshes attempts and analytics after recording a new attempt", async () => {
    const user = userEvent.setup();
    vi.mocked(bossesApi.getBossById).mockResolvedValue(boss);
    vi.mocked(attemptsApi.getBossAttempts)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: "attempt-001",
          boss_id: boss.id,
          timestamp: "2026-08-24T21:00:00Z",
          result: "failed",
          phase_reached: 1,
          failure_move_id: "thrust-attack",
          failure_category: null,
          notes: "",
        },
      ]);
    vi.mocked(attemptsApi.getBossAnalytics)
      .mockResolvedValueOnce(emptyAnalytics)
      .mockResolvedValueOnce({
        total_attempts: 1,
        defeated: false,
        best_phase: 1,
        main_bottleneck_phase: 1,
        most_common_failure_move: "thrust-attack",
        failure_by_phase: { "1": 1 },
        failure_by_move: { "thrust-attack": 1 },
      });
    vi.mocked(attemptsApi.createAttempt).mockResolvedValue({
      id: "attempt-001",
      boss_id: boss.id,
      timestamp: "2026-08-24T21:00:00Z",
      result: "failed",
      phase_reached: 1,
      failure_move_id: "thrust-attack",
      failure_category: null,
      notes: "",
    });

    renderDashboard();
    await screen.findByRole("heading", { name: "Genichiro Ashina" });
    expect(screen.getByText(/no attempts recorded yet/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /record attempt/i }));
    await user.click(screen.getByRole("button", { name: /save attempt/i }));

    await waitFor(() => expect(attemptsApi.getBossAttempts).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/failed — phase 1/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save attempt/i })).not.toBeInTheDocument();
  });
});
