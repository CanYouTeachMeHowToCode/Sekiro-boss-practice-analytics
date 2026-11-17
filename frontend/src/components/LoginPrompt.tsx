import { Link, useLocation } from "react-router-dom";
import { useLanguage } from "../i18n/language";
import type { MessageKey } from "../i18n/language";

/** "Log in or create an account <rest>", returning to this page afterwards. */
export default function LoginPrompt({ rest }: { rest: MessageKey }) {
  const location = useLocation();
  const { t } = useLanguage();
  return (
    <p className="login-prompt">
      <Link to="/login" state={{ from: location.pathname }}>
        {t("boss.loginPrompt.login")}
      </Link>
      {t("boss.loginPrompt.or")}
      <Link to="/register" state={{ from: location.pathname }}>
        {t("boss.loginPrompt.register")}
      </Link>
      {t(rest)}
    </p>
  );
}
