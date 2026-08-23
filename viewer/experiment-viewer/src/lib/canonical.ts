// Canonical Experiment Model — 設計說明見 ../../README.md
// UI 元件只認這些型別，不直接碰 records/experiments/ 底下的原始 JSON 欄位名。

export type RunStatus = "pending" | "running" | "completed" | "invalid";

export interface CanonicalRunFailure {
  failureClass: string;
  phase: string;
  exitCode?: number;
  retriable?: boolean;
  errorArtifact?: string;
}

export interface CanonicalRun {
  runId: string;
  experimentId: string;
  experimentType?: string;
  stage?: string;
  parentRunId?: string;
  attemptKind?: string;
  // 跑失敗是正式結果。UI 照實顯示，不因為它不好看就過濾掉。
  failure?: CanonicalRunFailure;
  // canonical adapter 只會產生 RunStatus 四個值；manifest adapter 讀的是使用者自訂資料，
  // 狀態字串可以是任何值，所以型別放寬成 string，UI 對未知值一律用中性樣式顯示。
  status: string;
  createdAt?: string;
  baselineRun?: string | null;
  treatment?: string;
  configHash?: string;
  metrics: Record<string, number>;
  artifacts: string[];
  invalidReason?: string;
  sourcePath: string;
}

export interface CanonicalExperiment {
  experimentId: string;
  // 同 CanonicalRun.status：canonical adapter 只會給 "draft"/"locked"，manifest adapter
  // 的來源資料可能是任意字串，型別放寬成 string。
  status: string;
  question?: string;
  hypothesis?: string;
  contractHash?: string;
  primaryMetric?: string;
  secondaryMetrics: string[];
  eligibleRunStages: string[];
  runs: CanonicalRun[];
  claims: CanonicalClaim[];
  gateState: CanonicalGateState | null;
  derivation: CanonicalDerivation | null;
  producer: CanonicalProducer | null;
  diagnoses: CanonicalDiagnosis[];
  sourcePath: string;
}

// 產生或修改一份紀錄的責任者。lineage 靠它回答「這個結論是誰、用哪版 prompt 寫的」。
export interface CanonicalProducer {
  kind: string;
  name: string;
  model?: string;
  promptId?: string;
  promptHash?: string;
  inputRefs: string[];
  toolCallsArtifact?: string;
  createdAt?: string;
}

export interface CanonicalEvidenceRef {
  kind: "comparison" | "run" | "artifact" | "source";
  ref: string;
  locator?: string;
  hash?: string;
}

export type ClaimStatus = "candidate" | "supported" | "refuted" | "inconclusive" | "superseded";

export interface CanonicalClaim {
  claimId: string;
  statement: string;
  experimentId: string;
  comparisonRef: string;
  // claim 引用的是 comparison.estimates 裡的 estimand，不是 run metric。
  estimandId: string;
  // 只描述 point estimate 相對 null value 的符號預期，不含尺度與不確定性。
  expectedDirection: "increase" | "decrease";
  // 證據結論的預期，由凍結的 decision rule 判定，跟 expectedDirection 分開。
  expectedConclusion: DecisionConclusion;
  statedMagnitude?: number;
  magnitudeType?: "absolute" | "relative";
  scope: string;
  createdAt: string;
  claimType?: string;
  // refuted 與 inconclusive 是正式終態，UI 不得因為「不好看」就藏起來。
  status: ClaimStatus;
  supersededBy?: string;
  evidenceRefs: CanonicalEvidenceRef[];
  producer: CanonicalProducer | null;
  sourcePath: string;
  auditResult: CanonicalClaimAuditResult | null;
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
  evidenceEligible: boolean;
  evidenceReasons: string[];
  referenceExists: boolean;
  comparisonValid: boolean | null;
  estimandExists: boolean | null;
  directionMatches: boolean | null;
  conclusionMatches: boolean | null;
  magnitudeMatches: boolean | null;
  mechanicalReasons: string[];
  scopeVerdict: ClaimVerdict;
  scopeReasoning?: string;
  // "pending" 代表機械段跑完、語意段還沒判——schema 規定此時不得寫出 final_verdict，
  // 所以這裡不是「資料缺漏」，是一個合法的中間狀態，UI 必須照實顯示。
  finalVerdict: ClaimVerdict;
  intendedQuestionFit?: { verdict: string; reasoning?: string };
  entailment?: { verdict: string; reasoning?: string };
  novelty?: { status: string; sourceRefs: string[]; reasoning?: string };
  reviewIndependence?: { independent: boolean; reviewerKind?: string; reason?: string };
  producer: CanonicalProducer | null;
  sourcePath: string;
}

// definition.derivation 的研究問題憑證。lineage 的終點——「當初為什麼問這個問題」。
export interface CanonicalDerivation {
  primitives: Array<{ id: string; definition: string }>;
  assumptions: Array<{ id: string; statement: string; status: string }>;
  mechanismSummary: string;
  mechanismVariables: string[];
  tension: string;
  falsifier: string;
  minimalDecisiveTest: string;
  expectedObservations: string[];
  failureUpdate: Array<{ when: string; updateAssumptionId: string; to: string }>;
  sourceRefs: string[];
  counterexamples: string[];
  noveltyStatus: string;
}

export interface CanonicalDiagnosis {
  diagnosisId: string;
  experimentId: string;
  diagnosedAt: string;
  subject: { kind: string; ref: string };
  deterministicFacts: Array<{ fact: string; sourceRef: string; locator?: string }>;
  hypotheses: Array<{
    id: string;
    failureClass: string;
    statement: string;
    confidence: string;
    discriminatingObservation?: string;
  }>;
  excludedClasses: Array<{ failureClass: string; reason: string }>;
  cheapestNextTest: { description: string; command?: string; distinguishes: string[]; estimatedCost?: string };
  producer: CanonicalProducer | null;
  sourcePath: string;
}

export type GateLevel = "L0" | "L1" | "L2" | "L3" | "L4" | "L5";

export interface CanonicalGateHistoryEntry {
  level: GateLevel;
  status: "passed" | "failed" | "aborted";
  decidedAt: string;
  reason: string;
  runIds: string[];
  evidenceEligible: boolean;
  evidenceReasons: string[];
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

export interface CanonicalEstimateInterval {
  lower: number;
  upper: number;
  confidenceLevel: number;
  method: string;
}

export interface CanonicalEstimateComponent {
  id: string;
  pointEstimate: number;
  interval: CanonicalEstimateInterval | null;
}

export type DecisionConclusion = "superior" | "inferior" | "equivalent" | "inconclusive";

export interface CanonicalEstimateDecision {
  ruleId: string;
  // 數值方向與證據結論分開：point estimate 為正不等於 superior，
  // 區間跨過決策邊界時只會是 inconclusive。
  conclusion: DecisionConclusion;
  reasonCodes: string[];
}

export interface CanonicalComparisonEstimate {
  estimandId: string;
  estimatorId: string;
  pointEstimate: number;
  // interval 為 null 是合法狀態（例如沒設定 uncertainty），
  // 此時 decision 只能是 inconclusive，UI 照實顯示「未估計」。
  interval: CanonicalEstimateInterval | null;
  observations: number | null;
  clusters: number | null;
  methodRef: string;
  componentEstimates: CanonicalEstimateComponent[];
  decision: CanonicalEstimateDecision;
}

export interface CanonicalComparison {
  experimentId: string;
  runA: string;
  runB: string;
  // comparisonValid=false 不代表 confounded=true——兩者是 schema 上獨立的欄位
  // （例如指標定義不一致也可能讓整體判定不可比較，但不是因為 confound）。
  // UI 呈現時必須分開判斷，不能把「invalid」直接講成「confounded」。
  comparisonValid: boolean;
  evidenceEligible: boolean;
  evidenceReasons: string[];
  confounded: boolean;
  confoundedReasons: string[];
  notes: string[];
  metrics: CanonicalMetricDiff[];
  // 凍結 analysis plan 產生的 estimate 與判定。Viewer 只顯示持久化結果，
  // 不在前端重算點估計、區間或 decision——統計語意屬於 compare-runs，不屬於 UI。
  estimates: CanonicalComparisonEstimate[];
  sourcePath: string;
}

export type MetricDirection = "higher_is_better" | "lower_is_better";

export interface CanonicalMetricDefinition {
  name: string;
  type: "ratio" | "count" | "duration" | "score" | "cost";
  // canonical adapter（metric-definition.schema.json 規定必填）永遠會有值；
  // manifest adapter 的 metric catalog 沒宣告 direction 時必須維持 undefined，
  // 不得預設猜一個方向——沒有方向定義就只能顯示中性的 change（規則 6）。
  direction?: MetricDirection;
  aggregation: string;
  implementation: string;
  // 以下三個只有 manifest adapter 會填（viewer.json 的 metrics[] catalog）；
  // canonical adapter 的 metric-definition.schema.json 沒有這些欄位。
  displayName?: string;
  unit?: string;
  format?: string;
  // metric-definition.schema.json 的 validity 區塊，整塊選填。缺它代表這個指標
  // 還沒被驗證過——那是合法狀態，但它就不能當 primary metric，也不能承載門檻。
  validity?: CanonicalMetricValidity;
  sourcePath: string;
}

export interface CanonicalMetricValidity {
  intendedUse?: string;
  evidenceRefs: string[];
  limitations: string[];
  // 沒宣告就是沒資格。UI 顯示時「未宣告」與「明確為 false」要分得出來，
  // 前者是還沒做，後者是做過而且判定不適合，兩者不是同一件事。
  thresholdEligible?: boolean;
}

// run-envelope 的 artifacts[] 只是相對於 project root 的字串路徑；
// 這裡把它跟來源 run/experiment 綁在一起，方便 Artifacts 分頁按 run 分組顯示。
export interface CanonicalArtifact {
  path: string;
  runId: string;
  experimentId: string;
}

export interface ProjectDiagnostic {
  level: "error" | "warning";
  message: string;
  sourcePath?: string;
}

// manifest-driven generic adapter 讀到、但沒有對應 canonical 型別的額外 collection，
// 原樣保留成 key-value，UI 只能列表顯示，不做語意詮釋。
export interface GenericRecord {
  id: string;
  sourcePath: string;
  fields: Record<string, unknown>;
}

export interface GenericRecordCollection {
  name: string;
  // manifest 宣告的欄位（dot-path），Records 分頁依這個動態畫欄位，
  // 不是寫死只顯示 id/source。沒宣告就是空陣列，UI 退回顯示 id/source。
  columns: string[];
  records: GenericRecord[];
}

export type ProjectAdapterKind = "canonical" | "manifest";

// loadProject() 的回傳型別——UI 只認這一個介面，不知道底下是 canonical records
// 還是 viewer.json manifest 產生的，也不知道實體 JSON 檔案長怎樣或路徑怎麼拼。
export interface ProjectSnapshot {
  // PROJECT_ROOT 契約：使用者可能指到 project 根目錄，也可能（沿用舊習慣）直接指到
  // `<projectRoot>/records/experiments`——兩者都會被 Rust 端解析回同一組
  // (projectRoot, recordsRoot)。UI 一律顯示 projectRoot，artifact containment
  // 永遠以 projectRoot 為界，不是 recordsRoot。
  projectRoot: string;
  recordsRoot: string;
  // 純粹給 Diagnostics 顯示用（輸入路徑的形狀：windows_drive／unc／wsl_unc／relative）。
  rootKind: string;
  adapterKind: ProjectAdapterKind;
  experiments: CanonicalExperiment[];
  comparisons: CanonicalComparison[];
  metricDefinitions: CanonicalMetricDefinition[];
  artifacts: CanonicalArtifact[];
  genericCollections: GenericRecordCollection[];
  diagnostics: ProjectDiagnostic[];
}
