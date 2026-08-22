import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";

vi.mock("../tauri-fs", () => import("../test-utils/fs-fixture"));

import { loadCanonicalProject } from "../canonical-adapter";
import { resolveProjectLayout } from "../test-utils/fs-fixture";

const fixturesDir = fileURLToPath(new URL("../../../tests/fixtures", import.meta.url));

async function loadCanonicalFixture(root: string) {
  return loadCanonicalProject(await resolveProjectLayout(root));
}

describe("loadCanonicalProject - happy path (RAG / 演算法比較 / 模擬三種實驗)", () => {
  const root = path.join(fixturesDir, "canonical/happy-path");

  it("loads all three experiments", async () => {
    const snapshot = await loadCanonicalFixture(root);
    expect(snapshot.adapterKind).toBe("canonical");
    expect(snapshot.experiments.map((e) => e.experimentId).sort()).toEqual([
      "algo-sort-compare",
      "rag-topk-recall",
      "sim-queueing",
    ]);
  });

  it("attaches runs, claim audit result, and gate state to the RAG experiment", async () => {
    const snapshot = await loadCanonicalFixture(root);
    const rag = snapshot.experiments.find((e) => e.experimentId === "rag-topk-recall");
    expect(rag?.runs.map((r) => r.runId).sort()).toEqual([
      "rag-topk-recall-baseline",
      "rag-topk-recall-treatment",
    ]);
    expect(rag?.claims).toHaveLength(1);
    expect(rag?.claims[0].auditResult?.finalVerdict).toBe("fully_supported");
    expect(rag?.claims[0].auditResult?.evidenceEligible).toBe(true);
    expect(rag?.eligibleRunStages).toEqual(["pilot", "main", "replication"]);
    expect(rag?.gateState?.currentLevel).toBe("L2");
    expect(rag?.gateState?.history).toHaveLength(3);
  });

  it("loads the comparison result as valid and non-confounded", async () => {
    const snapshot = await loadCanonicalFixture(root);
    expect(snapshot.comparisons).toHaveLength(1);
    expect(snapshot.comparisons[0].comparisonValid).toBe(true);
    expect(snapshot.comparisons[0].evidenceEligible).toBe(true);
    expect(snapshot.comparisons[0].confounded).toBe(false);
  });

  it("loads the persisted estimate, interval and decision as written", async () => {
    // 統計語意屬於 compare-runs。Viewer 只搬紀錄裡的數字與判定，不自己重算。
    const snapshot = await loadCanonicalFixture(root);
    const [estimate] = snapshot.comparisons[0].estimates;
    expect(estimate.estimandId).toBe("effect.primary");
    expect(estimate.pointEstimate).toBe(0.09);
    expect(estimate.interval).toEqual({
      lower: 0.031,
      upper: 0.147,
      confidenceLevel: 0.95,
      method: "percentile",
    });
    expect(estimate.clusters).toBe(42);
    expect(estimate.decision.conclusion).toBe("superior");
    expect(estimate.decision.reasonCodes).toEqual(["interval_above_null"]);
    expect(estimate.componentEstimates.map((c) => c.id)).toEqual(["baseline", "treatment"]);
  });

  it("keeps an estimate without an interval as inconclusive instead of guessing", async () => {
    const snapshot = await loadCanonicalFixture(path.join(fixturesDir, "canonical/edge-cases"));
    const comparison = snapshot.comparisons.find((c) => c.runB === "edge-good-run-2")!;
    expect(comparison.estimates[0].interval).toBeNull();
    expect(comparison.estimates[0].decision.conclusion).toBe("inconclusive");
    expect(comparison.estimates[0].decision.reasonCodes).toEqual(["interval_missing"]);
  });

  it("loads metric definitions with direction", async () => {
    const snapshot = await loadCanonicalFixture(root);
    const byName = Object.fromEntries(snapshot.metricDefinitions.map((m) => [m.name, m]));
    expect(byName.recall_at_10.direction).toBe("higher_is_better");
    expect(byName.latency_ms.direction).toBe("lower_is_better");
  });

  it("collects artifact references from run envelopes", async () => {
    const snapshot = await loadCanonicalFixture(root);
    expect(snapshot.artifacts.map((a) => a.path)).toContain(
      "artifacts/rag-topk-recall-baseline/recall_curve.png"
    );
  });

  it("has no diagnostics when every file is well-formed", async () => {
    const snapshot = await loadCanonicalFixture(root);
    expect(snapshot.diagnostics).toEqual([]);
  });
});

describe("loadCanonicalProject - edge cases", () => {
  const root = path.join(fixturesDir, "canonical/edge-cases");

  it("keeps loading other runs when one run file is malformed JSON", async () => {
    const snapshot = await loadCanonicalFixture(root);
    const exp = snapshot.experiments.find((e) => e.experimentId === "edge-exp");
    expect(exp?.runs.map((r) => r.runId)).toContain("edge-good-run");
    expect(
      snapshot.diagnostics.some((d) => d.level === "error" && d.sourcePath === "records/experiments/runs/edge-bad.json")
    ).toBe(true);
  });

  it("reports a missing required field as a diagnostic instead of throwing", async () => {
    const snapshot = await loadCanonicalFixture(root);
    expect(
      snapshot.diagnostics.some(
        (d) => d.level === "error" && d.sourcePath === "records/experiments/runs/edge-missing-field.json"
      )
    ).toBe(true);
  });

  it("keeps an orphan run out of any experiment and reports a warning", async () => {
    const snapshot = await loadCanonicalFixture(root);
    const allRunIds = snapshot.experiments.flatMap((e) => e.runs.map((r) => r.runId));
    expect(allRunIds).not.toContain("edge-orphan-run");
    expect(
      snapshot.diagnostics.some((d) => d.level === "warning" && d.message.includes("edge-orphan-run"))
    ).toBe(true);
  });

  it("loads an invalid run with its invalid_reason instead of dropping it", async () => {
    const snapshot = await loadCanonicalFixture(root);
    const exp = snapshot.experiments.find((e) => e.experimentId === "edge-exp");
    const invalidRun = exp?.runs.find((r) => r.runId === "edge-invalid-run");
    expect(invalidRun?.status).toBe("invalid");
    expect(invalidRun?.invalidReason).toContain("OOM");
  });

  it("marks a confounded comparison as invalid with reasons, not silently dropped", async () => {
    const snapshot = await loadCanonicalFixture(root);
    const comparison = snapshot.comparisons.find((c) => c.runB === "edge-invalid-run")!;
    expect(comparison.confounded).toBe(true);
    expect(comparison.comparisonValid).toBe(false);
    expect(comparison.evidenceEligible).toBe(false);
    expect(comparison.confoundedReasons.length).toBeGreaterThan(0);
  });

  it("loads an audit whose semantic pass has not run yet as pending, not as an error", async () => {
    // scope_verdict 還是 pending 時，schema 規定不得寫出 final_verdict。
    // 缺這一欄是合法的中間狀態，不是壞掉的檔案。
    const snapshot = await loadCanonicalFixture(root);
    const exp = snapshot.experiments.find((e) => e.experimentId === "edge-exp");
    const claim = exp?.claims.find((c) => c.claimId === "edge-pending-claim");
    expect(claim?.auditResult?.scopeVerdict).toBe("pending");
    expect(claim?.auditResult?.finalVerdict).toBe("pending");
    expect(claim?.auditResult?.mechanicalPass).toBe(true);
    expect(
      snapshot.diagnostics.some((d) => d.sourcePath === "records/experiments/audits/edge-pending.json")
    ).toBe(false);
  });
});
