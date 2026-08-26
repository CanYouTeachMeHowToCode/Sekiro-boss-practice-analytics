import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getBossById } from "../api/bosses";
import { getBossAnalytics, getBossAttempts } from "../api/attempts";
import { ApiError } from "../api/client";
import type { Attempt, Boss, BossAnalytics } from "../types";
import RecordAttemptForm from "../components/RecordAttemptForm";
import AnalyticsPanel from "../components/AnalyticsPanel";
import AttemptHistory from "../components/AttemptHistory";
import MovesetReference from "../components/MovesetReference";

type LoadState = "loading" | "error" | "not-found" | "ready";

export default function BossDashboardPage() {
  const { bossId } = useParams<{ bossId: string }>();
  const [boss, setBoss] = useState<Boss | null>(null);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [analytics, setAnalytics] = useState<BossAnalytics | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [showForm, setShowForm] = useState(false);

  const loadAttemptData = useCallback(async (id: string) => {
    const [attemptsData, analyticsData] = await Promise.all([getBossAttempts(id), getBossAnalytics(id)]);
    setAttempts(attemptsData);
    setAnalytics(analyticsData);
  }, []);

  useEffect(() => {
    if (!bossId) return;
    let cancelled = false;
    setState("loading");

    Promise.all([getBossById(bossId), getBossAttempts(bossId), getBossAnalytics(bossId)])
      .then(([bossData, attemptsData, analyticsData]) => {
        if (cancelled) return;
        setBoss(bossData);
        setAttempts(attemptsData);
        setAnalytics(analyticsData);
        setState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setState(err instanceof ApiError && err.status === 404 ? "not-found" : "error");
      });

    return () => {
      cancelled = true;
    };
  }, [bossId]);

  async function handleAttemptSaved() {
    setShowForm(false);
    if (bossId) {
      await loadAttemptData(bossId);
    }
  }

  if (state === "loading") {
    return (
      <main className="page">
        <p>Loading…</p>
      </main>
    );
  }

  if (state === "not-found") {
    return (
      <main className="page">
        <p>Boss not found.</p>
        <Link to="/">Back to boss selection</Link>
      </main>
    );
  }

  if (state === "error" || !boss || !analytics) {
    return (
      <main className="page">
        <p role="alert">Failed to load boss dashboard.</p>
      </main>
    );
  }

  return (
    <main className="page">
      <Link to="/" className="back-link">
        ← Choose a different boss
      </Link>

      <h1>{boss.name}</h1>
      <p>{boss.location}</p>

      <div className="stat-grid">
        <div>
          <h3>Attempts</h3>
          <p>{analytics.total_attempts}</p>
        </div>
        <div>
          <h3>Best Result</h3>
          <p>{analytics.best_phase !== null ? `Phase ${analytics.best_phase}` : "—"}</p>
        </div>
        <div>
          <h3>Defeated</h3>
          <p>{analytics.defeated ? "Yes" : "No"}</p>
        </div>
      </div>

      <button className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>
        {showForm ? "Cancel" : "+ Record Attempt"}
      </button>

      {showForm && (
        <RecordAttemptForm boss={boss} onSuccess={handleAttemptSaved} onCancel={() => setShowForm(false)} />
      )}

      <AnalyticsPanel boss={boss} analytics={analytics} />
      <AttemptHistory boss={boss} attempts={attempts} />
      <MovesetReference boss={boss} />
    </main>
  );
}
