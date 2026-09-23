/** Every key sharing the highest count, so ties are shown instead of silently picking one. */
export function topKeys(counts: Record<string, number>): string[] {
  const max = Math.max(0, ...Object.values(counts));
  return max === 0 ? [] : Object.keys(counts).filter((key) => counts[key] === max);
}
