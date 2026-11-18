import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { adminClipUrl, getAdminRecordingReport } from "../api/admin";
import { getBossById } from "../api/bosses";
import { ApiError } from "../api/client";
import { clipUrl, deleteRecording, getRecordingReport } from "../api/recordings";
import { useAuth } from "../auth/authContext";
import LoginPrompt from "../components/LoginPrompt";
import { formatPhase, useLanguage } from "../i18n/language";
import type { Language, MessageKey, Translate } from "../i18n/language";
import type { AdminRecordingReport, Boss, Recording, RecordingFailure, RecordingReport } from "../types";
import { getMoveName } from "../utils/moves";
import {
  REPORT_POLL_MS,
  alternatives,
  formatClock,
  formatDuration,
  formatUploadTime,
  isPending,
  percent,
  rejectReason,
} from "../utils/recordings";

/** How many of an unsure failure's candidates are named. */
const CANDIDATES_SHOWN = 3;

const FAILURE_TYPES = ["damage", "posture_break", "death"] as const;

type LoadState = "loading" | "error" | "not-found" | "ready";

function moveLabel(boss: Boss | null, moveId: string, language: Language): string {
  return (boss && getMoveName(boss, moveId, language)) ?? moveId;
}

function StatusMessage({ recording, t }: { recording: Recording; t: Translate }) {
  switch (recording.status) {
    case "done":
      return null;
    case "rejected":
      return (
        <div className="recording-rejected" role="alert">
          <p>{t("report.rejected")}</p>
          <p>{rejectReason(recording.reject_code, t)}</p>
        </div>
      );
    case "failed":
      return <p role="alert">{t("report.status.failed")}</p>;
    case "processing":
      return (
        <div className="recording-progress">
          <progress max={1} value={recording.progress} />
          <p>{t("report.status.processing", { percent: percent(recording.progress) })}</p>
        </div>
      );
    default:
      return <p className="recording-waiting">{t(`report.status.${recording.status}` as MessageKey)}</p>;
  }
}

/** Where the browser gets a failure's clip: the owner's or the admin's path. */
type ClipSource = (failureId: string) => string;

function FailureItem({ clipSrc, failure, boss }: { clipSrc: ClipSource; failure: RecordingFailure; boss: Boss | null }) {
  const { language, t } = useLanguage();
  const [showClip, setShowClip] = useState(false);
  const candidates = failure.candidates.slice(0, CANDIDATES_SHOWN).map((c) => moveLabel(boss, c.move_id, language));
  let move: string;
  if (failure.sure && failure.move_id) move = moveLabel(boss, failure.move_id, language);
  else if (candidates.length > 0) move = t("report.failure.unsure", { moves: alternatives(candidates, t) });
  else move = t("report.failure.unsureNoCandidates");

  return (
    <li className={`failure-item ${failure.sure ? "sure" : "unsure"}`}>
      <p className="failure-heading">
        <span className="failure-time">{formatClock(failure.time_s)}</span>
        <span>{formatPhase(failure.phase, language)}</span>
        <span>{t(`failureType.${failure.type}`)}</span>
      </p>
      <p className="failure-move">{move}</p>
      {failure.events.length > 1 && (
        <p className="failure-events">
          {t("report.failure.events", {
            events: failure.events
              .map((e) => `${t(`failureType.${e.type}`)} ${formatClock(e.time_s)}`)
              .join(t("listSeparator")),
          })}
        </p>
      )}
      {failure.has_clip && (
        <>
          <button type="button" className="btn btn-small" onClick={() => setShowClip((v) => !v)}>
            {showClip ? t("report.hideClip") : t("report.playClip")}
          </button>
          {showClip && (
            <video className="failure-clip" src={clipSrc(failure.id)} controls autoPlay preload="metadata" />
          )}
        </>
      )}
    </li>
  );
}

function FailureReport({ report, boss, clipSrc }: { report: RecordingReport; boss: Boss | null; clipSrc: ClipSource }) {
  const { language, t } = useLanguage();
  const { failures, by_move: byMove } = report;
  const count = (type: string) => failures.filter((f) => f.type === type).length;

  return (
    <>
      <div className="stat-grid">
        <div>
          <h3>{t("report.stat.failures")}</h3>
          <p>{failures.length}</p>
        </div>
        {FAILURE_TYPES.map((type) => (
          <div key={type}>
            <h3>{t(`report.stat.${type}`)}</h3>
            <p>{count(type)}</p>
          </div>
        ))}
        <div>
          <h3>{t("report.stat.uncertain")}</h3>
          <p>{report.uncertain}</p>
        </div>
      </div>

      {failures.length === 0 ? (
        <p>{t("report.noFailures")}</p>
      ) : (
        <>
          <section className="failures-by-move">
            <h2>{t("report.byMove")}</h2>
            <p className="form-hint">{t("report.byMove.note")}</p>
            {byMove.length === 0 ? (
              <p>{t("report.byMove.empty")}</p>
            ) : (
              <div className="table-scroll">
                <table className="failure-breakdown">
                  <thead>
                    <tr>
                      <th scope="col">{t("report.col.move")}</th>
                      {FAILURE_TYPES.map((type) => (
                        <th key={type} scope="col">
                          {t(`report.stat.${type}`)}
                        </th>
                      ))}
                      <th scope="col">{t("report.col.total")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {byMove.map((m) => (
                      <tr key={m.move_id}>
                        <td>{moveLabel(boss, m.move_id, language)}</td>
                        <td>{m.damage}</td>
                        <td>{m.posture_break}</td>
                        <td>{m.death}</td>
                        <td>{m.total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {report.uncertain > 0 && <p>{t("report.byMove.uncertain", { count: report.uncertain })}</p>}
          </section>

          <section className="failure-list">
            <h2>{t("report.failures")}</h2>
            <ol>
              {failures.map((f) => (
                <FailureItem key={f.id} clipSrc={clipSrc} failure={f} boss={boss} />
              ))}
            </ol>
          </section>
        </>
      )}
    </>
  );
}

/** One recording: where it is in the checks and analysis, and once analysed, its failure report. With `admin`, the
 * read-only admin view of any user's recording (owner decision, 2026-11-18): no delete, a link back to the admin
 * list, and a page that does not exist for anyone but an admin. */
export default function RecordingReportPage({ admin = false }: { admin?: boolean }) {
  const { recordingId } = useParams<{ recordingId: string }>();
  const { status: authStatus, user } = useAuth();
  const { language, t } = useLanguage();
  const navigate = useNavigate();
  const [report, setReport] = useState<RecordingReport | AdminRecordingReport | null>(null);
  const [boss, setBoss] = useState<Boss | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [deleteFailed, setDeleteFailed] = useState(false);
  const bossId = report?.recording.boss_id;

  const allowed = admin ? user?.is_admin === true : user !== null;

  useEffect(() => {
    if (!allowed || !recordingId) return;
    let cancelled = false;
    let timer: number | undefined;
    let loaded = false;
    setState("loading");
    const fetchReport = admin ? getAdminRecordingReport : getRecordingReport;
    const load = () => {
      fetchReport(recordingId)
        .then((data) => {
          if (cancelled) return;
          loaded = true;
          setReport(data);
          setState("ready");
          if (isPending(data.recording.status)) timer = window.setTimeout(load, REPORT_POLL_MS);
        })
        .catch((err) => {
          if (cancelled) return;
          if (err instanceof ApiError && err.status === 404) setState("not-found");
          else if (loaded) timer = window.setTimeout(load, REPORT_POLL_MS);
          else setState("error");
        });
    };
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [allowed, admin, recordingId]);

  // the boss's moveset names the moves; without it the report still shows, with the moves' ids
  useEffect(() => {
    if (!bossId) return;
    let cancelled = false;
    getBossById(bossId)
      .then((data) => {
        if (!cancelled) setBoss(data);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [bossId]);

  async function handleDelete(recording: Recording) {
    if (!window.confirm(t("recordings.deleteConfirm", { file: recording.filename }))) return;
    setDeleteFailed(false);
    try {
      await deleteRecording(recording.id);
      navigate("/recordings");
    } catch {
      setDeleteFailed(true);
    }
  }

  if (authStatus !== "loading" && admin && !allowed) {
    return (
      <main className="page">
        <p role="alert">{t("admin.notFound")}</p>
      </main>
    );
  }

  if (authStatus === "loading" || (user && state === "loading")) {
    return (
      <main className="page">
        <p>{t("loading")}</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="page">
        <LoginPrompt rest="recordings.loginPrompt" />
      </main>
    );
  }

  const back = admin ? { to: "/admin", label: t("admin.back") } : { to: "/recordings", label: t("report.back") };

  if (state === "not-found" || state === "error" || !report) {
    return (
      <main className="page">
        <Link to={back.to} className="back-link">
          {back.label}
        </Link>
        <p role="alert">{state === "not-found" ? t("report.notFound") : t("report.loadError")}</p>
      </main>
    );
  }

  const { recording } = report;
  const owner = "owner" in report ? report.owner : null;
  const clipSrc: ClipSource = (failureId) => (admin ? adminClipUrl : clipUrl)(recording.id, failureId);

  return (
    <main className="page">
      <Link to={back.to} className="back-link">
        {back.label}
      </Link>
      <h1 className="recording-title">{recording.filename}</h1>
      <dl className="comparison recording-details">
        {owner !== null && (
          <>
            <dt>{t("admin.owner")}</dt>
            <dd>{owner}</dd>
          </>
        )}
        <dt>{t("report.uploaded")}</dt>
        <dd>{formatUploadTime(recording.created_at, language)}</dd>
        {recording.duration_s !== null && (
          <>
            <dt>{t("report.length")}</dt>
            <dd>{formatDuration(recording.duration_s)}</dd>
          </>
        )}
        {recording.width !== null && recording.height !== null && (
          <>
            <dt>{t("report.resolution")}</dt>
            <dd>
              {recording.width}×{recording.height}
            </dd>
          </>
        )}
      </dl>

      <StatusMessage recording={recording} t={t} />
      {recording.low_resolution && recording.status !== "rejected" && (
        <p className="notice">{t("report.lowResolution")}</p>
      )}
      {recording.status === "done" && <FailureReport report={report} boss={boss} clipSrc={clipSrc} />}

      {!admin && (
        <>
          {deleteFailed && <p role="alert">{t("recordings.deleteError")}</p>}
          <div className="form-actions">
            <button type="button" className="btn" onClick={() => handleDelete(recording)}>
              {t("recordings.delete")}
            </button>
          </div>
        </>
      )}
    </main>
  );
}
