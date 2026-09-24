import { useId, useState } from "react";
import { useLanguage } from "../i18n/language";

interface PasswordInputProps {
  value: string;
  onChange: (value: string) => void;
  autoComplete: "current-password" | "new-password";
}

function EyeIcon({ crossed }: { crossed: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
      <path
        d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
      {crossed && <path d="M4 4l16 16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />}
    </svg>
  );
}

/** A labelled password field with a button that shows or hides what was typed. */
export default function PasswordInput({ value, onChange, autoComplete }: PasswordInputProps) {
  const { t } = useLanguage();
  const id = useId();
  const [visible, setVisible] = useState(false);
  const toggleLabel = visible ? t("password.hide") : t("password.show");

  return (
    <div className="form-field">
      <label htmlFor={id}>{t("auth.password")}</label>
      <div className="password-field">
        <input
          id={id}
          name="password"
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={toggleLabel}
          aria-pressed={visible}
          title={toggleLabel}
        >
          {/* Crossed-out eye while the password is visible: the button hides it again. */}
          <EyeIcon crossed={visible} />
        </button>
      </div>
    </div>
  );
}
