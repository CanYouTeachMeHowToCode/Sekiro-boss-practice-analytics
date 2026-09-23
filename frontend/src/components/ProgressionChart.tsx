import type { Boss, ProgressionPoint } from "../types";

const X_STEP = 28;
const ROW_HEIGHT = 36;
const MARGIN = { top: 16, right: 16, bottom: 28, left: 40 };
const MIN_WIDTH = 320;
const MAX_X_LABELS = 10;

interface ProgressionChartProps {
  boss: Boss;
  points: ProgressionPoint[];
}

export default function ProgressionChart({ boss, points }: ProgressionChartProps) {
  if (points.length === 0) {
    return (
      <section className="progression">
        <h2>Progression</h2>
        <p>Record an attempt to see your progression.</p>
      </section>
    );
  }

  const phaseNumbers = boss.phases.map((p) => p.phase_number).sort((a, b) => a - b);
  const topPhase = phaseNumbers[phaseNumbers.length - 1] ?? 1;
  const plotHeight = (topPhase - 1) * ROW_HEIGHT;
  const width = Math.max(MIN_WIDTH, MARGIN.left + MARGIN.right + (points.length - 1) * X_STEP);
  const height = MARGIN.top + plotHeight + MARGIN.bottom;

  const x = (attemptNumber: number) => MARGIN.left + (attemptNumber - 1) * X_STEP;
  const y = (phase: number) => MARGIN.top + (topPhase - phase) * ROW_HEIGHT;
  const labelEvery = Math.ceil(points.length / MAX_X_LABELS);
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.attempt_number)},${y(p.phase_reached)}`).join(" ");
  const victories = points.filter((p) => p.result === "victory").length;

  return (
    <section className="progression">
      <h2>Progression</h2>
      <div className="progression-scroll">
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`Phase reached across ${points.length} attempts, ${victories} of them victories`}
        >
          {phaseNumbers.map((phase) => (
            <g key={phase}>
              <line className="progression-grid" x1={MARGIN.left} x2={width - MARGIN.right} y1={y(phase)} y2={y(phase)} />
              <text className="progression-axis" x={MARGIN.left - 8} y={y(phase)} textAnchor="end" dominantBaseline="middle">
                P{phase}
              </text>
            </g>
          ))}
          {points
            .filter((p) => (p.attempt_number - 1) % labelEvery === 0)
            .map((p) => (
              <text
                key={p.attempt_id}
                className="progression-axis"
                x={x(p.attempt_number)}
                y={height - 8}
                textAnchor="middle"
              >
                {p.attempt_number}
              </text>
            ))}
          <path className="progression-line" d={path} />
          {points.map((p) => (
            <circle
              key={p.attempt_id}
              className={p.result === "victory" ? "progression-point victory" : "progression-point"}
              cx={x(p.attempt_number)}
              cy={y(p.phase_reached)}
              r={p.result === "victory" ? 7 : 5}
              aria-label={`Attempt ${p.attempt_number}: Phase ${p.phase_reached}, ${p.result}`}
            >
              <title>{`Attempt ${p.attempt_number}: Phase ${p.phase_reached}, ${p.result}`}</title>
            </circle>
          ))}
        </svg>
      </div>
    </section>
  );
}
