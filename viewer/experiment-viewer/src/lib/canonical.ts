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
