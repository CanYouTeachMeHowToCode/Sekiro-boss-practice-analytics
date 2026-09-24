import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getBosses } from "../api/bosses";
import { bossLocation, bossName } from "../i18n/content";
import { useLanguage } from "../i18n/language";
import type { BossSummary } from "../types";

type LoadState = "loading" | "error" | "ready";

export default function BossList() {
  const { language, t } = useLanguage();
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

  if (state === "loading") return <p>{t("bossList.loading")}</p>;
  if (state === "error") return <p role="alert">{t("bossList.error")}</p>;

  return (
    <ul className="boss-list">
      {bosses.map((boss) => (
        <li key={boss.id} className="boss-card">
          <h3>{bossName(boss, language)}</h3>
          <p>{bossLocation(boss, language)}</p>
          <Link to={`/bosses/${boss.id}`} className="btn btn-primary">
            {t("bossList.view")}
          </Link>
        </li>
      ))}
    </ul>
  );
}
