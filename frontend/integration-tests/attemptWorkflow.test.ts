import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { spawn } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import { existsSync, mkdtempSync, copyFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

// These tests boot the real FastAPI backend as a subprocess and drive it
// through the frontend's own (unmocked) api/ layer. They verify that the
// TypeScript request/response shapes actually match what the backend
// returns over the wire, which the mocked component/page tests can't catch.
//
// Requires the backend's Python environment to already be set up locally
// (backend/.venv with requirements.txt installed) — not run as part of the
// default `npm test` / CI, see `npm run test:integration`.

const BACKEND_DIR = fileURLToPath(new URL("../../backend", import.meta.url));
const PORT = 8123;
const HEALTH_URL = `http://127.0.0.1:${PORT}/health`;
const API_BASE_URL = `http://127.0.0.1:${PORT}/api`;

let backendProcess: ChildProcess;
let dataDir: string;

function resolvePython(): string {
  const isWindows = process.platform === "win32";
  const venvPython = join(BACKEND_DIR, ".venv", isWindows ? "Scripts/python.exe" : "bin/python");
  if (existsSync(venvPython)) return venvPython;
  return isWindows ? "python" : "python3";
}

async function waitForHealth(timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError: unknown;

  while (Date.now() < deadline) {
    try {
      const res = await fetch(HEALTH_URL);
      if (res.ok) return;
    } catch (err) {
      lastError = err;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }

  throw new Error(`Backend did not become healthy within ${timeoutMs}ms: ${String(lastError)}`);
}

beforeAll(async () => {
  dataDir = mkdtempSync(join(tmpdir(), "sekiro-integration-"));
  copyFileSync(join(BACKEND_DIR, "app", "data", "bosses.json"), join(dataDir, "bosses.json"));
  writeFileSync(join(dataDir, "attempts.json"), "[]");

  backendProcess = spawn(resolvePython(), ["-m", "uvicorn", "app.main:app", "--port", String(PORT)], {
    cwd: BACKEND_DIR,
    env: { ...process.env, SEKIRO_DATA_DIR: dataDir },
    stdio: "pipe",
  });

  const startupErrors: string[] = [];
  backendProcess.stderr?.on("data", (chunk) => startupErrors.push(String(chunk)));

  vi.stubEnv("VITE_API_BASE_URL", API_BASE_URL);

  try {
    await waitForHealth(15000);
  } catch (err) {
    throw new Error(`${(err as Error).message}\nbackend stderr:\n${startupErrors.join("")}`);
  }
});

afterAll(() => {
  backendProcess?.kill();
  vi.unstubAllEnvs();
  rmSync(dataDir, { recursive: true, force: true });
});

describe("frontend calling the real backend", () => {
  it("lists the seeded bosses exactly as the backend returns them", async () => {
    const { getBosses } = await import("../src/api/bosses");

    const bosses = await getBosses();

    expect(bosses.map((b) => b.id).sort()).toEqual(["genichiro-ashina", "owl-father"]);
  });

  it("fetches boss detail with a real move id usable for recording an attempt", async () => {
    const { getBossById } = await import("../src/api/bosses");

    const boss = await getBossById("genichiro-ashina");

    expect(boss.name).toBe("Genichiro Ashina");
    const phase1Moves = boss.phases.find((p) => p.phase_number === 1)?.moves ?? [];
    expect(phase1Moves.some((m) => m.id === "floating-passage")).toBe(true);
  });

  it("surfaces a 404 from the real backend as an ApiError", async () => {
    const { getBossById } = await import("../src/api/bosses");
    const { ApiError } = await import("../src/api/client");

    await expect(getBossById("nonexistent-boss")).rejects.toThrow(ApiError);
  });

  it("records an attempt end-to-end and reflects it in history and analytics", async () => {
    const { getBossAttempts, createAttempt, getBossAnalytics } = await import("../src/api/attempts");

    const created = await createAttempt("genichiro-ashina", {
      result: "failed",
      phase_reached: 2,
      failure_move_id: "floating-passage",
      failure_category: null,
      notes: "integration test",
    });

    expect(created.id).toBeTruthy();
    expect(created.failure_move_id).toBe("floating-passage");
    expect(created.failure_category).toBeNull();

    const history = await getBossAttempts("genichiro-ashina");
    expect(history).toHaveLength(1);
    expect(history[0].notes).toBe("integration test");

    const analytics = await getBossAnalytics("genichiro-ashina");
    expect(analytics.total_attempts).toBe(1);
    expect(analytics.main_bottleneck_phase).toBe(2);
    expect(analytics.failure_by_move["floating-passage"]).toBe(1);
  });

  it("lets the backend default an unknown failure cause to not_sure, matching the V1 spec", async () => {
    const { createAttempt } = await import("../src/api/attempts");

    const created = await createAttempt("genichiro-ashina", {
      result: "failed",
      phase_reached: 1,
      failure_move_id: null,
      failure_category: null,
      notes: "",
    });

    expect(created.failure_move_id).toBeNull();
    expect(created.failure_category).toBe("not_sure");
  });
});
