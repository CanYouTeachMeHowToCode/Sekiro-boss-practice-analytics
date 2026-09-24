import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getBosses } from "../api/bosses";
import type { BossSummary } from "../types";

type LoadState = "loading" | "error" | "ready";

export default function BossList() {
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

  if (state === "loading") return <p>Loading bosses…</p>;
  if (state === "error") return <p role="alert">Failed to load bosses.</p>;

  return (
    <ul className="boss-list">
      {bosses.map((boss) => (
        <li key={boss.id} className="boss-card">
          <h3>{boss.name}</h3>
          {boss.name_zh && <p className="boss-name-zh">{boss.name_zh}</p>}
          <p>{boss.location}</p>
          <Link to={`/bosses/${boss.id}`} className="btn btn-primary">
            View Boss
          </Link>
        </li>
      ))}
    </ul>
  );
}
