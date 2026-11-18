import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { UploadError, uploadProblem, uploadRecording } from "../api/recordings";
import { useAuth } from "../auth/authContext";
import LoginPrompt from "../components/LoginPrompt";
import { useLanguage } from "../i18n/language";
import type { MessageKey } from "../i18n/language";
import { formatSize, percent, uploadErrorMessage } from "../utils/recordings";

const REQUIREMENTS: MessageKey[] = [
  "upload.req.boss",
  "upload.req.format",
  "upload.req.language",
  "upload.req.resolution",
  "upload.req.frameRate",
  "upload.req.private",
];

/** What the analysis supports, and the upload with its progress; a finished upload opens the recording's page. */
export default function UploadRecordingPage() {
  const { status: authStatus, user } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const upload = useRef<AbortController | null>(null);

  // leaving the page stops an upload that is still running
  useEffect(() => () => upload.current?.abort(), []);

  function handleChoose(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0] ?? null;
    setFile(chosen);
    setProblem(chosen ? uploadProblem(chosen) : null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || progress !== null) return;
    const found = uploadProblem(file);
    if (found) {
      setProblem(found);
      return;
    }
    const controller = new AbortController();
    upload.current = controller;
    setProblem(null);
    setProgress(0);
    try {
      const recording = await uploadRecording(file, setProgress, controller.signal);
      navigate(`/recordings/${recording.id}`);
    } catch (err) {
      if (controller.signal.aborted) return;
      setProblem(err instanceof UploadError ? err.code : "unknown");
      setProgress(null);
    }
  }

  function handleCancel() {
    upload.current?.abort();
    setProgress(null);
  }

  if (authStatus === "loading") {
    return (
      <main className="page">
        <p>{t("loading")}</p>
      </main>
    );
  }

  const uploading = progress !== null;
  // a file the backend would refuse cannot be sent; after a failed upload (a lost connection) it can be sent again
  const fileProblem = file ? uploadProblem(file) : null;

  return (
    <main className="page">
      <Link to="/recordings" className="back-link">
        {t("upload.back")}
      </Link>
      <h1>{t("upload.heading")}</h1>

      <section className="upload-requirements">
        <h2>{t("upload.requirements")}</h2>
        <ul>
          {REQUIREMENTS.map((key) => (
            <li key={key}>{t(key)}</li>
          ))}
        </ul>
      </section>

      {!user ? (
        <LoginPrompt rest="recordings.loginPrompt" />
      ) : (
        <form className="upload-form" onSubmit={handleSubmit}>
          <label className="form-field">
            {t("upload.file")}
            <input
              type="file"
              accept=".mp4,.mkv,.mov,video/mp4,video/x-matroska,video/quicktime"
              onChange={handleChoose}
              disabled={uploading}
            />
          </label>
          {file && <p className="form-hint">{t("upload.selected", { name: file.name, size: formatSize(file.size) })}</p>}
          {problem && <p role="alert">{uploadErrorMessage(problem, t)}</p>}
          {uploading && (
            <div className="upload-progress">
              <progress max={1} value={progress} aria-label={t("upload.uploading", { percent: percent(progress) })} />
              <p>{t("upload.uploading", { percent: percent(progress) })}</p>
              <p className="form-hint">{t("upload.stayOnPage")}</p>
            </div>
          )}
          <div className="form-actions">
            {uploading && (
              <button type="button" className="btn" onClick={handleCancel}>
                {t("cancel")}
              </button>
            )}
            <button type="submit" className="btn btn-primary" disabled={!file || fileProblem !== null || uploading}>
              {t("upload.submit")}
            </button>
          </div>
        </form>
      )}
    </main>
  );
}
