// Canonical Experiment Model — 設計說明見 ../../README.md
// UI 元件只認這些型別，不直接碰 records/experiments/ 底下的原始 JSON 欄位名。

export type RunStatus = "pending" | "running" | "completed" | "invalid";

export interface CanonicalRun {
  runId: string;
  experimentId: string;
  experimentType: string;
  status: RunStatus;
  createdAt: string;
  baselineRun: string | null;
  treatment?: string;
  configHash: string;
  metrics: Record<string, number>;
  invalidReason?: string;
  sourcePath: string;
}

export interface CanonicalExperiment {
  experimentId: string;
  question: string;
  hypothesis: string;
  status: "draft" | "locked";
  contractHash?: string;
  primaryMetric: string;
  secondaryMetrics: string[];
  runs: CanonicalRun[];
  claims: CanonicalClaim[];
  gateState: CanonicalGateState | null;
  sourcePath: string;
}

export interface CanonicalClaim {
  claimId: string;
  statement: string;
  experimentId: string;
  comparisonRef: string;
  metric: string;
  expectedDirection: "increase" | "decrease" | "no_change";
  statedMagnitude?: number;
  magnitudeType?: "absolute" | "relative";
  scope: string;
  createdAt: string;
  sourcePath: string;
}

export type ClaimVerdict =
  | "fully_supported"
  | "partially_supported"
  | "overreaching"
  | "unsupported"
  | "unauditable"
  | "pending";

export interface CanonicalClaimAuditResult {
  claimId: string;
  auditedAt: string;
  mechanicalPass: boolean;
  referenceExists: boolean;
  comparisonValid: boolean | null;
  metricExists: boolean | null;
  directionMatches: boolean | null;
  magnitudeMatches: boolean | null;
  mechanicalReasons: string[];
  scopeVerdict: ClaimVerdict;
  scopeReasoning?: string;
  finalVerdict: Exclude<ClaimVerdict, "pending">;
  sourcePath: string;
}

export type GateLevel = "L0" | "L1" | "L2" | "L3" | "L4" | "L5";

export interface CanonicalGateHistoryEntry {
  level: GateLevel;
  status: "passed" | "failed" | "aborted";
  decidedAt: string;
  reason: string;
  runIds: string[];
}

export interface CanonicalGateState {
  experimentId: string;
  currentLevel: GateLevel | null;
  history: CanonicalGateHistoryEntry[];
  updatedAt: string;
  sourcePath: string;
}

export interface CanonicalMetricDiff {
  metric: string;
  definitionConsistent: boolean;
  computed: boolean;
  baseline: number | null;
  treatment: number | null;
  absoluteDiff: number | null;
  relativeDiff: number | null;
}

export interface CanonicalComparison {
  experimentId: string;
  runA: string;
  runB: string;
  comparisonValid: boolean;
  confounded: boolean;
  confoundedReasons: string[];
  metrics: CanonicalMetricDiff[];
  sourcePath: string;
}
