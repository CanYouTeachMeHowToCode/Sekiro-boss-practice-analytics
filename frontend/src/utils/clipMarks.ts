import type { RecordingFailureType } from "../types";

/** A moment marked on a clip: the events of one failure at one time, this clip's failure (`own`) or another whose
 * events fall inside the clip. */
export interface ClipMark {
  time_s: number;
  types: RecordingFailureType[];
  own: boolean;
}

interface FailureMoments {
  id: string;
  time_s: number;
  type: RecordingFailureType;
  events: { type: RecordingFailureType; time_s: number }[];
}

/** The marks of `failure`'s clip: its own events and every other failure's, the events of one at one moment together
 * (a damage and the death it caused). FailureClip keeps those inside the clip. */
export function clipMarks(failure: FailureMoments, all: FailureMoments[]): ClipMark[] {
  const marks: ClipMark[] = [];
  for (const f of all) {
    const own = f.id === failure.id;
    const events = f.events.length > 0 ? f.events : [{ type: f.type, time_s: f.time_s }];
    for (const e of events) {
      const same = marks.find((m) => m.own === own && Math.abs(m.time_s - e.time_s) < 0.05);
      if (!same) marks.push({ time_s: e.time_s, types: [e.type], own });
      else if (!same.types.includes(e.type)) same.types.push(e.type);
    }
  }
  return marks.sort((a, b) => a.time_s - b.time_s);
}
