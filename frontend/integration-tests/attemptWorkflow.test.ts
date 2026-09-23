import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { spawn, spawnSync } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

// These tests boot the real FastAPI backend as a subprocess and drive it
// through the frontend's own (unmocked) api/ layer. They verify that the
// TypeScript request/response shapes actually match what the backend
// returns over the wire, which the mocked component/page tests can't catch.
//
// Requires the backend's Python environment (backend/.venv) and a running
// PostgreSQL server. The connection comes from TEST_DATABASE_URL, or from
// the repo's .env file. Not run as part of the default `npm test` / CI, see
// `npm run test:integration`.

const REPO_DIR = fileURLToPath(new URL("../..", import.meta.url));
const BACKEND_DIR = join(REPO_DIR, "backend");
const PORT = 8123;
const HEALTH_URL = `http://127.0.0.1:${PORT}/health`;
const API_BASE_URL = `http://127.0.0.1:${PORT}/api`;
// Separate from the backend's pytest database so the two suites never wipe each other's data.
const DATABASE_NAME = "sekiro_integration_test";

let backendProcess: ChildProcess;

function readDotEnv(): Record<string, string> {
  const path = join(REPO_DIR, ".env");
  if (!existsSync(path)) return {};
  const entries = readFileSync(path, "utf-8")
    .split(/\r?\n/)
    .map((line) => line.match(/^([^#=]+)=(.*)$/))
    .filter((match): match is RegExpMatchArray => match !== null)
    .map((match) => [match[1].trim(), match[2].trim()]);
  return Object.fromEntries(entries);
}

function integrationDatabaseUrl(): string {
  const base = process.env.TEST_DATABASE_URL ?? readDotEnv().TEST_DATABASE_URL;
  if (!base) {
    throw new Error("Set TEST_DATABASE_URL (or add it to the repo's .env) to run the integration tests");
  }
  const url = new URL(base);
  url.pathname = `/${DATABASE_NAME}`;
  return url.toString();
}

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
  const env = { ...process.env, DATABASE_URL: integrationDatabaseUrl() };

  const reset = spawnSync(resolvePython(), ["-m", "scripts.reset_test_database"], {
    cwd: BACKEND_DIR,
    env,
    encoding: "utf-8",
  });
  if (reset.status !== 0) {
    throw new Error(`Failed to reset the integration database:\n${reset.stderr}`);
  }

  backendProcess = spawn(resolvePython(), ["-m", "uvicorn", "app.main:app", "--port", String(PORT)], {
    cwd: BACKEND_DIR,
    env,
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
});

describe("frontend calling the real backend", () => {
  it("lists the seeded bosses exactly as the backend returns them", async () => {
    const { getBosses } = await import("../src/api/bosses");

    const bosses = await getBosses();

    expect(bosses.map((b) => b.id).sort()).toEqual([
      "corrupted-monk",
      "genichiro-ashina",
      "great-shinobi-owl",
      "guardian-ape",
      "isshin-sword-saint",
      "lady-butterfly",
      "owl-father",
      "true-corrupted-monk",
    ]);
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

  it("returns progression and a recent-window comparison for the attempts recorded above", async () => {
    const { getBossProgression, getBossAnalytics } = await import("../src/api/attempts");

    const points = await getBossProgression("genichiro-ashina");
    expect(points.map((p) => p.attempt_number)).toEqual([1, 2]);
    expect(points.map((p) => p.phase_reached)).toEqual([2, 1]);

    const analytics = await getBossAnalytics("genichiro-ashina", 1);
    expect(analytics.attempts_until_first_victory).toBeNull();
    expect(analytics.failure_by_phase).toEqual({ "2": 1, "1": 1 });
    expect(analytics.recent).toEqual({
      window_size: 1,
      total_attempts: 1,
      main_bottleneck_phase: 1,
      most_common_failure_move: null,
      failure_by_phase: { "1": 1 },
      failure_by_move: {},
    });
  });
});
