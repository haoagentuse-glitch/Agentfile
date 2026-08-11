import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";

vi.mock("../tauri-fs", () => import("../test-utils/fs-fixture"));

import { loadProject } from "../project-loader";

const fixturesDir = fileURLToPath(new URL("../../../tests/fixtures", import.meta.url));

describe("loadProject", () => {
  it("uses the canonical adapter when there is no viewer.json", async () => {
    const root = path.join(fixturesDir, "canonical/happy-path");
    const snapshot = await loadProject(root);
    expect(snapshot.adapterKind).toBe("canonical");
    expect(snapshot.experiments.length).toBeGreaterThan(0);
    expect(snapshot.projectRoot).toBe(root);
    expect(snapshot.recordsRoot).toBe(path.join(root, "records/experiments"));
  });

  it("uses the manifest adapter when viewer.json is present", async () => {
    const root = path.join(fixturesDir, "generic");
    const snapshot = await loadProject(root);
    expect(snapshot.adapterKind).toBe("manifest");
    expect(snapshot.experiments.map((e) => e.experimentId).sort()).toEqual(["exp-a", "exp-b"]);
  });

  it("accepts records/experiments as the selected root", async () => {
    const projectRoot = path.join(fixturesDir, "canonical/happy-path");
    const recordsRoot = path.join(projectRoot, "records/experiments");
    const snapshot = await loadProject(recordsRoot);

    expect(snapshot.projectRoot).toBe(projectRoot);
    expect(snapshot.recordsRoot).toBe(recordsRoot);
    expect(snapshot.experiments.length).toBeGreaterThan(0);
  });

  it("surfaces a malformed viewer.json as a diagnostic instead of throwing", async () => {
    const root = path.join(fixturesDir, "generic-bad-manifest");
    const snapshot = await loadProject(root);
    expect(snapshot.adapterKind).toBe("manifest");
    expect(snapshot.experiments).toEqual([]);
    expect(snapshot.diagnostics).toHaveLength(1);
    expect(snapshot.diagnostics[0].level).toBe("error");
    expect(snapshot.diagnostics[0].sourcePath).toBe("records/experiments/viewer.json");
  });
});
