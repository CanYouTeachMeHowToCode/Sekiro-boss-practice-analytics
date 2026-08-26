import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { createAttempt } from "../api/attempts";
import { ApiError } from "../api/client";
import type { AttemptResult, Boss, CreateAttemptRequest } from "../types";

const OTHER = "__other__";
const NOT_SURE = "__not_sure__";

interface RecordAttemptFormProps {
  boss: Boss;
  onSuccess: () => void;
  onCancel: () => void;
}

export default function RecordAttemptForm({ boss, onSuccess, onCancel }: RecordAttemptFormProps) {
  const [result, setResult] = useState<AttemptResult>("failed");
  const [phaseReached, setPhaseReached] = useState<number>(boss.phases[0]?.phase_number ?? 1);
  const [failureChoice, setFailureChoice] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const movesForPhase = boss.phases.find((p) => p.phase_number === phaseReached)?.moves ?? [];

  useEffect(() => {
    if (failureChoice === "" || failureChoice === OTHER || failureChoice === NOT_SURE) return;
    if (!movesForPhase.some((m) => m.id === failureChoice)) {
      setFailureChoice("");
    }
    // Only re-validate when the phase changes, not on every failureChoice edit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phaseReached]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const payload: CreateAttemptRequest =
      result === "victory"
        ? { result, phase_reached: null, failure_move_id: null, failure_category: null, notes }
        : {
            result,
            phase_reached: phaseReached,
            failure_move_id: failureChoice && failureChoice !== OTHER && failureChoice !== NOT_SURE ? failureChoice : null,
            failure_category: failureChoice === OTHER ? "other" : failureChoice === NOT_SURE ? "not_sure" : null,
            notes,
          };

    try {
      await createAttempt(boss.id, payload);
      setSubmitting(false);
      onSuccess();
    } catch (err) {
      setSubmitting(false);
      setError(err instanceof ApiError ? err.message : "Failed to save attempt.");
    }
  }

  return (
    <form className="record-attempt-form" onSubmit={handleSubmit}>
      <h3>Record Attempt — {boss.name}</h3>

      <fieldset>
        <legend>Result</legend>
        <label>
          <input
            type="radio"
            name="result"
            value="failed"
            checked={result === "failed"}
            onChange={() => setResult("failed")}
          />
          Failed
        </label>
        <label>
          <input
            type="radio"
            name="result"
            value="victory"
            checked={result === "victory"}
            onChange={() => setResult("victory")}
          />
          Victory
        </label>
      </fieldset>

      {result === "failed" && (
        <label>
          Phase Reached
          <select value={phaseReached} onChange={(e) => setPhaseReached(Number(e.target.value))}>
            {boss.phases.map((phase) => (
              <option key={phase.phase_number} value={phase.phase_number}>
                {phase.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {result === "failed" && (
        <label>
          What ended this attempt?
          <select value={failureChoice} onChange={(e) => setFailureChoice(e.target.value)}>
            <option value="">Select…</option>
            {movesForPhase.map((move) => (
              <option key={move.id} value={move.id}>
                {move.name}
              </option>
            ))}
            <option value={OTHER}>Other</option>
            <option value={NOT_SURE}>Not Sure</option>
          </select>
        </label>
      )}

      <label>
        Notes
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" rows={2} />
      </label>

      {error && <p role="alert">{error}</p>}

      <div className="form-actions">
        <button type="button" className="btn" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Saving…" : "Save Attempt"}
        </button>
      </div>
    </form>
  );
}
