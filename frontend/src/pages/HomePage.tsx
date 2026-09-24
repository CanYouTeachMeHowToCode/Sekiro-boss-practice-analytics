import { useAuth } from "../auth/authContext";
import SekiroDashboardPage from "./SekiroDashboardPage";
import WelcomePage from "./WelcomePage";

/** Logged-in players see their Sekiro dashboard; visitors see the welcome page and boss list. */
export default function HomePage() {
  const { status, user } = useAuth();

  if (status === "loading") {
    return (
      <main className="page">
        <p>Loading…</p>
      </main>
    );
  }

  return user ? <SekiroDashboardPage /> : <WelcomePage />;
}
