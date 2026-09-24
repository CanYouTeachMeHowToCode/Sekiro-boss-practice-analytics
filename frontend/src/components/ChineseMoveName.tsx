import type { BossMove } from "../types";

const TRANSLATION_NOTE = "Translated for this app; not an official in-game name.";

/**
 * A move's Chinese name next to its English one. Names taken from a Chinese wiki
 * link to that page; translations are labelled so they are never mistaken for
 * official names.
 */
export default function ChineseMoveName({ move }: { move: BossMove }) {
  if (!move.name_zh) return null;

  if (move.name_zh_source === "wiki" && move.name_zh_source_url) {
    return (
      <span className="move-name-zh" lang="zh-Hans">
        <a href={move.name_zh_source_url} target="_blank" rel="noopener noreferrer" title="Name from a Chinese wiki">
          {move.name_zh}
        </a>
      </span>
    );
  }

  return (
    <span className="move-name-zh" lang="zh-Hans">
      {move.name_zh}
      <abbr className="translation-badge" title={TRANSLATION_NOTE} aria-label={`译名: ${TRANSLATION_NOTE}`}>
        译名
      </abbr>
    </span>
  );
}
