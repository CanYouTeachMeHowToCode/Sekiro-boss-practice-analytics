import type { Boss } from "../types";

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
                {move.description && <p>{move.description}</p>}
                {move.recommended_response && <p className="recommended-response">Response: {move.recommended_response}</p>}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
