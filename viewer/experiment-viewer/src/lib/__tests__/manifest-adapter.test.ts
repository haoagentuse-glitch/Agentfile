import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";

vi.mock("../tauri-fs", () => import("../test-utils/fs-fixture"));

import { loadManifestProject, parseViewerManifest, ViewerManifestError } from "../manifest-adapter";
import { resolveProjectLayout } from "../test-utils/fs-fixture";

const fixturesDir = fileURLToPath(new URL("../../../tests/fixtures", import.meta.url));
const root = path.join(fixturesDir, "generic");

async function loadManifestFixture() {
  const manifest = parseViewerManifest(JSON.parse(await readFixtureViewerJson()));
  return loadManifestProject(await resolveProjectLayout(root), manifest);
}

describe("parseViewerManifest", () => {
  it("accepts a well-formed manifest", () => {
    const manifest = parseViewerManifest({
      version: 1,
      experiments: { dir: "experiments", id: "meta.id" },
      runs: { dir: "runs", id: "meta.id", experimentId: "meta.experiment" },
    });
    expect(manifest.experiments.dir).toBe("experiments");
  });

  it("rejects a version other than 1", () => {
    expect(() =>
      parseViewerManifest({
        version: 2,
        experiments: { dir: "experiments", id: "meta.id" },
        runs: { dir: "runs", id: "meta.id", experimentId: "meta.experiment" },
      })
    ).toThrow(ViewerManifestError);
  });

  it("requires experiments.dir and experiments.id", () => {
    expect(() =>
      parseViewerManifest({
        version: 1,
        experiments: { id: "meta.id" },
        runs: { dir: "runs", id: "meta.id", experimentId: "meta.experiment" },
      })
    ).toThrow(ViewerManifestError);
  });

  it("requires runs.experimentId", () => {
    expect(() =>
      parseViewerManifest({
        version: 1,
        experiments: { dir: "experiments", id: "meta.id" },
        runs: { dir: "runs", id: "meta.id" },
      })
    ).toThrow(ViewerManifestError);
  });

  it("rejects a non-object payload", () => {
    expect(() => parseViewerManifest("not an object")).toThrow(ViewerManifestError);
  });
});

describe("loadManifestProject", () => {
  it("loads experiments and attaches matching runs via the experimentId dot-path", async () => {
    const snapshot = await loadManifestFixture();

    expect(snapshot.adapterKind).toBe("manifest");
    expect(snapshot.experiments.map((e) => e.experimentId).sort()).toEqual(["exp-a", "exp-b"]);

    const expA = snapshot.experiments.find((e) => e.experimentId === "exp-a");
    expect(expA?.runs.map((r) => r.runId).sort()).toEqual(["run-a1", "run-a2"]);
  });

  it("resolves metrics and artifacts via manifest-configured dot-paths", async () => {
    const snapshot = await loadManifestFixture();

    const expA = snapshot.experiments.find((e) => e.experimentId === "exp-a");
    const run1 = expA?.runs.find((r) => r.runId === "run-a1");
    expect(run1?.metrics).toEqual({ accuracy: 0.9, cost_usd: 1.2 });
    expect(run1?.artifacts).toEqual(["outputs/run-a1/report.html"]);
  });

  it("reports an orphan run as a warning without attaching it anywhere", async () => {
    const snapshot = await loadManifestFixture();

    const allRunIds = snapshot.experiments.flatMap((e) => e.runs.map((r) => r.runId));
    expect(allRunIds).not.toContain("run-orphan");
    expect(
      snapshot.diagnostics.some((d) => d.level === "warning" && d.message.includes("run-orphan"))
    ).toBe(true);
  });

  it("carries metric direction/unit/displayName from the manifest catalog", async () => {
    const snapshot = await loadManifestFixture();

    const byName = Object.fromEntries(snapshot.metricDefinitions.map((m) => [m.name, m]));
    expect(byName.accuracy.direction).toBe("higher_is_better");
    expect(byName.accuracy.displayName).toBe("Accuracy");
    expect(byName.accuracy.unit).toBe("ratio");
    expect(byName.accuracy.format).toBe(".2%");
    expect(byName.cost_usd.direction).toBe("lower_is_better");
  });

  it("keeps unmapped collections as generic records without interpreting their fields", async () => {
    const snapshot = await loadManifestFixture();

    const notes = snapshot.genericCollections.find((c) => c.name === "notes");
    expect(notes?.records.map((r) => r.id)).toEqual(["note-1"]);
    expect(notes?.columns).toEqual(["meta.title", "body"]);
  });

  it("does not guess a metric direction when the manifest omits it", async () => {
    const snapshot = await loadManifestFixture();

    const definition = snapshot.metricDefinitions.find((metric) => metric.name === "neutral_score");
    expect(definition?.direction).toBeUndefined();
  });
});

async function readFixtureViewerJson(): Promise<string> {
  const { readProjectFile } = await import("../test-utils/fs-fixture");
  return readProjectFile(root, "records/experiments/viewer.json");
}
