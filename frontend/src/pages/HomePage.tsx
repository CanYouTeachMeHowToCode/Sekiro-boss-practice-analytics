import { useAuth } from "../auth/authContext";
import { useLanguage } from "../i18n/language";
import SekiroDashboardPage from "./SekiroDashboardPage";
import WelcomePage from "./WelcomePage";

/** Logged-in players see their Sekiro dashboard; visitors see the welcome page and boss list. */
export default function HomePage() {
  const { status, user } = useAuth();
  const { t } = useLanguage();

  if (status === "loading") {
    return (
      <main className="page">
        <p>{t("loading")}</p>
      </main>
    );
  }

  return user ? <SekiroDashboardPage /> : <WelcomePage />;
}
