// 研究 lineage：從一個 claim 一路走回它憑什麼成立。
//
// claim → audit → comparison → runs → definition/certificate → sources/prompts
//
// 每一步都可能斷掉（引用的東西不存在、還沒產生、或根本沒記）。斷掉時回一個
// 標了 missing 的節點，不是把那一步從鏈上拿掉——鏈上少一環跟鏈上有一環接不上，
// 讀的人要分得出來。
//
// 失敗與作廢的 run、refuted 與 inconclusive 的 claim 一律照實列出。這條鏈存在的
// 目的就是回答「這個結論憑什麼」，而選擇性隱藏會讓答案失真。

import type {
  CanonicalClaim,
  CanonicalComparison,
  CanonicalDerivation,
  CanonicalExperiment,
  CanonicalProducer,
  CanonicalRun,
  ProjectSnapshot,
} from "./canonical";

export type LineageStepKind =
  | "claim"
  | "audit"
  | "comparison"
  | "run"
  | "definition"
  | "certificate"
  | "source"
  | "prompt";

export interface LineageStep {
  kind: LineageStepKind;
  /** 這一步在畫面上的標題。 */
  label: string;
  /** 一句話說明這一步提供了什麼。 */
  detail: string;
  /** 這一步對應的紀錄路徑；斷掉時是嘗試解析的 ref。 */
  ref?: string;
  /** true 代表這一步接不上——引用的東西找不到，或根本沒記。 */
  missing: boolean;
  /** 需要提醒讀者的狀態，例如 confounded、invalid run、未稽核。 */
  warning?: string;
}

export interface ClaimLineage {
  claimId: string;
  steps: LineageStep[];
  /** 鏈上任何一步接不上就是 true。UI 據此提醒「這條證據鏈有缺口」。 */
  broken: boolean;
}

function producerStep(producer: CanonicalProducer | null, role: string): LineageStep {
  if (!producer) {
    return {
      kind: "prompt",
      label: `${role} 的產出者`,
      detail: "未記錄 producer，回溯不到是誰、用哪版 prompt 產生的",
      missing: true,
    };
  }
  const version = producer.promptId ? `，prompt ${producer.promptId}` : "";
  const model = producer.model ? `，model ${producer.model}` : "";
  return {
    kind: "prompt",
    label: `${role} 的產出者：${producer.name}`,
    detail: `${producer.kind}${model}${version}`,
    missing: false,
    warning: producer.kind === "software_agent" && !producer.promptHash
      ? "沒有記錄 prompt_hash，偵測不到 prompt 漂移"
      : undefined,
  };
}

function certificateStep(derivation: CanonicalDerivation | null, sourcePath: string): LineageStep {
  if (!derivation) {
    return {
      kind: "certificate",
      label: "研究問題憑證",
      detail: "這個 experiment 的 definition 沒有 derivation 區塊",
      ref: sourcePath,
      missing: true,
    };
  }
  return {
    kind: "certificate",
    label: "研究問題憑證",
    detail: `可證偽觀察：${derivation.falsifier}`,
    ref: sourcePath,
    missing: false,
    warning: derivation.noveltyStatus === "unverified" ? "新穎性未查證" : undefined,
  };
}

function runStep(runId: string, run: CanonicalRun | undefined, role: string): LineageStep {
  if (!run) {
    return {
      kind: "run",
      label: `${role}：${runId}`,
      detail: "runs/ 底下找不到這個 run",
      missing: true,
    };
  }
  const stage = run.stage ? `${run.stage} 階段，` : "";
  return {
    kind: "run",
    label: `${role}：${run.runId}`,
    detail: `${stage}status=${run.status}`,
    ref: run.sourcePath,
    missing: false,
    // 作廢的 run 仍然留在鏈上——它是這條鏈的一部分，只是要標出來。
    warning: run.status === "invalid"
      ? `作廢：${run.invalidReason ?? run.failure?.failureClass ?? "未說明原因"}`
      : undefined,
  };
}

/** 從 claim 往回組出完整的證據鏈。找不到 claim 時回 null。 */
export function buildClaimLineage(snapshot: ProjectSnapshot, claimId: string): ClaimLineage | null {
  let claim: CanonicalClaim | undefined;
  let experiment: CanonicalExperiment | undefined;
  for (const candidate of snapshot.experiments) {
    const found = candidate.claims.find((c) => c.claimId === claimId);
    if (found) {
      claim = found;
      experiment = candidate;
      break;
    }
  }
  if (!claim || !experiment) return null;

  const steps: LineageStep[] = [];

  steps.push({
    kind: "claim",
    label: `結論：${claim.claimId}`,
    detail: claim.statement,
    ref: claim.sourcePath,
    missing: false,
    warning: claim.status === "superseded" && claim.supersededBy
      ? `已被 ${claim.supersededBy} 取代`
      : undefined,
  });
  steps.push(producerStep(claim.producer, "結論"));

  const audit = claim.auditResult;
  if (audit) {
    const fit = audit.intendedQuestionFit?.verdict;
    steps.push({
      kind: "audit",
      label: `稽核：${audit.finalVerdict}`,
      detail: audit.scopeReasoning ?? audit.entailment?.reasoning ?? "（無說明）",
      ref: audit.sourcePath,
      missing: false,
      warning: fit && fit !== "answers" ? `回答原問題的程度：${fit}` : undefined,
    });
    steps.push(producerStep(audit.producer, "稽核"));
  } else {
    steps.push({
      kind: "audit",
      label: "稽核",
      detail: "這個 claim 還沒有對應的 claim-audit-result",
      missing: true,
    });
  }

  const comparison: CanonicalComparison | undefined = snapshot.comparisons.find(
    (c) => c.sourcePath === claim.comparisonRef
  );
  if (comparison) {
    steps.push({
      kind: "comparison",
      label: `比較：${comparison.runA} vs ${comparison.runB}`,
      detail: `comparison_valid=${comparison.comparisonValid}、confounded=${comparison.confounded}`,
      ref: comparison.sourcePath,
      missing: false,
      warning: comparison.comparisonValid ? undefined : "這次比較不可引用",
    });

    const byId = new Map(experiment.runs.map((run) => [run.runId, run]));
    steps.push(runStep(comparison.runA, byId.get(comparison.runA), "baseline"));
    steps.push(runStep(comparison.runB, byId.get(comparison.runB), "treatment"));
  } else {
    steps.push({
      kind: "comparison",
      label: "比較",
      detail: "comparison_ref 指到的檔案不在已載入的 comparisons 裡",
      ref: claim.comparisonRef,
      missing: true,
    });
  }

  steps.push({
    kind: "definition",
    label: `實驗定義：${experiment.experimentId}`,
    detail: experiment.question ?? "（未記錄 question）",
    ref: experiment.sourcePath,
    missing: false,
    warning: experiment.status === "draft" ? "Contract 尚未鎖定" : undefined,
  });
  steps.push(certificateStep(experiment.derivation, experiment.sourcePath));
  steps.push(producerStep(experiment.producer, "題目"));

  for (const ref of experiment.derivation?.sourceRefs ?? []) {
    steps.push({
      kind: "source",
      label: "查過的來源",
      detail: ref,
      ref,
      missing: false,
    });
  }

  return { claimId, steps, broken: steps.some((step) => step.missing) };
}

/**
 * 這個 experiment 底下所有 claim 的 lineage，含 refuted 與 inconclusive。
 * 排序只依 createdAt，不依「結論好不好看」。
 */
export function buildExperimentLineages(
  snapshot: ProjectSnapshot,
  experimentId: string
): ClaimLineage[] {
  const experiment = snapshot.experiments.find((e) => e.experimentId === experimentId);
  if (!experiment) return [];
  return [...experiment.claims]
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
    .map((claim) => buildClaimLineage(snapshot, claim.claimId))
    .filter((lineage): lineage is ClaimLineage => lineage !== null);
}
