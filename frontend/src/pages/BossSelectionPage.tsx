import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getBosses } from "../api/bosses";
import type { BossSummary } from "../types";

type LoadState = "loading" | "error" | "ready";

export default function BossSelectionPage() {
  const [bosses, setBosses] = useState<BossSummary[]>([]);
  const [state, setState] = useState<LoadState>("loading");

  useEffect(() => {
    let cancelled = false;
    setState("loading");

    getBosses()
      .then((data) => {
        if (cancelled) return;
        setBosses(data);
        setState("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="page">
      <h1>Sekiro Boss Practice Analytics</h1>
      <h2>Choose a Boss</h2>

      {state === "loading" && <p>Loading bosses…</p>}
      {state === "error" && <p role="alert">Failed to load bosses.</p>}

      {state === "ready" && (
        <ul className="boss-list">
          {bosses.map((boss) => (
            <li key={boss.id} className="boss-card">
              <h3>{boss.name}</h3>
              <p>{boss.location}</p>
              <Link to={`/bosses/${boss.id}`} className="btn btn-primary">
                View Boss
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
