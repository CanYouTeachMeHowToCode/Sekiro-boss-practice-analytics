import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { getBossById } from "../api/bosses";
import { getBossAnalytics, getBossAttempts, getBossProgression } from "../api/attempts";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/authContext";
import { bossLocation, bossName } from "../i18n/content";
import { formatPhase, useLanguage } from "../i18n/language";
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
  const { language, t } = useLanguage();
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
        <p>{t("loading")}</p>
      </main>
    );
  }

  if (state === "not-found") {
    return (
      <main className="page">
        <p>{t("boss.notFound")}</p>
        <Link to="/bosses">{t("boss.backToSelection")}</Link>
      </main>
    );
  }

  if (state === "error" || !boss || (loggedIn && !analytics)) {
    return (
      <main className="page">
        <p role="alert">{t("boss.loadError")}</p>
      </main>
    );
  }

  return (
    <main className="page">
      <Link to="/bosses" className="back-link">
        {t("boss.back")}
      </Link>

      <h1>{bossName(boss, language)}</h1>
      <p>{bossLocation(boss, language)}</p>

      {!analytics ? (
        <p className="login-prompt">
          <Link to="/login" state={{ from: location.pathname }}>
            {t("boss.loginPrompt.login")}
          </Link>
          {t("boss.loginPrompt.or")}
          <Link to="/register" state={{ from: location.pathname }}>
            {t("boss.loginPrompt.register")}
          </Link>
          {t("boss.loginPrompt.rest")}
        </p>
      ) : (
        <>
          <div className="stat-grid">
            <div>
              <h3>{t("boss.stat.attempts")}</h3>
              <p>{analytics.total_attempts}</p>
            </div>
            <div>
              <h3>{t("boss.stat.bestResult")}</h3>
              <p>{analytics.best_phase !== null ? formatPhase(analytics.best_phase, language) : "—"}</p>
            </div>
            <div>
              <h3>{t("boss.stat.defeated")}</h3>
              <p>{analytics.defeated ? t("yes") : t("no")}</p>
            </div>
            <div>
              <h3>{t("boss.stat.firstVictory")}</h3>
              <p>
                {analytics.attempts_until_first_victory !== null
                  ? t("boss.attemptNumber", { n: analytics.attempts_until_first_victory })
                  : t("boss.notYet")}
              </p>
            </div>
          </div>

          <button className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? t("cancel") : t("boss.recordAttempt")}
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
