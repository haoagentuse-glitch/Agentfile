// Schema Adapter — 把 records/experiments/ 底下目前這包定義的 schema 轉成 canonical model。
// 只認 profiles/experimental/records/experiments/schemas/ 現有的欄位；schema 改版時只改這個檔案。

import type {
  CanonicalClaim,
  CanonicalClaimAuditResult,
  CanonicalComparison,
  CanonicalComparisonEstimate,
  CanonicalDerivation,
  CanonicalDiagnosis,
  CanonicalEvidenceRef,
  CanonicalExperiment,
  CanonicalGateHistoryEntry,
  CanonicalGateState,
  CanonicalEstimateComponent,
  CanonicalEstimateInterval,
  CanonicalMetricDefinition,
  CanonicalMetricDiff,
  CanonicalProducer,
  CanonicalRun,
  CanonicalRunFailure,
  ClaimStatus,
  ClaimVerdict,
  DecisionConclusion,
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

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

// provenance.schema.json#/$defs/producer → CanonicalProducer。
// 沒有 producer 是合法的（人手寫的紀錄不必假造一個），回 null 讓 UI 照實說「未記錄」。
function adaptProducer(value: unknown): CanonicalProducer | null {
  const raw = record(value);
  if (!raw) return null;
  return {
    kind: String(raw.kind ?? "unknown"),
    name: String(raw.name ?? "unknown"),
    model: raw.model as string | undefined,
    promptId: raw.prompt_id as string | undefined,
    promptHash: raw.prompt_hash as string | undefined,
    inputRefs: list(raw.input_refs).map(String),
    toolCallsArtifact: raw.tool_calls_artifact as string | undefined,
    createdAt: raw.created_at as string | undefined,
  };
}

// experiment-contract.schema.json 的 derivation 區塊 → CanonicalDerivation。
function adaptDerivation(value: unknown): CanonicalDerivation | null {
  const raw = record(value);
  if (!raw) return null;
  const mechanism = record(raw.mechanism_model) ?? {};
  return {
    primitives: list(raw.primitives).map((item) => {
      const p = record(item) ?? {};
      return { id: String(p.id ?? ""), definition: String(p.definition ?? "") };
    }),
    assumptions: list(raw.assumptions).map((item) => {
      const a = record(item) ?? {};
      return {
        id: String(a.id ?? ""),
        statement: String(a.statement ?? ""),
        status: String(a.status ?? "unverified"),
      };
    }),
    mechanismSummary: String(mechanism.summary ?? ""),
    mechanismVariables: list(mechanism.variables).map(String),
    tension: String(raw.tension ?? ""),
    falsifier: String(raw.falsifier ?? ""),
    minimalDecisiveTest: String(raw.minimal_decisive_test ?? ""),
    expectedObservations: list(raw.expected_observations).map(String),
    failureUpdate: list(raw.failure_update).map((item) => {
      const f = record(item) ?? {};
      return {
        when: String(f.when ?? ""),
        updateAssumptionId: String(f.update_assumption_id ?? ""),
        to: String(f.to ?? ""),
      };
    }),
    sourceRefs: list(raw.source_refs).map(String),
    counterexamples: list(raw.counterexamples).map(String),
    noveltyStatus: String(raw.novelty_status ?? "unverified"),
  };
}

// experiment-contract.schema.json → CanonicalExperiment（runs／claims／gateState／diagnoses 留空，由 canonical-adapter 填入）
export function adaptExperimentContract(
  raw: Record<string, unknown>,
  sourcePath: string
): Omit<CanonicalExperiment, "runs" | "claims" | "gateState" | "diagnoses"> {
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
    eligibleRunStages:
      (record(raw.evidence_policy)?.eligible_run_stages as string[]) ?? [],
    derivation: adaptDerivation(raw.derivation),
    producer: adaptProducer(raw.producer),
    sourcePath,
  };
}

// failure-diagnosis.schema.json → CanonicalDiagnosis
export function adaptFailureDiagnosis(
  raw: Record<string, unknown>,
  sourcePath: string
): CanonicalDiagnosis {
  const diagnosisId = requireField(raw, "diagnosis_id", sourcePath) as string;
  const experimentId = requireField(raw, "experiment_id", sourcePath) as string;
  const diagnosedAt = requireField(raw, "diagnosed_at", sourcePath) as string;
  const subject = record(requireField(raw, "subject", sourcePath)) ?? {};
  const nextTest = record(requireField(raw, "cheapest_next_test", sourcePath)) ?? {};

  return {
    diagnosisId,
    experimentId,
    diagnosedAt,
    subject: { kind: String(subject.kind ?? ""), ref: String(subject.ref ?? "") },
    deterministicFacts: list(raw.deterministic_facts).map((item) => {
      const f = record(item) ?? {};
      return {
        fact: String(f.fact ?? ""),
        sourceRef: String(f.source_ref ?? ""),
        locator: f.locator as string | undefined,
      };
    }),
    hypotheses: list(raw.hypotheses).map((item) => {
      const h = record(item) ?? {};
      return {
        id: String(h.id ?? ""),
        failureClass: String(h.failure_class ?? ""),
        statement: String(h.statement ?? ""),
        confidence: String(h.confidence ?? ""),
        discriminatingObservation: h.discriminating_observation as string | undefined,
      };
    }),
    excludedClasses: list(raw.excluded_classes).map((item) => {
      const e = record(item) ?? {};
      return { failureClass: String(e.failure_class ?? ""), reason: String(e.reason ?? "") };
    }),
    cheapestNextTest: {
      description: String(nextTest.description ?? ""),
      command: nextTest.command as string | undefined,
      distinguishes: list(nextTest.distinguishes).map(String),
      estimatedCost: nextTest.estimated_cost as string | undefined,
    },
    producer: adaptProducer(raw.producer),
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
    stage: raw.stage as string | undefined,
    parentRunId: raw.parent_run_id as string | undefined,
    attemptKind: raw.attempt_kind as string | undefined,
    failure: adaptRunFailure(raw.failure),
    metrics: (raw.metrics as Record<string, number>) ?? {},
    artifacts: (raw.artifacts as string[]) ?? [],
    invalidReason: raw.invalid_reason as string | undefined,
    sourcePath,
  };
}

function adaptRunFailure(value: unknown): CanonicalRunFailure | undefined {
  const raw = record(value);
  if (!raw) return undefined;
  return {
    failureClass: String(raw.class ?? ""),
    phase: String(raw.phase ?? ""),
    exitCode: raw.exit_code as number | undefined,
    retriable: raw.retriable as boolean | undefined,
    errorArtifact: raw.error_artifact as string | undefined,
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
  const evidenceEligible = requireField(raw, "evidence_eligible", sourcePath) as boolean;
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

  const estimates = list(requireField(raw, "estimates", sourcePath)).map((item) =>
    adaptComparisonEstimate(item as Record<string, unknown>, sourcePath)
  );

  return {
    experimentId,
    runA,
    runB,
    comparisonValid,
    evidenceEligible,
    evidenceReasons: (raw.evidence_reasons as string[]) ?? [],
    confounded,
    confoundedReasons: (raw.confounded_reasons as string[]) ?? [],
    notes: (raw.notes as string[]) ?? [],
    metrics,
    estimates,
    sourcePath,
  };
}

function adaptInterval(raw: unknown): CanonicalEstimateInterval | null {
  if (raw === null || typeof raw !== "object") return null;
  const interval = raw as Record<string, unknown>;
  return {
    lower: interval.lower as number,
    upper: interval.upper as number,
    confidenceLevel: interval.confidence_level as number,
    method: String(interval.method ?? ""),
  };
}

// comparison-estimate.schema.json → CanonicalComparisonEstimate。
// 只搬欄位，不重算：point estimate、interval 與 decision 都由 compare-runs 寫死在紀錄裡。
export function adaptComparisonEstimate(
  raw: Record<string, unknown>,
  sourcePath: string
): CanonicalComparisonEstimate {
  const decision = requireField(raw, "decision", sourcePath) as Record<string, unknown>;
  const sampleSize = (raw.sample_size as Record<string, unknown>) ?? {};
  const components: CanonicalEstimateComponent[] = list(raw.component_estimates).map((item) => {
    const component = item as Record<string, unknown>;
    return {
      id: String(component.id ?? ""),
      pointEstimate: component.point_estimate as number,
      interval: adaptInterval(component.interval ?? null),
    };
  });

  return {
    estimandId: requireField(raw, "estimand_id", sourcePath) as string,
    estimatorId: requireField(raw, "estimator_id", sourcePath) as string,
    pointEstimate: requireField(raw, "point_estimate", sourcePath) as number,
    interval: adaptInterval(requireField(raw, "interval", sourcePath)),
    observations: (sampleSize.observations as number | undefined) ?? null,
    clusters: (sampleSize.clusters as number | undefined) ?? null,
    methodRef: requireField(raw, "method_ref", sourcePath) as string,
    componentEstimates: components,
    decision: {
      ruleId: requireField(decision, "rule_id", sourcePath) as string,
      conclusion: requireField(decision, "conclusion", sourcePath) as DecisionConclusion,
      reasonCodes: (decision.reason_codes as string[]) ?? [],
    },
  };
}

// claim.schema.json → CanonicalClaim
export function adaptClaim(raw: Record<string, unknown>, sourcePath: string): CanonicalClaim {
  const claimId = requireField(raw, "claim_id", sourcePath) as string;
  const statement = requireField(raw, "statement", sourcePath) as string;
  const experimentId = requireField(raw, "experiment_id", sourcePath) as string;
  const comparisonRef = requireField(raw, "comparison_ref", sourcePath) as string;
  const estimandId = requireField(raw, "estimand_id", sourcePath) as string;
  const expectedDirection = requireField(raw, "expected_direction", sourcePath) as
    | "increase"
    | "decrease";
  const expectedConclusion = requireField(
    raw,
    "expected_conclusion",
    sourcePath
  ) as DecisionConclusion;
  const scope = requireField(raw, "scope", sourcePath) as string;
  const createdAt = requireField(raw, "created_at", sourcePath) as string;

  return {
    claimId,
    statement,
    experimentId,
    comparisonRef,
    estimandId,
    expectedDirection,
    expectedConclusion,
    statedMagnitude: raw.stated_magnitude as number | undefined,
    magnitudeType: raw.magnitude_type as "absolute" | "relative" | undefined,
    scope,
    createdAt,
    claimType: raw.claim_type as string | undefined,
    // 沒寫 status 就是 candidate（schema 的 default）；refuted 與 inconclusive
    // 是正式終態，載進來照實顯示，不因為不好看就過濾掉。
    status: (raw.status as ClaimStatus) ?? "candidate",
    supersededBy: raw.superseded_by as string | undefined,
    evidenceRefs: list(raw.evidence_refs).map((item) => {
      const e = record(item) ?? {};
      return {
        kind: String(e.kind ?? "artifact") as CanonicalEvidenceRef["kind"],
        ref: String(e.ref ?? ""),
        locator: e.locator as string | undefined,
        hash: e.hash as string | undefined,
      };
    }),
    producer: adaptProducer(raw.producer),
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
  const evidenceEligible = requireField(raw, "evidence_eligible", sourcePath) as boolean;
  // scope_verdict 還是 pending 時 schema 規定不得寫 final_verdict——缺這欄不是壞資料。
  const finalVerdict = (raw.final_verdict as ClaimVerdict | undefined) ?? "pending";

  if (!("mechanical_pass" in mechanical)) {
    throw new SchemaAdapterError('mechanical 底下缺少 "mechanical_pass"', sourcePath);
  }

  return {
    claimId,
    auditedAt,
    mechanicalPass: Boolean(mechanical.mechanical_pass),
    evidenceEligible,
    evidenceReasons: (raw.evidence_reasons as string[]) ?? [],
    referenceExists: Boolean(mechanical.reference_exists),
    comparisonValid: (mechanical.comparison_valid as boolean | null) ?? null,
    estimandExists: (mechanical.estimand_exists as boolean | null) ?? null,
    directionMatches: (mechanical.direction_matches as boolean | null) ?? null,
    conclusionMatches: (mechanical.conclusion_matches as boolean | null) ?? null,
    magnitudeMatches: (mechanical.magnitude_matches as boolean | null) ?? null,
    mechanicalReasons: (raw.mechanical_reasons as string[]) ?? [],
    scopeVerdict: (raw.scope_verdict as ClaimVerdict) ?? "pending",
    scopeReasoning: raw.scope_reasoning as string | undefined,
    finalVerdict,
    entailment: adaptVerdictAxis(raw.entailment),
    intendedQuestionFit: adaptVerdictAxis(raw.intended_question_fit),
    novelty: adaptNovelty(raw.novelty),
    reviewIndependence: adaptIndependence(raw.review_independence),
    producer: adaptProducer(raw.producer),
    sourcePath,
  };
}

function adaptVerdictAxis(value: unknown): { verdict: string; reasoning?: string } | undefined {
  const raw = record(value);
  if (!raw) return undefined;
  return { verdict: String(raw.verdict ?? ""), reasoning: raw.reasoning as string | undefined };
}

function adaptNovelty(value: unknown): { status: string; sourceRefs: string[]; reasoning?: string } | undefined {
  const raw = record(value);
  if (!raw) return undefined;
  return {
    status: String(raw.status ?? "unverified"),
    sourceRefs: list(raw.source_refs).map(String),
    reasoning: raw.reasoning as string | undefined,
  };
}

function adaptIndependence(
  value: unknown
): { independent: boolean; reviewerKind?: string; reason?: string } | undefined {
  const raw = record(value);
  if (!raw) return undefined;
  return {
    independent: Boolean(raw.independent),
    reviewerKind: raw.reviewer_kind as string | undefined,
    reason: raw.reason as string | undefined,
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
    evidenceEligible: Boolean(entry.evidence_eligible),
    evidenceReasons: (entry.evidence_reasons as string[]) ?? [],
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
