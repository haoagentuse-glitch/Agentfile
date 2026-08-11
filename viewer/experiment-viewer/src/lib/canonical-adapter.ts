// Canonical Records Adapter — Adapter A：讀這包自己的 records/experiments/ 慣例目錄。
// 固定目錄慣例（跟 compare-runs / claim-audit / compute-gate 幾支 SKILL.md 的輸出路徑一致），
// 全部相對 projectRoot（不是 recordsRoot）——這幾個路徑字串是寫死的常數，不是用檔案列表
// 結果現拼出來的，Vue 端沒有任何 `${dir}/${name}` 這種字串組裝：
//   <projectRoot>/records/experiments/definitions/<experiment_id>.json      Experiment Contract
//   <projectRoot>/records/experiments/runs/<run_id>.json                    Run Envelope
//   <projectRoot>/records/experiments/claims/<claim_id>.json                Claim
//   <projectRoot>/records/experiments/audits/<claim_id>.json                Claim Audit Result
//   <projectRoot>/records/experiments/comparisons/<run-a>__<run-b>.json     Comparison Result
//   <projectRoot>/records/experiments/gates/<experiment_id>.json            Gate State（append-only）
//   <projectRoot>/records/experiments/metrics/<metric_name>.json            Metric Definition
// 目錄不存在＝這個 profile 還沒有任何這類紀錄，是空狀態不是錯誤（Rust 端的 list_project_dir
// 已經把 NotFound 轉成空陣列）；其他 I/O 錯誤（權限、跳脫 root）會被丟出來，這裡接住記成
// 一筆 diagnostic，不吞掉、不裝作空狀態。單一檔案壞掉只記一筆 diagnostic，不拖垮其他資料。

import type {
  CanonicalArtifact,
  CanonicalClaim,
  CanonicalComparison,
  CanonicalExperiment,
  CanonicalMetricDefinition,
  CanonicalRun,
  ProjectDiagnostic,
  ProjectSnapshot,
} from "./canonical";
import {
  adaptClaim,
  adaptClaimAuditResult,
  adaptComparisonResult,
  adaptExperimentContract,
  adaptGateState,
  adaptMetricDefinition,
  adaptRunEnvelope,
} from "./schema-adapter";
import type { ProjectLayout } from "./tauri-fs";
import { listProjectDir, readProjectFile } from "./tauri-fs";

const DEFINITIONS_DIR = "records/experiments/definitions";
const RUNS_DIR = "records/experiments/runs";
const CLAIMS_DIR = "records/experiments/claims";
const AUDITS_DIR = "records/experiments/audits";
const GATES_DIR = "records/experiments/gates";
const COMPARISONS_DIR = "records/experiments/comparisons";
const METRICS_DIR = "records/experiments/metrics";

interface JsonFileOk {
  path: string;
  ok: true;
  data: Record<string, unknown>;
}
interface JsonFileErr {
  path: string;
  ok: false;
  error: string;
}
type JsonFileResult = JsonFileOk | JsonFileErr;

// dir 永遠是上面列出的其中一個字面常數；list_project_dir 回傳的路徑已經是
// Rust 端 PathBuf::join 組好、containment 驗證過的相對路徑，這裡原樣使用，不再拼接。
async function readJsonFiles(projectRoot: string, dir: string): Promise<JsonFileResult[]> {
  let entries: string[];
  try {
    entries = await listProjectDir(projectRoot, dir);
  } catch (e) {
    // 目錄本身讀取失敗（權限等），不是「不存在」——不能偽裝成空狀態,整個目錄記一筆錯誤。
    return [{ path: dir, ok: false, error: String(e) }];
  }

  const results: JsonFileResult[] = [];
  for (const path of entries) {
    if (!path.endsWith(".json")) continue;
    try {
      const text = await readProjectFile(projectRoot, path);
      results.push({ path, ok: true, data: JSON.parse(text) });
    } catch (e) {
      results.push({ path, ok: false, error: String(e) });
    }
  }
  return results;
}

export async function loadCanonicalProject(layout: ProjectLayout): Promise<ProjectSnapshot> {
  const { projectRoot, recordsRoot, rootKind } = layout;
  const diagnostics: ProjectDiagnostic[] = [];
  const experiments = new Map<string, CanonicalExperiment>();
  const claimsById = new Map<string, CanonicalClaim>();
  const artifacts: CanonicalArtifact[] = [];

  for (const file of await readJsonFiles(projectRoot, DEFINITIONS_DIR)) {
    if (!file.ok) {
      diagnostics.push({ level: "error", message: file.error, sourcePath: file.path });
      continue;
    }
    try {
      const contract = adaptExperimentContract(file.data, file.path);
      experiments.set(contract.experimentId, { ...contract, runs: [], claims: [], gateState: null });
    } catch (e) {
      diagnostics.push({ level: "error", message: String(e), sourcePath: file.path });
    }
  }

  for (const file of await readJsonFiles(projectRoot, RUNS_DIR)) {
    if (!file.ok) {
      diagnostics.push({ level: "error", message: file.error, sourcePath: file.path });
      continue;
    }
    try {
      const run: CanonicalRun = adaptRunEnvelope(file.data, file.path);
      const experiment = experiments.get(run.experimentId);
      if (experiment) {
        experiment.runs.push(run);
      } else {
        diagnostics.push({
          level: "warning",
          message: `run ${run.runId} 找不到對應的 experiment contract（definitions/ 底下沒有 experiment_id=${run.experimentId}）`,
          sourcePath: file.path,
        });
      }
      for (const artifactPath of run.artifacts) {
        artifacts.push({ path: artifactPath, runId: run.runId, experimentId: run.experimentId });
      }
    } catch (e) {
      diagnostics.push({ level: "error", message: String(e), sourcePath: file.path });
    }
  }

  for (const file of await readJsonFiles(projectRoot, CLAIMS_DIR)) {
    if (!file.ok) {
      diagnostics.push({ level: "error", message: file.error, sourcePath: file.path });
      continue;
    }
    try {
      const claim = adaptClaim(file.data, file.path);
      claimsById.set(claim.claimId, claim);
      const experiment = experiments.get(claim.experimentId);
      if (experiment) {
        experiment.claims.push(claim);
      } else {
        diagnostics.push({
          level: "warning",
          message: `claim ${claim.claimId} 找不到對應的 experiment contract（experiment_id=${claim.experimentId}）`,
          sourcePath: file.path,
        });
      }
    } catch (e) {
      diagnostics.push({ level: "error", message: String(e), sourcePath: file.path });
    }
  }

  for (const file of await readJsonFiles(projectRoot, AUDITS_DIR)) {
    if (!file.ok) {
      diagnostics.push({ level: "error", message: file.error, sourcePath: file.path });
      continue;
    }
    try {
      const audit = adaptClaimAuditResult(file.data, file.path);
      const claim = claimsById.get(audit.claimId);
      if (claim) {
        claim.auditResult = audit;
      } else {
        diagnostics.push({
          level: "warning",
          message: `claim audit result 找不到對應的 claim（claim_id=${audit.claimId}）`,
          sourcePath: file.path,
        });
      }
    } catch (e) {
      diagnostics.push({ level: "error", message: String(e), sourcePath: file.path });
    }
  }

  for (const file of await readJsonFiles(projectRoot, GATES_DIR)) {
    if (!file.ok) {
      diagnostics.push({ level: "error", message: file.error, sourcePath: file.path });
      continue;
    }
    try {
      const gateState = adaptGateState(file.data, file.path);
      const experiment = experiments.get(gateState.experimentId);
      if (experiment) {
        experiment.gateState = gateState;
      } else {
        diagnostics.push({
          level: "warning",
          message: `gate state 找不到對應的 experiment contract（experiment_id=${gateState.experimentId}）`,
          sourcePath: file.path,
        });
      }
    } catch (e) {
      diagnostics.push({ level: "error", message: String(e), sourcePath: file.path });
    }
  }

  const comparisons: CanonicalComparison[] = [];
  for (const file of await readJsonFiles(projectRoot, COMPARISONS_DIR)) {
    if (!file.ok) {
      diagnostics.push({ level: "error", message: file.error, sourcePath: file.path });
      continue;
    }
    try {
      comparisons.push(adaptComparisonResult(file.data, file.path));
    } catch (e) {
      diagnostics.push({ level: "error", message: String(e), sourcePath: file.path });
    }
  }

  const metricDefinitions: CanonicalMetricDefinition[] = [];
  for (const file of await readJsonFiles(projectRoot, METRICS_DIR)) {
    if (!file.ok) {
      diagnostics.push({ level: "error", message: file.error, sourcePath: file.path });
      continue;
    }
    try {
      metricDefinitions.push(adaptMetricDefinition(file.data, file.path));
    } catch (e) {
      diagnostics.push({ level: "error", message: String(e), sourcePath: file.path });
    }
  }

  return {
    projectRoot,
    recordsRoot,
    rootKind,
    adapterKind: "canonical",
    experiments: Array.from(experiments.values()),
    comparisons,
    metricDefinitions,
    artifacts,
    genericCollections: [],
    diagnostics,
  };
}
