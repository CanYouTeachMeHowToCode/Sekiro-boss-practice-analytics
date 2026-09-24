import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/authContext";
import { useLanguage } from "../i18n/language";

export default function NavBar() {
  const { status, user, logout } = useAuth();
  const { language, setLanguage, t } = useLanguage();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout().catch(() => undefined);
    navigate("/");
  }

  const otherLanguage = language === "en" ? "zh" : "en";

  return (
    <header className="nav-bar">
      <nav aria-label={t("nav.main")}>
        <Link to="/" className="nav-brand">
          {t("nav.brand")}
        </Link>
        <Link to="/bosses">{t("nav.bosses")}</Link>
      </nav>
      <div className="nav-account">
        <button
          type="button"
          className="language-toggle"
          onClick={() => setLanguage(otherLanguage)}
          aria-label={t("nav.switchLanguageLabel")}
          lang={otherLanguage === "zh" ? "zh-Hans" : "en"}
        >
          {t("nav.switchLanguage")}
        </button>
        {status === "ready" &&
          (user ? (
            <>
              <span className="nav-username">{user.username}</span>
              <button type="button" className="btn" onClick={handleLogout}>
                {t("nav.logOut")}
              </button>
            </>
          ) : (
            <>
              <Link to="/login">{t("nav.logIn")}</Link>
              <Link to="/register" className="btn btn-primary">
                {t("nav.register")}
              </Link>
            </>
          ))}
      </div>
    </header>
  );
}
