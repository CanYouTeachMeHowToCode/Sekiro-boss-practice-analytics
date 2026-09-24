import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { getBossById } from "../api/bosses";
import { getBossAnalytics, getBossAttempts, getBossProgression } from "../api/attempts";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/authContext";
import type { Attempt, Boss, BossAnalytics, ProgressionPoint } from "../types";
import RecordAttemptForm from "../components/RecordAttemptForm";
import AnalyticsPanel from "../components/AnalyticsPanel";
import AttemptHistory from "../components/AttemptHistory";
import MovesetReference from "../components/MovesetReference";
import ProgressionChart from "../components/ProgressionChart";

type LoadState = "loading" | "error" | "not-found" | "ready";

export default function BossDashboardPage() {
  const { bossId } = useParams<{ bossId: string }>();
  const { status: authStatus, user } = useAuth();
  const location = useLocation();
  const loggedIn = user !== null;
  const [boss, setBoss] = useState<Boss | null>(null);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [analytics, setAnalytics] = useState<BossAnalytics | null>(null);
  const [progression, setProgression] = useState<ProgressionPoint[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [showForm, setShowForm] = useState(false);

  const loadAttemptData = useCallback(async (id: string) => {
    const [attemptsData, analyticsData, progressionData] = await Promise.all([
      getBossAttempts(id),
      getBossAnalytics(id),
      getBossProgression(id),
    ]);
    setAttempts(attemptsData);
    setAnalytics(analyticsData);
    setProgression(progressionData);
  }, []);

  useEffect(() => {
    if (!bossId || authStatus === "loading") return;
    let cancelled = false;
    setState("loading");

    // Visitors only get the public boss data; attempts and analytics need a login.
    const load = loggedIn
      ? Promise.all([
          getBossById(bossId),
          getBossAttempts(bossId),
          getBossAnalytics(bossId),
          getBossProgression(bossId),
        ])
      : getBossById(bossId).then((b) => [b, [] as Attempt[], null, [] as ProgressionPoint[]] as const);

    load
      .then(([bossData, attemptsData, analyticsData, progressionData]) => {
        if (cancelled) return;
        setBoss(bossData);
        setAttempts(attemptsData);
        setAnalytics(analyticsData);
        setProgression(progressionData);
        setState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setState(err instanceof ApiError && err.status === 404 ? "not-found" : "error");
      });

    return () => {
      cancelled = true;
    };
  }, [bossId, authStatus, loggedIn]);

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
        <Link to="/bosses">Back to boss selection</Link>
      </main>
    );
  }

  if (state === "error" || !boss || (loggedIn && !analytics)) {
    return (
      <main className="page">
        <p role="alert">Failed to load boss dashboard.</p>
      </main>
    );
  }

  return (
    <main className="page">
      <Link to="/bosses" className="back-link">
        ← Choose a different boss
      </Link>

      <h1>{boss.name}</h1>
      {boss.name_zh && <p className="boss-name-zh">{boss.name_zh}</p>}
      <p>{boss.location}</p>

      {!analytics ? (
        <p className="login-prompt">
          <Link to="/login" state={{ from: location.pathname }}>
            Log in
          </Link>{" "}
          or{" "}
          <Link to="/register" state={{ from: location.pathname }}>
            create an account
          </Link>{" "}
          to record attempts and see your analytics for this boss.
        </p>
      ) : (
        <>
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
            <div>
              <h3>First Victory</h3>
              <p>
                {analytics.attempts_until_first_victory !== null
                  ? `Attempt #${analytics.attempts_until_first_victory}`
                  : "Not yet"}
              </p>
            </div>
          </div>

          <button className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "+ Record Attempt"}
          </button>

          {showForm && (
            <RecordAttemptForm boss={boss} onSuccess={handleAttemptSaved} onCancel={() => setShowForm(false)} />
          )}

          <ProgressionChart boss={boss} points={progression} />
          <AnalyticsPanel boss={boss} analytics={analytics} />
          <AttemptHistory boss={boss} attempts={attempts} />
        </>
      )}
      <MovesetReference boss={boss} />
    </main>
  );
}
