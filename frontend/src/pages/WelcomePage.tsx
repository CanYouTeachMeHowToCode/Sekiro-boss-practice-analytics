import { Link } from "react-router-dom";
import BossList from "../components/BossList";
import { useLanguage } from "../i18n/language";

export default function WelcomePage() {
  const { t } = useLanguage();
  return (
    <main className="page">
      <h1>{t("appTitle")}</h1>
      <p>{t("welcome.intro")}</p>
      <p className="welcome-actions">
        <Link to="/register" className="btn btn-primary">
          {t("welcome.createAccount")}
        </Link>
        <Link to="/login" className="btn">
          {t("welcome.logIn")}
        </Link>
      </p>
      <h2>{t("welcome.bosses")}</h2>
      <p>{t("welcome.browse")}</p>
      <BossList />
    </main>
  );
}
