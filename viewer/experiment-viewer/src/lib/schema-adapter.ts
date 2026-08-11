// Schema Adapter — 把 records/experiments/ 底下目前這包定義的 schema 轉成 canonical model。
// 只認 profiles/experimental/records/experiments/schemas/ 現有的欄位；schema 改版時只改這個檔案。

import type {
  CanonicalClaim,
  CanonicalClaimAuditResult,
  CanonicalComparison,
  CanonicalExperiment,
  CanonicalGateHistoryEntry,
  CanonicalGateState,
  CanonicalMetricDefinition,
  CanonicalMetricDiff,
  CanonicalRun,
  ClaimVerdict,
  GateLevel,
  MetricDirection,
  RunStatus,
} from "./canonical";

export class SchemaAdapterError extends Error {
  readonly sourcePath: string;

  constructor(message: string, sourcePath: string) {
    super(`${sourcePath}: ${message}`);
    this.name = "SchemaAdapterError";
    this.sourcePath = sourcePath;
  }
}

function requireField(obj: Record<string, unknown>, field: string, sourcePath: string): unknown {
  if (!(field in obj) || obj[field] === undefined) {
    throw new SchemaAdapterError(`缺少必填欄位 "${field}"`, sourcePath);
  }
  return obj[field];
}

// experiment-contract.schema.json → CanonicalExperiment（runs／claims／gateState 留空，由 canonical-adapter 填入）
export function adaptExperimentContract(
  raw: Record<string, unknown>,
  sourcePath: string
): Omit<CanonicalExperiment, "runs" | "claims" | "gateState"> {
  const experimentId = requireField(raw, "experiment_id", sourcePath) as string;
  const question = requireField(raw, "question", sourcePath) as string;
  const hypothesis = requireField(raw, "hypothesis", sourcePath) as string;
  const status = requireField(raw, "status", sourcePath) as "draft" | "locked";
  const primaryMetric = requireField(raw, "primary_metric", sourcePath) as string;

  return {
    experimentId,
    question,
    hypothesis,
    status,
    contractHash: raw.contract_hash as string | undefined,
    primaryMetric,
    secondaryMetrics: (raw.secondary_metrics as string[]) ?? [],
    sourcePath,
  };
}

// run-envelope.schema.json → CanonicalRun
export function adaptRunEnvelope(raw: Record<string, unknown>, sourcePath: string): CanonicalRun {
  const runId = requireField(raw, "run_id", sourcePath) as string;
  const experimentId = requireField(raw, "experiment_id", sourcePath) as string;
  const experimentType = requireField(raw, "experiment_type", sourcePath) as string;
  const createdAt = requireField(raw, "created_at", sourcePath) as string;
  const configHash = requireField(raw, "config_hash", sourcePath) as string;
  const status = requireField(raw, "status", sourcePath) as RunStatus;

  if (status === "invalid" && !raw.invalid_reason) {
    throw new SchemaAdapterError('status 為 "invalid" 時必須有 invalid_reason', sourcePath);
  }

  return {
    runId,
    experimentId,
    experimentType,
    status,
    createdAt,
    baselineRun: (raw.baseline_run as string | null) ?? null,
    treatment: raw.treatment as string | undefined,
    configHash,
    metrics: (raw.metrics as Record<string, number>) ?? {},
    artifacts: (raw.artifacts as string[]) ?? [],
    invalidReason: raw.invalid_reason as string | undefined,
    sourcePath,
  };
}

// comparison-result.schema.json（compare-runs 的輸出）→ CanonicalComparison
export function adaptComparisonResult(
  raw: Record<string, unknown>,
  sourcePath: string
): CanonicalComparison {
  const experimentId = requireField(raw, "experiment_id", sourcePath) as string;
  const runA = requireField(raw, "run_a", sourcePath) as string;
  const runB = requireField(raw, "run_b", sourcePath) as string;
  const comparisonValid = requireField(raw, "comparison_valid", sourcePath) as boolean;
  const confounded = requireField(raw, "confounded", sourcePath) as boolean;
  const rawMetrics = (requireField(raw, "metrics", sourcePath) as Record<
    string,
    Record<string, unknown>
  >) ?? {};

  const metrics: CanonicalMetricDiff[] = Object.entries(rawMetrics).map(([metric, m]) => ({
    metric,
    definitionConsistent: Boolean(m.definition_consistent),
    computed: Boolean(m.computed),
    baseline: (m.baseline as number | null) ?? null,
    treatment: (m.treatment as number | null) ?? null,
    absoluteDiff: (m.absolute_diff as number | null) ?? null,
    relativeDiff: (m.relative_diff as number | null) ?? null,
  }));

  return {
    experimentId,
    runA,
    runB,
    comparisonValid,
    confounded,
    confoundedReasons: (raw.confounded_reasons as string[]) ?? [],
    notes: (raw.notes as string[]) ?? [],
    metrics,
    sourcePath,
  };
}

// claim.schema.json → CanonicalClaim
export function adaptClaim(raw: Record<string, unknown>, sourcePath: string): CanonicalClaim {
  const claimId = requireField(raw, "claim_id", sourcePath) as string;
  const statement = requireField(raw, "statement", sourcePath) as string;
  const experimentId = requireField(raw, "experiment_id", sourcePath) as string;
  const comparisonRef = requireField(raw, "comparison_ref", sourcePath) as string;
  const metric = requireField(raw, "metric", sourcePath) as string;
  const expectedDirection = requireField(raw, "expected_direction", sourcePath) as
    | "increase"
    | "decrease"
    | "no_change";
  const scope = requireField(raw, "scope", sourcePath) as string;
  const createdAt = requireField(raw, "created_at", sourcePath) as string;

  return {
    claimId,
    statement,
    experimentId,
    comparisonRef,
    metric,
    expectedDirection,
    statedMagnitude: raw.stated_magnitude as number | undefined,
    magnitudeType: raw.magnitude_type as "absolute" | "relative" | undefined,
    scope,
    createdAt,
    sourcePath,
    auditResult: null,
  };
}

// claim-audit-result.schema.json（claim_audit.py 的機械段輸出 + agent 填的語意段）→ CanonicalClaimAuditResult
export function adaptClaimAuditResult(
  raw: Record<string, unknown>,
  sourcePath: string
): CanonicalClaimAuditResult {
  const claimId = requireField(raw, "claim_id", sourcePath) as string;
  const auditedAt = requireField(raw, "audited_at", sourcePath) as string;
  const mechanical = requireField(raw, "mechanical", sourcePath) as Record<string, unknown>;
  const finalVerdict = requireField(raw, "final_verdict", sourcePath) as Exclude<
    ClaimVerdict,
    "pending"
  >;

  if (!("mechanical_pass" in mechanical)) {
    throw new SchemaAdapterError('mechanical 底下缺少 "mechanical_pass"', sourcePath);
  }

  return {
    claimId,
    auditedAt,
    mechanicalPass: Boolean(mechanical.mechanical_pass),
    referenceExists: Boolean(mechanical.reference_exists),
    comparisonValid: (mechanical.comparison_valid as boolean | null) ?? null,
    metricExists: (mechanical.metric_exists as boolean | null) ?? null,
    directionMatches: (mechanical.direction_matches as boolean | null) ?? null,
    magnitudeMatches: (mechanical.magnitude_matches as boolean | null) ?? null,
    mechanicalReasons: (raw.mechanical_reasons as string[]) ?? [],
    scopeVerdict: (raw.scope_verdict as ClaimVerdict) ?? "pending",
    scopeReasoning: raw.scope_reasoning as string | undefined,
    finalVerdict,
    sourcePath,
  };
}

// gate-state.schema.json（compute_gate.py 維護的單一、append-only 檔案）→ CanonicalGateState
export function adaptGateState(raw: Record<string, unknown>, sourcePath: string): CanonicalGateState {
  const experimentId = requireField(raw, "experiment_id", sourcePath) as string;
  const history = requireField(raw, "history", sourcePath) as Array<Record<string, unknown>>;
  const updatedAt = requireField(raw, "updated_at", sourcePath) as string;

  const canonicalHistory: CanonicalGateHistoryEntry[] = history.map((entry) => ({
    level: entry.level as GateLevel,
    status: entry.status as "passed" | "failed" | "aborted",
    decidedAt: entry.decided_at as string,
    reason: entry.reason as string,
    runIds: (entry.run_ids as string[]) ?? [],
  }));

  return {
    experimentId,
    currentLevel: (raw.current_level as GateLevel | null) ?? null,
    history: canonicalHistory,
    updatedAt,
    sourcePath,
  };
}

// metric-definition.schema.json → CanonicalMetricDefinition
// direction 是「只有 comparison_valid=true 且 metric 有方向定義才顯示 improvement/regression」
// 這條規則唯一的資料來源——沒有這份定義就只能顯示中性的 change。
export function adaptMetricDefinition(
  raw: Record<string, unknown>,
  sourcePath: string
): CanonicalMetricDefinition {
  const name = requireField(raw, "name", sourcePath) as string;
  const type = requireField(raw, "type", sourcePath) as CanonicalMetricDefinition["type"];
  const direction = requireField(raw, "direction", sourcePath) as MetricDirection;
  const aggregation = requireField(raw, "aggregation", sourcePath) as string;
  const implementation = requireField(raw, "implementation", sourcePath) as string;

  return { name, type, direction, aggregation, implementation, sourcePath };
}
