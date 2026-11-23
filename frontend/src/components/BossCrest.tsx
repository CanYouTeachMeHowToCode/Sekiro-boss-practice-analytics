/** A boss's mark in visual style B: a gold double ring with the boss's crest character in it, instead of a picture of
 * the boss (no game art, CLAUDE.md section 22). The character is boss data (`crest`); until the owner picks one, the
 * ring holds a small diamond. Decorative: the boss's name is always written next to it. */
export default function BossCrest({ crest, size = 40 }: { crest?: string | null; size?: number }) {
  return (
    <svg className="boss-crest" viewBox="0 0 40 40" width={size} height={size} aria-hidden="true" focusable="false">
      <circle className="crest-ring" cx="20" cy="20" r="18.5" />
      <circle className="crest-ring inner" cx="20" cy="20" r="15" />
      {crest ? (
        <text className="crest-char" x="20" y="20" textAnchor="middle" dominantBaseline="central">
          {crest}
        </text>
      ) : (
        <path className="crest-mark" d="M20 14 L24.5 20 L20 26 L15.5 20 Z" />
      )}
    </svg>
  );
}
