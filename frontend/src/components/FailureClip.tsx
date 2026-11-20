import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../i18n/language";
import type { ClipMark } from "../utils/clipMarks";
import { formatClock } from "../utils/recordings";

/** Around a hit of the clip's own failure the time over the clip turns red, from a little before it to a little after,
 * so the moment is readable while the clip plays. */
const HIT_BEFORE_S = 0.2;
const HIT_AFTER_S = 0.6;
/** A mark picked from the list plays from this long before it, so the hit is seen coming. */
const LEAD_S = 1.0;

/** A failure's clip with the recording's own time over it (red at this failure's hits) and, under it, where this
 * failure's hits and any other failure's fall in the clip: with two failures a few seconds apart, the clip of the later
 * one also shows the earlier one (owner, 2026-11-20). */
export default function FailureClip({ src, start, marks }: { src: string; start: number; marks: ClipMark[] }) {
  const { t } = useLanguage();
  const video = useRef<HTMLVideoElement>(null);
  const [now, setNow] = useState(0);
  const [length, setLength] = useState<number | null>(null);

  useEffect(() => {
    const v = video.current;
    if (!v) return undefined;
    let frame = 0;
    const read = () => setNow(v.currentTime);
    // timeupdate comes about four times a second, too seldom for tenths: follow every frame while playing
    const tick = () => {
      read();
      frame = requestAnimationFrame(tick);
    };
    const play = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(tick);
    };
    const stop = () => {
      cancelAnimationFrame(frame);
      read();
    };
    const meta = () => setLength(Number.isFinite(v.duration) && v.duration > 0 ? v.duration : null);
    const listeners: [string, () => void][] = [
      ["timeupdate", read],
      ["seeked", read],
      ["play", play],
      ["pause", stop],
      ["ended", stop],
      ["loadedmetadata", meta],
    ];
    listeners.forEach(([name, fn]) => v.addEventListener(name, fn));
    return () => {
      cancelAnimationFrame(frame);
      listeners.forEach(([name, fn]) => v.removeEventListener(name, fn));
    };
  }, []);

  const at = start + now;
  const hit = marks.find((m) => m.own && at >= m.time_s - HIT_BEFORE_S && at <= m.time_s + HIT_AFTER_S);
  const shown = length === null ? [] : marks.filter((m) => m.time_s >= start && m.time_s <= start + length);
  const left = (seconds: number) => `${length ? Math.min(100, Math.max(0, (seconds / length) * 100)) : 0}%`;
  const types = (m: ClipMark) => m.types.map((type) => t(`failureType.${type}`)).join(t("listSeparator"));
  const key = (m: ClipMark) => `${m.own ? "own" : "other"}-${m.time_s}`;

  const playFrom = (m: ClipMark) => {
    const v = video.current;
    if (!v) return;
    v.currentTime = Math.max(0, m.time_s - start - LEAD_S);
    try {
      void v.play()?.catch(() => undefined);
    } catch {
      // a browser that plays only after a click on the video itself: the clip is at the right moment anyway
    }
  };

  return (
    <div className="failure-clip-box">
      <div className="clip-frame">
        <video ref={video} className="failure-clip" src={src} controls autoPlay preload="metadata" />
        <span className={`clip-time${hit ? " hit" : ""}`} data-testid="clip-time">
          {formatClock(at)}
          {hit && ` · ${types(hit)}`}
        </span>
      </div>
      {length !== null && (
        <>
          <div className="clip-track" aria-hidden="true">
            {shown.map((m) => (
              <span key={key(m)} className={`clip-mark ${m.own ? "own" : "other"}`} style={{ left: left(m.time_s - start) }} />
            ))}
            <span className="clip-playhead" style={{ left: left(now) }} />
          </div>
          <div className="clip-ends" aria-hidden="true">
            <span>{formatClock(start)}</span>
            <span>{formatClock(start + length)}</span>
          </div>
          {shown.length > 0 && (
            <ul className="clip-marks" aria-label={t("report.clip.marks")}>
              {shown.map((m) => (
                <li key={key(m)}>
                  <button type="button" className={`clip-mark-button ${m.own ? "own" : "other"}`} onClick={() => playFrom(m)}>
                    {t("report.clip.mark", {
                      events: types(m),
                      time: formatClock(m.time_s),
                      which: t(m.own ? "report.clip.this" : "report.clip.other"),
                    })}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="clip-legend">{t("report.clip.legend")}</p>
        </>
      )}
    </div>
  );
}
