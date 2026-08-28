import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";

vi.mock("../tauri-fs", () => import("../test-utils/fs-fixture"));

import { loadCanonicalProject } from "../canonical-adapter";
import { buildClaimLineage, buildExperimentLineages } from "../lineage";
import { resolveProjectLayout } from "../test-utils/fs-fixture";
import type { ProjectSnapshot } from "../canonical";

// 貫穿式 fixture 只有一份，放在 profile 底下（experiment_records 的測試也讀它）。
// 這裡直接指過去，不在 viewer 複製一份——複製出來的那份遲早會跟本尊分歧。
const walkthroughDir = fileURLToPath(
  new URL("../../../../../examples/experimental/rag-walkthrough", import.meta.url)
);

async function walkthrough(): Promise<ProjectSnapshot> {
  return loadCanonicalProject(await resolveProjectLayout(walkthroughDir));
}

describe("buildClaimLineage - 成功路徑", () => {
  it("walks from the claim all the way back to the certificate", async () => {
    const lineage = buildClaimLineage(await walkthrough(), "topk-recall-claim");

    expect(lineage).not.toBeNull();
    const kinds = lineage!.steps.map((step) => step.kind);
    expect(kinds).toContain("claim");
    expect(kinds).toContain("audit");
    expect(kinds).toContain("comparison");
    expect(kinds).toContain("run");
    expect(kinds).toContain("definition");
    expect(kinds).toContain("certificate");
  });

  it("reaches both runs of the comparison", async () => {
    const lineage = buildClaimLineage(await walkthrough(), "topk-recall-claim");

    const runs = lineage!.steps.filter((step) => step.kind === "run");
    expect(runs.map((step) => step.label)).toEqual([
      "baseline：topk-main-baseline",
      "treatment：topk-main-treatment",
    ]);
    expect(runs.every((step) => step.ref)).toBe(true);
  });

  it("reaches the prompt version behind every generated record", async () => {
    const lineage = buildClaimLineage(await walkthrough(), "topk-recall-claim");

    const prompts = lineage!.steps.filter((step) => step.kind === "prompt");
    const details = prompts.map((step) => step.detail).join(" ");
    expect(details).toContain("claim-writer@1");
    expect(details).toContain("evidence-reviewer@1");
    expect(details).toContain("question-builder@1");
  });

  it("reaches the sources that were actually saved", async () => {
    const lineage = buildClaimLineage(await walkthrough(), "topk-recall-claim");

    const sources = lineage!.steps.filter((step) => step.kind === "source");
    expect(sources.map((step) => step.ref)).toContain(
      "records/experiments/artifacts/topk-prior-art.md"
    );
  });

  it("reports an unbroken chain when every link resolves", async () => {
    const lineage = buildClaimLineage(await walkthrough(), "topk-recall-claim");

    expect(lineage!.broken).toBe(false);
  });

  it("surfaces the audit gap that the mechanical pass cannot see", async () => {
    // 數字全對、卻沒有完整回答原問題——這件事不能只留在 audit 檔案裡。
    const lineage = buildClaimLineage(await walkthrough(), "topk-recall-claim");

    const audit = lineage!.steps.find((step) => step.kind === "audit");
    expect(audit!.warning).toContain("partially_answers");
  });
});

describe("buildClaimLineage - 失敗與存疑不被隱藏", () => {
  it("builds a lineage for an inconclusive claim just like any other", async () => {
    const lineage = buildClaimLineage(await walkthrough(), "query-rewrite-claim");

    expect(lineage).not.toBeNull();
    expect(lineage!.steps.some((step) => step.kind === "comparison")).toBe(true);
  });

  it("lists every claim of an experiment regardless of its verdict", async () => {
    const snapshot = await walkthrough();

    const rewrite = buildExperimentLineages(snapshot, "rag-query-rewrite");
    expect(rewrite.map((lineage) => lineage.claimId)).toEqual(["query-rewrite-claim"]);

    const claim = snapshot.experiments
      .find((e) => e.experimentId === "rag-query-rewrite")!
      .claims.find((c) => c.claimId === "query-rewrite-claim")!;
    expect(claim.status).toBe("inconclusive");
  });

  it("keeps an invalid run on the chain and marks why", async () => {
    const snapshot = await walkthrough();
    const experiment = snapshot.experiments.find((e) => e.experimentId === "rag-topk-recall")!;

    // 失敗的複現沒有從 runs 消失。
    const oom = experiment.runs.find((run) => run.runId === "topk-replication-4-oom");
    expect(oom!.status).toBe("invalid");
    expect(oom!.failure?.failureClass).toBe("execution");
  });

  it("flags a chain whose comparison cannot be resolved", async () => {
    const snapshot = await walkthrough();
    const experiment = snapshot.experiments.find((e) => e.experimentId === "rag-topk-recall")!;
    experiment.claims[0].comparisonRef = "records/experiments/comparisons/gone.json";

    const lineage = buildClaimLineage(snapshot, "topk-recall-claim");

    const comparison = lineage!.steps.find((step) => step.kind === "comparison");
    expect(comparison!.missing).toBe(true);
    // 接不上的環節仍然留在鏈上——鏈上少一環跟鏈上有一環接不上，讀的人要分得出來。
    expect(lineage!.broken).toBe(true);
  });

  it("flags a claim that was never audited instead of dropping the step", async () => {
    const snapshot = await walkthrough();
    const experiment = snapshot.experiments.find((e) => e.experimentId === "rag-topk-recall")!;
    experiment.claims[0].auditResult = null;

    const lineage = buildClaimLineage(snapshot, "topk-recall-claim");

    const audit = lineage!.steps.find((step) => step.kind === "audit");
    expect(audit!.missing).toBe(true);
    expect(lineage!.broken).toBe(true);
  });

  it("returns null for a claim that does not exist", async () => {
    expect(buildClaimLineage(await walkthrough(), "no-such-claim")).toBeNull();
  });
});

describe("loadCanonicalProject - lineage 需要的欄位", () => {
  it("loads the certificate and the failure diagnoses", async () => {
    const snapshot = await walkthrough();

    const topk = snapshot.experiments.find((e) => e.experimentId === "rag-topk-recall")!;
    expect(topk.derivation!.falsifier).toContain("recall_at_10");
    expect(topk.derivation!.assumptions.map((a) => a.id)).toEqual(["a1", "a2", "a3"]);

    const overlap = snapshot.experiments.find((e) => e.experimentId === "rag-chunk-overlap")!;
    expect(overlap.diagnoses).toHaveLength(1);
    expect(overlap.diagnoses[0].hypotheses.every((h) => h.failureClass === "confound")).toBe(true);
  });

  it("has no diagnostics for the walkthrough fixture", async () => {
    const snapshot = await walkthrough();

    expect(snapshot.diagnostics).toEqual([]);
  });
});
