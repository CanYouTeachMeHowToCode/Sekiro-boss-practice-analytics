import type { Boss } from "../types";
import ChineseMoveName from "./ChineseMoveName";

export default function MovesetReference({ boss }: { boss: Boss }) {
  return (
    <section className="moveset-reference">
      <h2>Boss Moveset</h2>

      {boss.phases.map((phase) => (
        <div key={phase.phase_number} className="moveset-phase">
          <h3>{phase.name}</h3>
          <ul>
            {phase.moves.map((move) => (
              <li key={move.id}>
                <strong>{move.name}</strong>
                <ChineseMoveName move={move} />
                {move.description && <p>{move.description}</p>}
                {move.telegraph && <p className="telegraph">Telegraph: {move.telegraph}</p>}
                {move.counter && <p className="counter">Counter: {move.counter}</p>}
                {move.common_mistakes && <p className="common-mistakes">Common mistake: {move.common_mistakes}</p>}
              </li>
            ))}
          </ul>
        </div>
      ))}

      {boss.source_url && (
        <p className="moveset-source">
          Source:{" "}
          <a href={boss.source_url} target="_blank" rel="noopener noreferrer">
            {boss.source_name ?? boss.source_url}
          </a>
        </p>
      )}
    </section>
  );
}
