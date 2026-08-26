import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import RecordAttemptForm from "./RecordAttemptForm";
import * as attemptsApi from "../api/attempts";
import { ApiError } from "../api/client";
import type { Attempt, Boss } from "../types";

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
        { id: "thrust-attack", name: "Thrust Attack", move_type: "thrust", description: null, recommended_response: null },
      ],
    },
    {
      phase_number: 2,
      name: "Phase 2",
      moves: [
        { id: "floating-passage", name: "Floating Passage", move_type: "combo", description: null, recommended_response: null },
      ],
    },
  ],
};

function stubbedAttempt(overrides: Partial<Attempt>): Attempt {
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

describe("RecordAttemptForm", () => {
  it("submits a failed attempt with the selected phase and move", async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    vi.mocked(attemptsApi.createAttempt).mockResolvedValue(
      stubbedAttempt({ phase_reached: 2, failure_move_id: "floating-passage" })
    );

    render(<RecordAttemptForm boss={boss} onSuccess={onSuccess} onCancel={vi.fn()} />);

    await user.selectOptions(screen.getByLabelText(/phase reached/i), "2");
    await user.selectOptions(screen.getByLabelText(/what ended this attempt/i), "floating-passage");
    await user.click(screen.getByRole("button", { name: /save attempt/i }));

    await waitFor(() =>
      expect(attemptsApi.createAttempt).toHaveBeenCalledWith("genichiro-ashina", {
        result: "failed",
        phase_reached: 2,
        failure_move_id: "floating-passage",
        failure_category: null,
        notes: "",
      })
    );
    expect(onSuccess).toHaveBeenCalled();
  });

  it("hides the failure cause field and omits it from the payload when the result is Victory", async () => {
    const user = userEvent.setup();
    vi.mocked(attemptsApi.createAttempt).mockResolvedValue(stubbedAttempt({ result: "victory" }));

    render(<RecordAttemptForm boss={boss} onSuccess={vi.fn()} onCancel={vi.fn()} />);

    await user.click(screen.getByLabelText(/victory/i));

    expect(screen.queryByLabelText(/what ended this attempt/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /save attempt/i }));

    await waitFor(() =>
      expect(attemptsApi.createAttempt).toHaveBeenCalledWith("genichiro-ashina", {
        result: "victory",
        phase_reached: 1,
        failure_move_id: null,
        failure_category: null,
        notes: "",
      })
    );
  });

  it("records Not Sure as a failure category instead of requiring a move", async () => {
    const user = userEvent.setup();
    vi.mocked(attemptsApi.createAttempt).mockResolvedValue(stubbedAttempt({ failure_category: "not_sure" }));

    render(<RecordAttemptForm boss={boss} onSuccess={vi.fn()} onCancel={vi.fn()} />);

    await user.selectOptions(screen.getByLabelText(/what ended this attempt/i), "__not_sure__");
    await user.click(screen.getByRole("button", { name: /save attempt/i }));

    await waitFor(() =>
      expect(attemptsApi.createAttempt).toHaveBeenCalledWith(
        "genichiro-ashina",
        expect.objectContaining({ failure_move_id: null, failure_category: "not_sure" })
      )
    );
  });

  it("allows saving a failed attempt without picking a failure cause at all", async () => {
    const user = userEvent.setup();
    vi.mocked(attemptsApi.createAttempt).mockResolvedValue(stubbedAttempt({}));

    render(<RecordAttemptForm boss={boss} onSuccess={vi.fn()} onCancel={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /save attempt/i }));

    await waitFor(() =>
      expect(attemptsApi.createAttempt).toHaveBeenCalledWith(
        "genichiro-ashina",
        expect.objectContaining({ failure_move_id: null, failure_category: null })
      )
    );
  });

  it("shows the backend's error message when saving fails", async () => {
    const user = userEvent.setup();
    vi.mocked(attemptsApi.createAttempt).mockRejectedValue(new ApiError(400, "Phase 5 does not exist"));

    render(<RecordAttemptForm boss={boss} onSuccess={vi.fn()} onCancel={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /save attempt/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Phase 5 does not exist");
  });
});
