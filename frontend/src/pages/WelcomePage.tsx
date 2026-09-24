import { Link } from "react-router-dom";
import BossList from "../components/BossList";

export default function WelcomePage() {
  return (
    <main className="page">
      <h1>Sekiro Boss Practice Analytics</h1>
      <p>
        Record each boss attempt in a few seconds (how far you got and what ended the attempt) and see which phases and
        moves are holding you back, and whether you are improving.
      </p>
      <p className="welcome-actions">
        <Link to="/register" className="btn btn-primary">
          Create an Account
        </Link>
        <Link to="/login" className="btn">
          Log In
        </Link>
      </p>
      <h2>Bosses</h2>
      <p>Browse each boss&apos;s phases and moveset without an account.</p>
      <BossList />
    </main>
  );
}
