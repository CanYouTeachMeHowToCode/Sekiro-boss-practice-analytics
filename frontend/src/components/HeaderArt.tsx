/** The band under the nav row (visual style B「天守之夜」): a horizon line running to a castle keep with three tiers of
 * upturned eaves, and a crescent moon, all drawn in thin gold lines. Original artwork, no game imagery
 * (CLAUDE.md section 22); decorative only, so screen readers skip it. */
export default function HeaderArt() {
  return (
    <div className="header-art" aria-hidden="true">
      <svg viewBox="0 0 320 44" width="320" height="44" focusable="false">
        <path className="line faint" d="M0 38 H320" />
        {/* the moon: a crescent opening to the right */}
        <path className="line moon" d="M126 5.5 A9 9 0 1 0 126 22.5 A7 7 0 1 1 126 5.5 Z" />
        {/* a stretch of castle wall, then the keep on its stone base */}
        <path className="line faint" d="M150 38 V33 H186 V38 M156 33 V31 H180 V33" />
        <path className="line" d="M204 38 L210 31 H270 L276 38" />
        <path className="line" d="M214 31 V26 M266 31 V26" />
        <path className="line" d="M198 27.5 Q211 26 218 22 H262 Q269 26 282 27.5" />
        <path className="line" d="M224 22 V17 M256 22 V17" />
        <path className="line" d="M210 18.5 Q221 17 228 13 H252 Q259 17 270 18.5" />
        <path className="line" d="M232 13 V9 M248 13 V9" />
        <path className="line" d="M221 10 Q232 8.5 236 5 H244 Q248 8.5 259 10" />
        <path className="line" d="M240 5 V1.5" />
      </svg>
    </div>
  );
}
