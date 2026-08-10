// Storage Adapter — v1 只有一種：讀本機檔案系統的 records/experiments/。
// 目錄慣例跟 compare-runs / claim-audit / compute-gate 幾支腳本的 SKILL.md 範例一致：
//   <root>/definitions/<experiment_id>.json   Experiment Contract
//   <root>/runs/<run_id>.json                 Run Envelope
//   <root>/claims/<claim_id>.json             Claim（claim-audit 的輸入）
//   <root>/gates/<experiment_id>.json         Gate State（每個 experiment 一份，append-only）
// comparison-result／claim-audit-result 兩種輸出路徑由呼叫者用 --output 自訂，沒有固定目錄慣例，
// 所以維持單檔挑選，不是資料夾掃描。

import { readDir, readTextFile } from "@tauri-apps/plugin-fs";
import type {
  CanonicalClaim,
  CanonicalClaimAuditResult,
  CanonicalComparison,
  CanonicalExperiment,
  CanonicalRun,
} from "./canonical";
import {
  adaptClaim,
  adaptClaimAuditResult,
  adaptComparisonResult,
  adaptExperimentContract,
  adaptGateState,
  adaptRunEnvelope,
} from "./schema-adapter";

async function readJsonFiles(dirPath: string): Promise<Array<{ path: string; data: Record<string, unknown> }>> {
  let entries;
  try {
    entries = await readDir(dirPath);
  } catch {
    // 目錄不存在代表這個 profile 還沒有任何 run/experiment 紀錄，不是錯誤。
    return [];
  }
  const results: Array<{ path: string; data: Record<string, unknown> }> = [];
  for (const entry of entries) {
    if (!entry.name?.endsWith(".json")) continue;
    const path = `${dirPath}/${entry.name}`;
    const text = await readTextFile(path);
    results.push({ path, data: JSON.parse(text) });
  }
  return results;
}

export interface LoadResult {
  experiments: CanonicalExperiment[];
  errors: string[];
}

// records/experiments/ 底下的 definitions/ 與 runs/ 聯集組成 canonical model，
// 一份 run 壞了不擋住其他資料——錯誤收集起來回報，不整包載入失敗（Explicit Over Implicit）。
export async function loadRecordsRoot(root: string): Promise<LoadResult> {
  const errors: string[] = [];
  const experiments = new Map<string, CanonicalExperiment>();

  const contractFiles = await readJsonFiles(`${root}/definitions`);
  for (const { path, data } of contractFiles) {
    try {
      const contract = adaptExperimentContract(data, path);
      experiments.set(contract.experimentId, { ...contract, runs: [], claims: [], gateState: null });
    } catch (e) {
      errors.push(String(e));
    }
  }

  const runFiles = await readJsonFiles(`${root}/runs`);
  const orphanRuns: CanonicalRun[] = [];
  for (const { path, data } of runFiles) {
    try {
      const run = adaptRunEnvelope(data, path);
      const experiment = experiments.get(run.experimentId);
      if (experiment) {
        experiment.runs.push(run);
      } else {
        orphanRuns.push(run);
      }
    } catch (e) {
      errors.push(String(e));
    }
  }
  if (orphanRuns.length > 0) {
    errors.push(
      `${orphanRuns.length} 個 run 找不到對應的 experiment contract（definitions/ 底下沒有同名 experiment_id）：` +
        orphanRuns.map((r) => r.runId).join(", ")
    );
  }

  const claimFiles = await readJsonFiles(`${root}/claims`);
  const orphanClaims: CanonicalClaim[] = [];
  for (const { path, data } of claimFiles) {
    try {
      const claim = adaptClaim(data, path);
      const experiment = experiments.get(claim.experimentId);
      if (experiment) {
        experiment.claims.push(claim);
      } else {
        orphanClaims.push(claim);
      }
    } catch (e) {
      errors.push(String(e));
    }
  }
  if (orphanClaims.length > 0) {
    errors.push(
      `${orphanClaims.length} 個 claim 找不到對應的 experiment contract：` +
        orphanClaims.map((c) => c.claimId).join(", ")
    );
  }

  const gateFiles = await readJsonFiles(`${root}/gates`);
  for (const { path, data } of gateFiles) {
    try {
      const gateState = adaptGateState(data, path);
      const experiment = experiments.get(gateState.experimentId);
      if (experiment) {
        experiment.gateState = gateState;
      } else {
        errors.push(`gate state ${path} 找不到對應的 experiment contract：${gateState.experimentId}`);
      }
    } catch (e) {
      errors.push(String(e));
    }
  }

  return { experiments: Array.from(experiments.values()), errors };
}

// compare-runs 的輸出路徑由呼叫者自訂（--output），沒有固定目錄慣例，所以是單檔挑選，不是資料夾掃描。
export async function loadComparisonFile(path: string): Promise<CanonicalComparison> {
  const text = await readTextFile(path);
  return adaptComparisonResult(JSON.parse(text), path);
}

// claim-audit 的輸出路徑同樣由呼叫者自訂（--output），單檔挑選。
export async function loadClaimAuditFile(path: string): Promise<CanonicalClaimAuditResult> {
  const text = await readTextFile(path);
  return adaptClaimAuditResult(JSON.parse(text), path);
}
