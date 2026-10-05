import { Link } from "react-router-dom";
import BossList from "../components/BossList";
import { useLanguage } from "../i18n/language";

export default function BossSelectionPage() {
  const { t } = useLanguage();
  return (
    <main className="page">
      <Link to="/" className="back-link">
        {t("bossSelection.back")}
      </Link>
      <h1>{t("appTitle")}</h1>
      <h2>{t("bossSelection.heading")}</h2>
      <BossList />
    </main>
  );
}
