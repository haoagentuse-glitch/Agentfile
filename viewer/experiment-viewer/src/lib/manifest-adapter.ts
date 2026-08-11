// Manifest-Driven Generic JSON Adapter — Adapter B：沒有 canonical records 慣例時，
// 讀 `<projectRoot>/records/experiments/viewer.json` 描述的 dot-path mapping，把任意
// JSON 專案投影成 ProjectSnapshot。manifest 檔案本身固定放在 records/experiments/ 底下，
// 但裡面宣告的 `dir` 欄位（experiments.dir／runs.dir／collections.*.dir）是相對 projectRoot
// 解析——generic 專案的資料不一定跟這包自己的 records/experiments 慣例長在同一棵樹下，
// viewer.json 只是一個固定位置的指標檔，指向 projectRoot 底下實際的資料夾。
// 只支援受限、可測的 dot-path（見 dot-path.ts），不引入 JSONPath engine 或任意 script。

import type {
  CanonicalArtifact,
  CanonicalExperiment,
  CanonicalMetricDefinition,
  CanonicalRun,
  GenericRecord,
  GenericRecordCollection,
  MetricDirection,
  ProjectDiagnostic,
  ProjectSnapshot,
} from "./canonical";
import { getByPath, getNumberRecordByPath, getStringByPath } from "./dot-path";
import type { ProjectLayout } from "./tauri-fs";
import { listProjectDir, readProjectFile } from "./tauri-fs";

const METRIC_DIRECTIONS: readonly MetricDirection[] = ["higher_is_better", "lower_is_better"];

export interface ViewerManifestMetricSpec {
  name: string;
  displayName?: string;
  unit?: string;
  format?: string;
  // 沒宣告就是 undefined,不得預設猜一個方向——UI 只能在有方向時才顯示 improvement/regression。
  direction?: MetricDirection;
}

export interface ViewerManifestCollectionSpec {
  dir: string;
  id: string;
  // Records 分頁依這個動態畫欄位；沒宣告就退回只顯示 id/source。
  columns?: string[];
}

export interface ViewerManifestExperimentSpec extends ViewerManifestCollectionSpec {
  displayName?: string;
  status?: string;
  createdAt?: string;
}

export interface ViewerManifestRunSpec extends ViewerManifestCollectionSpec {
  experimentId: string;
  status?: string;
  createdAt?: string;
  metricsPath?: string;
  artifactsPath?: string;
}

export interface ViewerManifest {
  version: 1;
  experiments: ViewerManifestExperimentSpec;
  runs: ViewerManifestRunSpec;
  metrics?: ViewerManifestMetricSpec[];
  collections?: Record<string, ViewerManifestCollectionSpec>;
}

export class ViewerManifestError extends Error {}

function requireString(obj: Record<string, unknown>, field: string, context: string): string {
  const value = obj[field];
  if (typeof value !== "string" || value.length === 0) {
    throw new ViewerManifestError(`viewer.json: ${context}.${field} 必須是非空字串`);
  }
  return value;
}

function optionalString(obj: Record<string, unknown>, field: string, context: string): string | undefined {
  if (!(field in obj) || obj[field] === undefined) return undefined;
  if (typeof obj[field] !== "string") {
    throw new ViewerManifestError(`viewer.json: ${context}.${field} 必須是字串`);
  }
  return obj[field] as string;
}

function optionalStringArray(obj: Record<string, unknown>, field: string, context: string): string[] | undefined {
  if (!(field in obj) || obj[field] === undefined) return undefined;
  const value = obj[field];
  if (!Array.isArray(value) || value.some((v) => typeof v !== "string")) {
    throw new ViewerManifestError(`viewer.json: ${context}.${field} 必須是字串陣列`);
  }
  return value as string[];
}

function optionalDirection(obj: Record<string, unknown>, field: string, context: string): MetricDirection | undefined {
  if (!(field in obj) || obj[field] === undefined) return undefined;
  const value = obj[field];
  if (typeof value !== "string" || !METRIC_DIRECTIONS.includes(value as MetricDirection)) {
    throw new ViewerManifestError(`viewer.json: ${context}.${field} 必須是 "higher_is_better" 或 "lower_is_better"`);
  }
  return value as MetricDirection;
}

function parseCollectionSpec(raw: unknown, context: string): ViewerManifestCollectionSpec {
  if (typeof raw !== "object" || raw === null) {
    throw new ViewerManifestError(`viewer.json: ${context} 必須是 object`);
  }
  const obj = raw as Record<string, unknown>;
  return {
    dir: requireString(obj, "dir", context),
    id: requireString(obj, "id", context),
    columns: optionalStringArray(obj, "columns", context),
  };
}

export function parseViewerManifest(raw: unknown): ViewerManifest {
  if (typeof raw !== "object" || raw === null) {
    throw new ViewerManifestError("viewer.json 必須是一個 JSON object");
  }
  const obj = raw as Record<string, unknown>;
  if (obj.version !== 1) {
    throw new ViewerManifestError('viewer.json: "version" 必須是 1（目前唯一支援的版本）');
  }

  const experimentsRaw = obj.experiments;
  if (typeof experimentsRaw !== "object" || experimentsRaw === null) {
    throw new ViewerManifestError('viewer.json: "experiments" 為必填 object');
  }
  const experimentsObj = experimentsRaw as Record<string, unknown>;
  const experiments: ViewerManifestExperimentSpec = {
    ...parseCollectionSpec(experimentsObj, "experiments"),
    displayName: optionalString(experimentsObj, "displayName", "experiments"),
    status: optionalString(experimentsObj, "status", "experiments"),
    createdAt: optionalString(experimentsObj, "createdAt", "experiments"),
  };

  const runsRaw = obj.runs;
  if (typeof runsRaw !== "object" || runsRaw === null) {
    throw new ViewerManifestError('viewer.json: "runs" 為必填 object');
  }
  const runsObj = runsRaw as Record<string, unknown>;
  const runs: ViewerManifestRunSpec = {
    ...parseCollectionSpec(runsObj, "runs"),
    experimentId: requireString(runsObj, "experimentId", "runs"),
    status: optionalString(runsObj, "status", "runs"),
    createdAt: optionalString(runsObj, "createdAt", "runs"),
    metricsPath: optionalString(runsObj, "metricsPath", "runs"),
    artifactsPath: optionalString(runsObj, "artifactsPath", "runs"),
  };

  let metrics: ViewerManifestMetricSpec[] | undefined;
  if (obj.metrics !== undefined) {
    if (!Array.isArray(obj.metrics)) {
      throw new ViewerManifestError('viewer.json: "metrics" 必須是陣列');
    }
    metrics = obj.metrics.map((entry, i) => {
      const context = `metrics[${i}]`;
      if (typeof entry !== "object" || entry === null) {
        throw new ViewerManifestError(`viewer.json: ${context} 必須是 object`);
      }
      const entryObj = entry as Record<string, unknown>;
      return {
        name: requireString(entryObj, "name", context),
        displayName: optionalString(entryObj, "displayName", context),
        unit: optionalString(entryObj, "unit", context),
        format: optionalString(entryObj, "format", context),
        direction: optionalDirection(entryObj, "direction", context),
      };
    });
  }

  let collections: Record<string, ViewerManifestCollectionSpec> | undefined;
  if (obj.collections !== undefined) {
    if (typeof obj.collections !== "object" || obj.collections === null) {
      throw new ViewerManifestError('viewer.json: "collections" 必須是 object');
    }
    collections = {};
    for (const [name, spec] of Object.entries(obj.collections as Record<string, unknown>)) {
      collections[name] = parseCollectionSpec(spec, `collections.${name}`);
    }
  }

  return { version: 1, experiments, runs, metrics, collections };
}

async function readJsonRecords(
  projectRoot: string,
  dir: string,
  diagnostics: ProjectDiagnostic[]
): Promise<Array<{ path: string; data: Record<string, unknown> }>> {
  let entries: string[];
  try {
    entries = await listProjectDir(projectRoot, dir);
  } catch (e) {
    diagnostics.push({ level: "error", message: String(e), sourcePath: dir });
    return [];
  }

  const results: Array<{ path: string; data: Record<string, unknown> }> = [];
  for (const path of entries) {
    if (!path.endsWith(".json")) continue;
    try {
      const text = await readProjectFile(projectRoot, path);
      results.push({ path, data: JSON.parse(text) });
    } catch (e) {
      diagnostics.push({ level: "error", message: String(e), sourcePath: path });
    }
  }
  return results;
}

export async function loadManifestProject(
  layout: ProjectLayout,
  manifest: ViewerManifest
): Promise<ProjectSnapshot> {
  const { projectRoot, recordsRoot, rootKind } = layout;
  const diagnostics: ProjectDiagnostic[] = [];
  const experiments = new Map<string, CanonicalExperiment>();

  const experimentFiles = await readJsonRecords(projectRoot, manifest.experiments.dir, diagnostics);
  for (const { path, data } of experimentFiles) {
    const id = getStringByPath(data, manifest.experiments.id);
    if (!id) {
      diagnostics.push({ level: "error", message: `缺少 experiments.id 對應的欄位（${manifest.experiments.id}）`, sourcePath: path });
      continue;
    }
    experiments.set(id, {
      experimentId: id,
      status: getStringByPath(data, manifest.experiments.status) ?? "unknown",
      question: getStringByPath(data, manifest.experiments.displayName),
      hypothesis: undefined,
      primaryMetric: undefined,
      secondaryMetrics: [],
      runs: [],
      claims: [],
      gateState: null,
      sourcePath: path,
    });
  }

  const artifacts: CanonicalArtifact[] = [];
  const runFiles = await readJsonRecords(projectRoot, manifest.runs.dir, diagnostics);
  for (const { path, data } of runFiles) {
    const runId = getStringByPath(data, manifest.runs.id);
    const experimentId = getStringByPath(data, manifest.runs.experimentId);
    if (!runId || !experimentId) {
      diagnostics.push({
        level: "error",
        message: `缺少 runs.id 或 runs.experimentId 對應的欄位（${manifest.runs.id} / ${manifest.runs.experimentId}）`,
        sourcePath: path,
      });
      continue;
    }
    const metrics = getNumberRecordByPath(data, manifest.runs.metricsPath ?? "metrics");
    const artifactPaths = manifest.runs.artifactsPath
      ? ((getByPath(data, manifest.runs.artifactsPath) as unknown[] | undefined)?.filter(
          (v): v is string => typeof v === "string"
        ) ?? [])
      : [];

    const run: CanonicalRun = {
      runId,
      experimentId,
      status: getStringByPath(data, manifest.runs.status) ?? "unknown",
      createdAt: getStringByPath(data, manifest.runs.createdAt),
      metrics,
      artifacts: artifactPaths,
      sourcePath: path,
    };

    const experiment = experiments.get(experimentId);
    if (experiment) {
      experiment.runs.push(run);
    } else {
      diagnostics.push({
        level: "warning",
        message: `run ${runId} 找不到對應的 experiment（experiment_id=${experimentId}）`,
        sourcePath: path,
      });
    }
    for (const artifactPath of artifactPaths) {
      artifacts.push({ path: artifactPath, runId, experimentId });
    }
  }

  const metricDefinitions: CanonicalMetricDefinition[] = (manifest.metrics ?? []).map((spec) => ({
    name: spec.name,
    type: "score",
    // 沒宣告 direction 就維持 undefined,不得預設猜一個方向（規則 6）。
    direction: spec.direction,
    aggregation: "unknown",
    implementation: spec.name,
    displayName: spec.displayName,
    unit: spec.unit,
    format: spec.format,
    sourcePath: "records/experiments/viewer.json",
  }));

  const genericCollections: GenericRecordCollection[] = [];
  for (const [name, spec] of Object.entries(manifest.collections ?? {})) {
    const files = await readJsonRecords(projectRoot, spec.dir, diagnostics);
    const records: GenericRecord[] = [];
    for (const { path, data } of files) {
      const id = getStringByPath(data, spec.id) ?? path;
      records.push({ id, sourcePath: path, fields: data });
    }
    genericCollections.push({ name, columns: spec.columns ?? [], records });
  }

  return {
    projectRoot,
    recordsRoot,
    rootKind,
    adapterKind: "manifest",
    experiments: Array.from(experiments.values()),
    comparisons: [],
    metricDefinitions,
    artifacts,
    genericCollections,
    diagnostics,
  };
}
