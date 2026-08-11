<script setup lang="ts">
import { computed, ref } from "vue";
import { use } from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import VChart from "vue-echarts";
import { useProjectStore } from "../store/project";
import { openArtifact } from "../lib/tauri-fs";
import { describeComparisonStatus } from "../lib/comparison-status";
import DataTable from "../components/DataTable.vue";
import Drawer from "../components/Drawer.vue";
import MetricValue from "../components/MetricValue.vue";
import RunSelector from "../components/RunSelector.vue";
import type {
  CanonicalArtifact,
  CanonicalClaim,
  CanonicalComparison,
  CanonicalGateHistoryEntry,
  CanonicalMetricDefinition,
  CanonicalRun,
} from "../lib/canonical";

use([CanvasRenderer, BarChart, GridComponent, LegendComponent, TooltipComponent]);

const props = defineProps<{ id: string }>();
const { snapshot } = useProjectStore();

const experiment = computed(() => snapshot.value?.experiments.find((e) => e.experimentId === props.id) ?? null);

type Tab = "summary" | "runs" | "compare" | "records" | "artifacts" | "claims";
const tabs: Array<{ key: Tab; label: string }> = [
  { key: "summary", label: "Summary" },
  { key: "runs", label: "Runs" },
  { key: "compare", label: "Compare" },
  { key: "records", label: "Records" },
  { key: "artifacts", label: "Artifacts" },
  { key: "claims", label: "Claims" },
];
const activeTab = ref<Tab>("summary");

// --- Summary：最新一筆有稽核結果的 claim，讓使用者一進 experiment 就看得到目前
// 最可信的結論是什麼，不用先切到 Claims 分頁才知道。 ---
const latestAuditedClaim = computed(() => {
  const audited = (experiment.value?.claims ?? []).filter((c) => c.auditResult !== null);
  if (audited.length === 0) return null;
  return [...audited].sort((a, b) => (a.auditResult!.auditedAt < b.auditResult!.auditedAt ? 1 : -1))[0];
});

// --- Gate history：單筆歷史項走 Drawer，不是塞在 Summary 頁面內文裡。 ---
const selectedGateEntry = ref<CanonicalGateHistoryEntry | null>(null);
function openGateEntry(entry: CanonicalGateHistoryEntry) {
  selectedGateEntry.value = entry;
}

// --- Runs ---
const runColumns = [
  { key: "runId", label: "run_id" },
  { key: "status", label: "status" },
  { key: "baselineRun", label: "baseline_run" },
  { key: "createdAt", label: "created_at" },
];
const runRows = computed(() =>
  (experiment.value?.runs ?? []).map((r) => ({
    runId: r.runId,
    status: r.status,
    baselineRun: r.baselineRun ?? "(baseline)",
    createdAt: r.createdAt ?? "—",
  }))
);
const selectedRun = ref<CanonicalRun | null>(null);
function openRun(row: Record<string, unknown>) {
  selectedRun.value = experiment.value?.runs.find((r) => r.runId === row.runId) ?? null;
}

// --- Compare ---
const experimentComparisons = computed(
  () => snapshot.value?.comparisons.filter((c) => c.experimentId === props.id) ?? []
);
const selectedComparison = ref<CanonicalComparison | null>(null);
const comparisonStatus = computed(() => (selectedComparison.value ? describeComparisonStatus(selectedComparison.value) : null));
const metricDefinitionByName = computed(() => {
  const map = new Map<string, CanonicalMetricDefinition>();
  for (const m of snapshot.value?.metricDefinitions ?? []) map.set(m.name, m);
  return map;
});

const chartOption = computed(() => {
  // 只有 valid 且非 confounded 才畫圖——invalid/confounded 絕不畫，避免暗示可比較。
  if (!selectedComparison.value || comparisonStatus.value !== "valid") return null;
  const validMetrics = selectedComparison.value.metrics.filter((m) => m.computed && m.definitionConsistent);
  if (validMetrics.length === 0) return null;
  return {
    tooltip: {},
    legend: { data: ["baseline", "treatment"] },
    xAxis: { type: "category", data: validMetrics.map((m) => m.metric) },
    yAxis: { type: "value" },
    series: [
      { name: "baseline", type: "bar", data: validMetrics.map((m) => m.baseline) },
      { name: "treatment", type: "bar", data: validMetrics.map((m) => m.treatment) },
    ],
  };
});

// --- Records（跟這個 experiment 的 primary/secondary metric 有關的 metric definitions）---
const relevantMetricNames = computed(() => {
  const names = new Set<string>();
  if (experiment.value?.primaryMetric) names.add(experiment.value.primaryMetric);
  for (const m of experiment.value?.secondaryMetrics ?? []) names.add(m);
  return names;
});
const relevantMetricDefinitions = computed(() =>
  (snapshot.value?.metricDefinitions ?? []).filter((m) => relevantMetricNames.value.has(m.name))
);

// --- Artifacts：單筆走 Drawer，開啟按鈕在 Drawer 內部，一樣經過 containment 檢查。 ---
const experimentArtifacts = computed(
  () => snapshot.value?.artifacts.filter((a) => a.experimentId === props.id) ?? []
);
const selectedArtifact = ref<CanonicalArtifact | null>(null);
const artifactOpenError = ref<string | null>(null);
function openArtifactDrawer(artifact: CanonicalArtifact) {
  artifactOpenError.value = null;
  selectedArtifact.value = artifact;
}
async function openArtifactExternally(path: string) {
  artifactOpenError.value = null;
  const projectRoot = snapshot.value?.projectRoot;
  if (!projectRoot) return;
  try {
    await openArtifact(projectRoot, path);
  } catch (e) {
    artifactOpenError.value = String(e);
  }
}

// --- Claims ---
const claimColumns = [
  { key: "claimId", label: "claim_id" },
  { key: "metric", label: "metric" },
  { key: "expectedDirection", label: "expected_direction" },
  { key: "verdict", label: "final_verdict" },
];
const claimRows = computed(() =>
  (experiment.value?.claims ?? []).map((c) => ({
    claimId: c.claimId,
    metric: c.metric,
    expectedDirection: c.expectedDirection,
    verdict: c.auditResult?.finalVerdict ?? "尚未稽核",
  }))
);
const selectedClaim = ref<CanonicalClaim | null>(null);
function openClaim(row: Record<string, unknown>) {
  selectedClaim.value = experiment.value?.claims.find((c) => c.claimId === row.claimId) ?? null;
}
</script>

<template>
  <section v-if="experiment">
    <h2>{{ experiment.experimentId }}</h2>

    <nav class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </nav>

    <div v-if="activeTab === 'summary'" class="tab-panel">
      <p v-if="experiment.question"><strong>question：</strong>{{ experiment.question }}</p>
      <p v-if="experiment.hypothesis"><em>{{ experiment.hypothesis }}</em></p>
      <p>status：<code>{{ experiment.status }}</code></p>
      <p v-if="experiment.primaryMetric">primary metric：<code>{{ experiment.primaryMetric }}</code></p>
      <p v-if="experiment.secondaryMetrics.length > 0">
        secondary metrics：<code>{{ experiment.secondaryMetrics.join(", ") }}</code>
      </p>
      <p v-if="experiment.contractHash">contract_hash：<code>{{ experiment.contractHash }}</code></p>

      <h3>最新可信結論</h3>
      <div v-if="latestAuditedClaim" class="latest-claim">
        <p>{{ latestAuditedClaim.statement }}</p>
        <p>
          <span
            class="badge"
            :class="{
              'badge-good': latestAuditedClaim.auditResult?.finalVerdict === 'fully_supported',
              'badge-bad':
                latestAuditedClaim.auditResult?.finalVerdict === 'overreaching' ||
                latestAuditedClaim.auditResult?.finalVerdict === 'unsupported' ||
                latestAuditedClaim.auditResult?.finalVerdict === 'unauditable',
            }"
          >{{ latestAuditedClaim.auditResult?.finalVerdict }}</span>
          <button class="link-button" @click="activeTab = 'claims'">看完整稽核結果 →</button>
        </p>
      </div>
      <p v-else class="hint">這個 experiment 底下還沒有稽核過的 claim。</p>

      <h3>Compute Gate</h3>
      <div v-if="experiment.gateState">
        <p>目前等級：<strong>{{ experiment.gateState.currentLevel ?? "尚未申請過任何等級" }}</strong></p>
        <table v-if="experiment.gateState.history.length > 0">
          <thead>
            <tr><th>level</th><th>status</th><th>decided_at</th><th>reason</th></tr>
          </thead>
          <tbody>
            <tr
              v-for="(entry, i) in experiment.gateState.history"
              :key="i"
              tabindex="0"
              :class="{ errors: entry.status === 'aborted' }"
              @click="openGateEntry(entry)"
              @keydown.enter="openGateEntry(entry)"
            >
              <td>{{ entry.level }}</td>
              <td><span class="badge" :class="{ 'badge-good': entry.status === 'passed', 'badge-bad': entry.status !== 'passed' }">{{ entry.status }}</span></td>
              <td>{{ entry.decidedAt }}</td>
              <td>{{ entry.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="hint">還沒申請過任何 Compute Gate 等級。</p>

      <Drawer :open="selectedGateEntry !== null" :title="`Gate ${selectedGateEntry?.level ?? ''}`" @close="selectedGateEntry = null">
        <template v-if="selectedGateEntry">
          <p>status：<code>{{ selectedGateEntry.status }}</code></p>
          <p>decided_at：<code>{{ selectedGateEntry.decidedAt }}</code></p>
          <p>{{ selectedGateEntry.reason }}</p>
          <h4>run_ids（{{ selectedGateEntry.runIds.length }}）</h4>
          <ul>
            <li v-for="runId in selectedGateEntry.runIds" :key="runId"><code>{{ runId }}</code></li>
          </ul>
        </template>
      </Drawer>
    </div>

    <div v-else-if="activeTab === 'runs'" class="tab-panel">
      <DataTable
        v-if="runRows.length > 0"
        :columns="runColumns"
        :rows="runRows"
        :row-key="(row) => String(row.runId)"
        :selected-key="selectedRun?.runId ?? null"
        @select="openRun"
      />
      <p v-else class="hint">這個 experiment 底下還沒有任何 run。</p>

      <Drawer :open="selectedRun !== null" :title="selectedRun?.runId ?? ''" @close="selectedRun = null">
        <template v-if="selectedRun">
          <p>status：<code>{{ selectedRun.status }}</code></p>
          <p v-if="selectedRun.invalidReason" class="errors">invalid_reason：{{ selectedRun.invalidReason }}</p>
          <p>baseline_run：<code>{{ selectedRun.baselineRun ?? "(baseline)" }}</code></p>
          <h4>metrics</h4>
          <table>
            <tbody>
              <tr v-for="(v, k) in selectedRun.metrics" :key="k"><th>{{ k }}</th><td>{{ v }}</td></tr>
            </tbody>
          </table>
          <h4>artifacts（{{ selectedRun.artifacts.length }}）</h4>
          <ul>
            <li v-for="a in selectedRun.artifacts" :key="a"><code>{{ a }}</code></li>
          </ul>
        </template>
      </Drawer>
    </div>

    <div v-else-if="activeTab === 'compare'" class="tab-panel">
      <p class="hint">只顯示 compare-runs 已產生的 comparison-result，不在這裡重新計算或重新判定 comparability。</p>
      <RunSelector v-model="selectedComparison" :comparisons="experimentComparisons" />

      <template v-if="selectedComparison">
        <div v-if="comparisonStatus === 'confounded'" class="errors">
          <p>⚠ 這組比較 <strong>confounded</strong>，不得下因果性結論。原因：</p>
          <ul>
            <li v-for="reason in selectedComparison.confoundedReasons" :key="reason">{{ reason }}</li>
          </ul>
        </div>
        <div v-else-if="comparisonStatus === 'invalid'" class="errors">
          <p>⚠ <code>comparison_valid</code> 為 false（非 confounded），不得下因果性結論。</p>
          <ul v-if="selectedComparison.notes.length > 0">
            <li v-for="note in selectedComparison.notes" :key="note">{{ note }}</li>
          </ul>
        </div>
        <template v-else>
          <VChart v-if="chartOption" :option="chartOption" style="height: 320px" autoresize />
          <table>
            <thead>
              <tr><th>metric</th><th>baseline</th><th>treatment</th><th>結果</th></tr>
            </thead>
            <tbody>
              <tr v-for="m in selectedComparison.metrics" :key="m.metric">
                <td>{{ metricDefinitionByName.get(m.metric)?.displayName ?? m.metric }}</td>
                <td>{{ m.baseline ?? "—" }}</td>
                <td>
                  <MetricValue
                    :value="m.treatment"
                    :unit="metricDefinitionByName.get(m.metric)?.unit"
                    :format="metricDefinitionByName.get(m.metric)?.format"
                    :direction="metricDefinitionByName.get(m.metric)?.direction"
                    :comparison-valid="m.computed && m.definitionConsistent"
                    :diff="m.absoluteDiff"
                  />
                </td>
                <td>{{ m.computed ? "已計算" : "未計算（定義不一致或整體不可比）" }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </template>
      <p v-else-if="experimentComparisons.length === 0" class="hint">這個 experiment 底下還沒有任何 comparison-result。</p>
    </div>

    <div v-else-if="activeTab === 'records'" class="tab-panel">
      <h3>相關 Metric Definitions</h3>
      <table v-if="relevantMetricDefinitions.length > 0">
        <thead><tr><th>name</th><th>display name</th><th>type</th><th>direction</th><th>unit</th><th>aggregation</th></tr></thead>
        <tbody>
          <tr v-for="m in relevantMetricDefinitions" :key="m.name">
            <td>{{ m.name }}</td>
            <td>{{ m.displayName ?? "—" }}</td>
            <td>{{ m.type }}</td>
            <td>{{ m.direction ?? "（未定義）" }}</td>
            <td>{{ m.unit ?? "—" }}</td>
            <td>{{ m.aggregation }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="hint">找不到這個 experiment 的 primary/secondary metric 對應的 metric definition。</p>
      <p class="hint">跨 experiment 的額外 record collections 在左側導覽的「Records」。</p>
    </div>

    <div v-else-if="activeTab === 'artifacts'" class="tab-panel">
      <table v-if="experimentArtifacts.length > 0">
        <thead><tr><th>run_id</th><th>path</th></tr></thead>
        <tbody>
          <tr
            v-for="(a, i) in experimentArtifacts"
            :key="i"
            tabindex="0"
            @click="openArtifactDrawer(a)"
            @keydown.enter="openArtifactDrawer(a)"
          >
            <td>{{ a.runId }}</td>
            <td><code>{{ a.path }}</code></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="hint">這個 experiment 底下的 run 還沒有任何 artifact。</p>

      <Drawer :open="selectedArtifact !== null" :title="selectedArtifact?.path ?? ''" @close="selectedArtifact = null">
        <template v-if="selectedArtifact">
          <p>run_id：<code>{{ selectedArtifact.runId }}</code></p>
          <p>path：<code>{{ selectedArtifact.path }}</code></p>
          <div v-if="artifactOpenError" class="errors">{{ artifactOpenError }}</div>
          <button @click="openArtifactExternally(selectedArtifact.path)">用外部程式開啟</button>
        </template>
      </Drawer>
    </div>

    <div v-else-if="activeTab === 'claims'" class="tab-panel">
      <DataTable
        v-if="claimRows.length > 0"
        :columns="claimColumns"
        :rows="claimRows"
        :row-key="(row) => String(row.claimId)"
        :selected-key="selectedClaim?.claimId ?? null"
        @select="openClaim"
      >
        <template #verdict="{ row }">
          <span
            class="badge"
            :class="{
              'badge-good': row.verdict === 'fully_supported',
              'badge-bad': row.verdict === 'overreaching' || row.verdict === 'unsupported' || row.verdict === 'unauditable',
            }"
          >{{ row.verdict }}</span>
        </template>
      </DataTable>
      <p v-else class="hint">這個 experiment 底下還沒有任何 claim。</p>

      <Drawer :open="selectedClaim !== null" :title="selectedClaim?.claimId ?? ''" @close="selectedClaim = null">
        <template v-if="selectedClaim">
          <p>{{ selectedClaim.statement }}</p>
          <p>scope：{{ selectedClaim.scope }}</p>
          <p>expected_direction：<code>{{ selectedClaim.expectedDirection }}</code></p>
          <template v-if="selectedClaim.auditResult">
            <h4>mechanical</h4>
            <table>
              <tbody>
                <tr><th>reference_exists</th><td>{{ selectedClaim.auditResult.referenceExists }}</td></tr>
                <tr><th>comparison_valid</th><td>{{ selectedClaim.auditResult.comparisonValid ?? "（未檢查）" }}</td></tr>
                <tr><th>metric_exists</th><td>{{ selectedClaim.auditResult.metricExists ?? "（未檢查）" }}</td></tr>
                <tr><th>direction_matches</th><td>{{ selectedClaim.auditResult.directionMatches ?? "（未檢查）" }}</td></tr>
                <tr><th>magnitude_matches</th><td>{{ selectedClaim.auditResult.magnitudeMatches ?? "（未填 stated_magnitude）" }}</td></tr>
              </tbody>
            </table>
            <p v-if="selectedClaim.auditResult.scopeReasoning" class="hint">{{ selectedClaim.auditResult.scopeReasoning }}</p>
          </template>
          <p v-else class="hint">還沒有對應的 claim-audit-result。</p>
        </template>
      </Drawer>
    </div>
  </section>
  <p v-else class="hint">找不到 experiment_id=<code>{{ id }}</code>。</p>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}
.tabs button {
  border: 1px solid transparent;
  border-bottom: none;
  background: transparent;
  border-radius: var(--radius) var(--radius) 0 0;
}
.tabs button.active {
  border-color: var(--color-border);
  background: var(--color-bg);
  color: var(--color-heading);
  font-weight: 600;
}
.tab-panel {
  padding-top: var(--space-2);
}
.latest-claim {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-3);
}
.link-button {
  background: transparent;
  border: none;
  padding: 0;
  margin-left: var(--space-2);
  color: var(--color-accent);
  cursor: pointer;
  font: inherit;
}
</style>
