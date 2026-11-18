import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAdminRecordings } from "../api/admin";
import { useAuth } from "../auth/authContext";
import { useLanguage } from "../i18n/language";
import type { AdminRecording } from "../types";
import { LIST_POLL_MS, formatDuration, formatUploadTime, rejectReason, statusLabel } from "../utils/recordings";

/** The read-only admin view of every user's recordings (owner decision, 2026-11-18). It checks for new uploads
 * and progress every few seconds. For anyone but an admin it is a page that does not exist. */
export default function AdminPage() {
  const { status: authStatus, user } = useAuth();
  const { language, t } = useLanguage();
  const [recordings, setRecordings] = useState<AdminRecording[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const isAdmin = user?.is_admin === true;

  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false;
    let timer: number | undefined;
    let loaded = false;
    const load = () => {
      listAdminRecordings()
        .then((rows) => {
          if (cancelled) return;
          loaded = true;
          setRecordings(rows);
          setLoadFailed(false);
          timer = window.setTimeout(load, LIST_POLL_MS);
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
  }, [isAdmin]);

  if (authStatus === "loading") {
    return (
      <main className="page">
        <p>{t("loading")}</p>
      </main>
    );
  }

  if (!isAdmin) {
    return (
      <main className="page">
        <p role="alert">{t("admin.notFound")}</p>
      </main>
    );
  }

  function video(r: AdminRecording): string {
    return [
      r.width !== null && r.height !== null ? `${r.width}×${r.height}` : null,
      r.duration_s !== null ? formatDuration(r.duration_s) : null,
      r.fps !== null ? `${Math.round(r.fps)} fps` : null,
    ]
      .filter(Boolean)
      .join(" · ");
  }

  function problem(r: AdminRecording): string {
    if (r.status === "rejected") return rejectReason(r.reject_code, t);
    if (r.status === "failed") return r.error ?? "";
    return "";
  }

  return (
    <main className="page page-wide">
      <h1>{t("admin.heading")}</h1>
      <p>{t("admin.intro")}</p>
      {loadFailed ? (
        <p role="alert">{t("admin.loadError")}</p>
      ) : recordings === null ? (
        <p>{t("loading")}</p>
      ) : recordings.length === 0 ? (
        <p>{t("admin.empty")}</p>
      ) : (
        <div className="table-scroll">
          <table className="admin-recordings">
            <thead>
              <tr>
                <th scope="col">{t("admin.col.owner")}</th>
                <th scope="col">{t("admin.col.file")}</th>
                <th scope="col">{t("admin.col.status")}</th>
                <th scope="col">{t("admin.col.video")}</th>
                <th scope="col">{t("admin.col.uploaded")}</th>
                <th scope="col">{t("admin.col.finished")}</th>
                <th scope="col">{t("admin.col.problem")}</th>
              </tr>
            </thead>
            <tbody>
              {recordings.map((r) => (
                <tr key={r.id} className={`status-${r.status}`}>
                  <td>{r.owner}</td>
                  <td>
                    <Link to={`/admin/recordings/${r.id}`}>{r.filename}</Link>
                  </td>
                  <td>{statusLabel(r, t)}</td>
                  <td>{video(r)}</td>
                  <td>{formatUploadTime(r.created_at, language)}</td>
                  <td>{r.processed_at ? formatUploadTime(r.processed_at, language) : ""}</td>
                  <td>{problem(r)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
