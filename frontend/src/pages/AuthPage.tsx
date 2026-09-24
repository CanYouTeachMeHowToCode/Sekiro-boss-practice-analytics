import { useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/authContext";
import PasswordInput from "../components/PasswordInput";

type Mode = "login" | "register";

interface LocationState {
  from?: string;
}

const COPY: Record<Mode, { title: string; submit: string; switchText: string; switchLink: string; switchTo: string }> = {
  login: {
    title: "Log In",
    submit: "Log In",
    switchText: "No account yet?",
    switchLink: "Register",
    switchTo: "/register",
  },
  register: {
    title: "Create an Account",
    submit: "Register",
    switchText: "Already have an account?",
    switchLink: "Log in",
    switchTo: "/login",
  },
};

const REGISTER_RULES = "Username: 3–30 letters, digits, '_' or '-'. Password: at least 8 characters.";

function errorMessage(err: unknown, mode: Mode): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return "Incorrect username or password.";
    if (err.status === 409) return "That username is already taken.";
    if (err.status === 422) return mode === "register" ? REGISTER_RULES : "Enter your username and password.";
  }
  return "Something went wrong. Please try again.";
}

export default function AuthPage({ mode }: { mode: Mode }) {
  const { status, user, login, register } = useAuth();
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
      setError(errorMessage(err, mode));
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page">
      <h1>{copy.title}</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          Username
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
        {mode === "register" && <p className="form-hint">{REGISTER_RULES}</p>}
        {error && <p role="alert">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Please wait…" : copy.submit}
        </button>
      </form>
      <p>
        {copy.switchText}{" "}
        <Link to={copy.switchTo} state={location.state}>
          {copy.switchLink}
        </Link>
      </p>
    </main>
  );
}
