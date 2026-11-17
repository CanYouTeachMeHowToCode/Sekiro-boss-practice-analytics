import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteRecording, listRecordings } from "../api/recordings";
import { useAuth } from "../auth/authContext";
import LoginPrompt from "../components/LoginPrompt";
import { useLanguage } from "../i18n/language";
import type { Recording } from "../types";
import { LIST_POLL_MS, formatDuration, formatUploadTime, isPending, statusLabel } from "../utils/recordings";

/** The user's uploaded recordings, newest first, with where each one is. */
export default function RecordingsPage() {
  const { status: authStatus, user } = useAuth();
  const { language, t } = useLanguage();
  const [recordings, setRecordings] = useState<Recording[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [deleteFailed, setDeleteFailed] = useState(false);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    let timer: number | undefined;
    let loaded = false;
    const load = () => {
      listRecordings()
        .then((rows) => {
          if (cancelled) return;
          loaded = true;
          setRecordings(rows);
          setLoadFailed(false);
          if (rows.some((r) => isPending(r.status))) timer = window.setTimeout(load, LIST_POLL_MS);
        })
        .catch(() => {
          if (cancelled) return;
          // a failed refresh keeps the list it has and tries again; a failed first load is an error
          if (loaded) timer = window.setTimeout(load, LIST_POLL_MS);
          else setLoadFailed(true);
        });
    };
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [user]);

  async function handleDelete(recording: Recording) {
    if (!window.confirm(t("recordings.deleteConfirm", { file: recording.filename }))) return;
    setDeleteFailed(false);
    try {
      await deleteRecording(recording.id);
      setRecordings((rows) => rows?.filter((r) => r.id !== recording.id) ?? null);
    } catch {
      setDeleteFailed(true);
    }
  }

  if (authStatus === "loading") {
    return (
      <main className="page">
        <p>{t("loading")}</p>
      </main>
    );
  }

  return (
    <main className="page">
      <h1>{t("recordings.heading")}</h1>
      <p>{t("recordings.intro")}</p>
      {!user ? (
        <LoginPrompt rest="recordings.loginPrompt" />
      ) : (
        <>
          <Link to="/recordings/upload" className="btn btn-primary">
            {t("recordings.upload")}
          </Link>
          {deleteFailed && <p role="alert">{t("recordings.deleteError")}</p>}
          {loadFailed ? (
            <p role="alert">{t("recordings.loadError")}</p>
          ) : recordings === null ? (
            <p>{t("loading")}</p>
          ) : recordings.length === 0 ? (
            <p className="recordings-empty">{t("recordings.empty")}</p>
          ) : (
            <ul className="recording-list">
              {recordings.map((r) => (
                <li key={r.id} className={`recording-item status-${r.status}`}>
                  <div className="recording-main">
                    <Link to={`/recordings/${r.id}`} className="recording-name">
                      {r.filename}
                    </Link>
                    <p className="recording-meta">
                      {[
                        formatUploadTime(r.created_at, language),
                        r.duration_s !== null ? formatDuration(r.duration_s) : null,
                        r.height !== null ? t("recordings.resolution", { height: r.height }) : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <span className="recording-status">{statusLabel(r, t)}</span>
                  <button type="button" className="btn btn-small" onClick={() => handleDelete(r)}>
                    {t("recordings.delete")}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </main>
  );
}
