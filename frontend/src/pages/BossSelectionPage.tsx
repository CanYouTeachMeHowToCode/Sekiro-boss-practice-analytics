import { Link } from "react-router-dom";
import BossList from "../components/BossList";

export default function BossSelectionPage() {
  return (
    <main className="page">
      <Link to="/" className="back-link">
        ← Home
      </Link>
      <h1>Sekiro Boss Practice Analytics</h1>
      <h2>Choose a Boss</h2>
      <BossList />
    </main>
  );
}
