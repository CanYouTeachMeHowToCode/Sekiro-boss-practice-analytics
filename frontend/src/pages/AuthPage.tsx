import { useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/authContext";
import PasswordInput from "../components/PasswordInput";
import { useLanguage } from "../i18n/language";
import type { MessageKey, Translate } from "../i18n/language";

type Mode = "login" | "register";

interface LocationState {
  from?: string;
}

const COPY: Record<Mode, { title: MessageKey; submit: MessageKey; switchText: MessageKey; switchLink: MessageKey; switchTo: string }> = {
  login: {
    title: "auth.login.title",
    submit: "auth.login.submit",
    switchText: "auth.login.switchText",
    switchLink: "auth.login.switchLink",
    switchTo: "/register",
  },
  register: {
    title: "auth.register.title",
    submit: "auth.register.submit",
    switchText: "auth.register.switchText",
    switchLink: "auth.register.switchLink",
    switchTo: "/login",
  },
};

function errorMessage(err: unknown, mode: Mode, t: Translate): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return t("auth.error.incorrect");
    if (err.status === 409) return t("auth.error.taken");
    if (err.status === 422) return mode === "register" ? t("auth.rules") : t("auth.error.missing");
  }
  return t("auth.error.generic");
}

export default function AuthPage({ mode }: { mode: Mode }) {
  const { status, user, login, register } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as LocationState | null)?.from ?? "/";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already logged in (e.g. opened /login directly): go where they were headed.
  if (status === "ready" && user && !submitting) {
    return <Navigate to={from} replace />;
  }

  const copy = COPY[mode];

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await (mode === "login" ? login : register)({ username, password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(errorMessage(err, mode, t));
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page">
      <h1>{t(copy.title)}</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          {t("auth.username")}
          <input
            name="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </label>
        <PasswordInput
          value={password}
          onChange={setPassword}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
        />
        {mode === "register" && <p className="form-hint">{t("auth.rules")}</p>}
        {error && <p role="alert">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? t("auth.pleaseWait") : t(copy.submit)}
        </button>
      </form>
      <p>
        {t(copy.switchText)}{" "}
        <Link to={copy.switchTo} state={location.state}>
          {t(copy.switchLink)}
        </Link>
      </p>
    </main>
  );
}
