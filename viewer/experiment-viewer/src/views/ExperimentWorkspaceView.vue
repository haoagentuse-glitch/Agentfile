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
import { statusLabel } from "../lib/status-label";
import DataTable from "../components/DataTable.vue";
import Drawer from "../components/Drawer.vue";
import MetricValue from "../components/MetricValue.vue";
import RunSelector from "../components/RunSelector.vue";
import { buildClaimLineage } from "../lib/lineage";
import type {
  CanonicalArtifact,
  CanonicalClaim,
  CanonicalComparison,
  CanonicalComparisonEstimate,
  CanonicalDiagnosis,
  CanonicalEstimateInterval,
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
  { key: "summary", label: "摘要" },
  { key: "runs", label: "執行紀錄" },
  { key: "compare", label: "比較" },
  { key: "records", label: "紀錄" },
  { key: "artifacts", label: "產物" },
  { key: "claims", label: "主張" },
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
  { key: "runId", label: "執行 ID" },
  { key: "status", label: "狀態" },
  { key: "baselineRun", label: "基準執行" },
  { key: "createdAt", label: "建立時間" },
];
const runRows = computed(() =>
  (experiment.value?.runs ?? []).map((r) => ({
    runId: r.runId,
    status: statusLabel(r.status),
    baselineRun: r.baselineRun ?? "（基準）",
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

// 缺 interval 是合法狀態，照實說「未估計」，不用點估計替代區間。
function formatInterval(interval: CanonicalEstimateInterval | null): string {
  if (!interval) return "未估計";
  return `[${interval.lower}, ${interval.upper}]（${interval.confidenceLevel}，${interval.method}）`;
}

// clustered inference 的樣本單位是 cluster 數，observations 不能取代它，兩個都顯示。
function formatSampleSize(estimate: CanonicalComparisonEstimate): string {
  const parts: string[] = [];
  if (estimate.observations !== null) parts.push(`${estimate.observations} 筆`);
  if (estimate.clusters !== null) parts.push(`${estimate.clusters} 群`);
  return parts.length > 0 ? parts.join("／") : "—";
}

const chartOption = computed(() => {
  // 只有 valid 且非 confounded 才畫圖——invalid/confounded 絕不畫，避免暗示可比較。
  if (!selectedComparison.value || comparisonStatus.value !== "valid") return null;
  const validMetrics = selectedComparison.value.metrics.filter((m) => m.computed && m.definitionConsistent);
  if (validMetrics.length === 0) return null;
  return {
    tooltip: {},
    legend: { data: ["基準", "處理組"] },
    xAxis: { type: "category", data: validMetrics.map((m) => m.metric) },
    yAxis: { type: "value" },
    series: [
      { name: "基準", type: "bar", data: validMetrics.map((m) => m.baseline) },
      { name: "處理組", type: "bar", data: validMetrics.map((m) => m.treatment) },
    ],
  };
});

// --- 紀錄：與這個實驗的主要與次要指標有關的指標定義。---
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
  { key: "claimId", label: "主張 ID" },
  { key: "estimandId", label: "估計目標" },
  { key: "status", label: "狀態" },
  { key: "verdict", label: "最終判定" },
];
// refuted 與 inconclusive 是正式終態，一起列出來，不因為結論不好看就過濾掉。
const claimRows = computed(() =>
  (experiment.value?.claims ?? []).map((c) => ({
    claimId: c.claimId,
    estimandId: c.estimandId,
    status: c.status,
    verdict: c.auditResult?.finalVerdict ?? "尚未稽核",
  }))
);
const selectedClaim = ref<CanonicalClaim | null>(null);
function openClaim(row: Record<string, unknown>) {
  selectedClaim.value = experiment.value?.claims.find((c) => c.claimId === row.claimId) ?? null;
}

// --- Lineage：從選中的 claim 一路回推到題目憑證與 prompt 版本。 ---
const selectedLineage = computed(() =>
  selectedClaim.value && snapshot.value
    ? buildClaimLineage(snapshot.value, selectedClaim.value.claimId)
    : null
);

// --- 失敗診斷：終態只留一句 reason 不夠，這裡把結構化診斷攤開。 ---
const selectedDiagnosis = ref<CanonicalDiagnosis | null>(null);
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
      <p v-if="experiment.question"><strong>研究問題：</strong>{{ experiment.question }}</p>
      <p v-if="experiment.hypothesis"><em>{{ experiment.hypothesis }}</em></p>
      <p>狀態：<code>{{ statusLabel(experiment.status) }}</code></p>
      <p v-if="experiment.primaryMetric">主要指標：<code>{{ experiment.primaryMetric }}</code></p>
      <p v-if="experiment.secondaryMetrics.length > 0">
        次要指標：<code>{{ experiment.secondaryMetrics.join(", ") }}</code>
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
          >{{ statusLabel(latestAuditedClaim.auditResult?.finalVerdict) }}</span>
          <button class="link-button" @click="activeTab = 'claims'">查看完整稽核結果 →</button>
        </p>
      </div>
      <p v-else class="hint">這個實驗下還沒有已稽核的主張。</p>

      <h3>計算關卡（Compute Gate）</h3>
      <div v-if="experiment.gateState">
        <p>目前等級：<strong>{{ experiment.gateState.currentLevel ?? "尚未申請過任何等級" }}</strong></p>
        <table v-if="experiment.gateState.history.length > 0">
          <thead>
            <tr><th>等級</th><th>狀態</th><th>決定時間</th><th>原因</th></tr>
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
              <td><span class="badge" :class="{ 'badge-good': entry.status === 'passed', 'badge-bad': entry.status !== 'passed' }">{{ statusLabel(entry.status) }}</span></td>
              <td>{{ entry.decidedAt }}</td>
              <td>{{ entry.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="hint">還沒申請過任何 Compute Gate 等級。</p>

      <Drawer :open="selectedGateEntry !== null" :title="`Gate ${selectedGateEntry?.level ?? ''}`" @close="selectedGateEntry = null">
        <template v-if="selectedGateEntry">
          <p>狀態：<code>{{ statusLabel(selectedGateEntry.status) }}</code></p>
          <p>決定時間：<code>{{ selectedGateEntry.decidedAt }}</code></p>
          <p>{{ selectedGateEntry.reason }}</p>
          <h4>執行 ID（{{ selectedGateEntry.runIds.length }}）</h4>
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
      <p v-else class="hint">這個實驗下還沒有任何執行紀錄。</p>

      <Drawer :open="selectedRun !== null" :title="selectedRun?.runId ?? ''" @close="selectedRun = null">
        <template v-if="selectedRun">
          <p>狀態：<code>{{ statusLabel(selectedRun.status) }}</code></p>
          <p v-if="selectedRun.invalidReason" class="errors">invalid_reason：{{ selectedRun.invalidReason }}</p>
          <p>baseline_run：<code>{{ selectedRun.baselineRun ?? "（基準）" }}</code></p>
          <h4>指標</h4>
          <table>
            <tbody>
              <tr v-for="(v, k) in selectedRun.metrics" :key="k"><th>{{ k }}</th><td>{{ v }}</td></tr>
            </tbody>
          </table>
          <h4>產物（{{ selectedRun.artifacts.length }}）</h4>
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
          <p>⚠ 這組比較為 <strong>已混雜（confounded）</strong>，不得下因果性結論。原因：</p>
          <ul>
            <li v-for="reason in selectedComparison.confoundedReasons" :key="reason">{{ reason }}</li>
          </ul>
        </div>
        <div v-else-if="comparisonStatus === 'invalid'" class="errors">
          <p>⚠ <code>comparison_valid</code> 為 false（非已混雜狀態），不得下因果性結論。</p>
          <ul v-if="selectedComparison.notes.length > 0">
            <li v-for="note in selectedComparison.notes" :key="note">{{ note }}</li>
          </ul>
        </div>
        <template v-else>
          <VChart v-if="chartOption" :option="chartOption" style="height: 320px" autoresize />
          <table>
            <thead>
              <tr><th>指標</th><th>基準</th><th>處理組</th><th>結果</th></tr>
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

          <h4>估計與判定</h4>
          <p class="hint">
            以下是 compare-runs 依凍結的 analysis plan 寫下的結果。點估計的正負不等於結論；
            區間跨過決策邊界時只會是 inconclusive。
          </p>
          <table v-if="selectedComparison.estimates.length > 0">
            <thead>
              <tr><th>估計目標</th><th>點估計</th><th>區間</th><th>樣本</th><th>判定</th></tr>
            </thead>
            <tbody>
              <tr v-for="e in selectedComparison.estimates" :key="e.estimandId">
                <td>
                  <code>{{ e.estimandId }}</code>
                  <p class="hint">{{ e.methodRef }}</p>
                </td>
                <td>{{ e.pointEstimate }}</td>
                <td>{{ formatInterval(e.interval) }}</td>
                <td>{{ formatSampleSize(e) }}</td>
                <td>
                  <code>{{ e.decision.conclusion }}</code>
                  <p v-if="e.decision.reasonCodes.length > 0" class="hint">
                    {{ e.decision.reasonCodes.join("、") }}
                  </p>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="hint">這份 comparison 沒有任何持久化 estimate。</p>
        </template>
      </template>
      <p v-else-if="experimentComparisons.length === 0" class="hint">這個實驗下還沒有任何比較結果。</p>
    </div>

    <div v-else-if="activeTab === 'records'" class="tab-panel">
      <h3>相關指標定義</h3>
      <table v-if="relevantMetricDefinitions.length > 0">
        <thead><tr><th>名稱</th><th>顯示名稱</th><th>類型</th><th>方向</th><th>單位</th><th>彙總方式</th></tr></thead>
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
      <p v-else class="hint">找不到這個實驗主要與次要指標對應的指標定義。</p>
      <p class="hint">跨實驗的額外紀錄集合在左側導覽的「紀錄」。</p>
    </div>

    <div v-else-if="activeTab === 'artifacts'" class="tab-panel">
      <table v-if="experimentArtifacts.length > 0">
        <thead><tr><th>執行 ID</th><th>路徑</th></tr></thead>
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
      <p v-else class="hint">這個實驗下的執行紀錄還沒有任何產物。</p>

      <Drawer :open="selectedArtifact !== null" :title="selectedArtifact?.path ?? ''" @close="selectedArtifact = null">
        <template v-if="selectedArtifact">
          <p>執行 ID：<code>{{ selectedArtifact.runId }}</code></p>
          <p>路徑：<code>{{ selectedArtifact.path }}</code></p>
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
          >{{ statusLabel(String(row.verdict)) }}</span>
        </template>
        <template #status="{ row }">
          <span
            class="badge"
            :class="{
              'badge-good': row.status === 'supported',
              'badge-warn': row.status === 'inconclusive' || row.status === 'refuted',
            }"
          >{{ statusLabel(String(row.status)) }}</span>
        </template>
      </DataTable>
      <p v-else class="hint">這個實驗下還沒有任何主張。</p>

      <h3>失敗診斷（{{ experiment.diagnoses.length }}）</h3>
      <table v-if="experiment.diagnoses.length > 0">
        <thead><tr><th>診斷 ID</th><th>對象</th><th>假設分類</th><th>最便宜的下一步</th></tr></thead>
        <tbody>
          <tr
            v-for="d in experiment.diagnoses"
            :key="d.diagnosisId"
            tabindex="0"
            @click="selectedDiagnosis = d"
            @keydown.enter="selectedDiagnosis = d"
          >
            <td>{{ d.diagnosisId }}</td>
            <td><code>{{ d.subject.kind }}</code></td>
            <td>{{ [...new Set(d.hypotheses.map((h) => h.failureClass))].join("、") }}</td>
            <td>{{ d.cheapestNextTest.description }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="hint">這個實驗下沒有結構化的失敗診斷。</p>

      <Drawer
        :open="selectedDiagnosis !== null"
        :title="selectedDiagnosis?.diagnosisId ?? ''"
        @close="selectedDiagnosis = null"
      >
        <template v-if="selectedDiagnosis">
          <h4>確定性事實</h4>
          <ul>
            <li v-for="(f, i) in selectedDiagnosis.deterministicFacts" :key="i">
              {{ f.fact }}<br /><code>{{ f.sourceRef }}{{ f.locator ? `#${f.locator}` : "" }}</code>
            </li>
          </ul>
          <h4>假設（推測，非事實）</h4>
          <ul>
            <li v-for="h in selectedDiagnosis.hypotheses" :key="h.id">
              <span class="badge">{{ h.failureClass }}</span>
              <span class="badge">{{ h.confidence }}</span>
              {{ h.statement }}
              <p v-if="h.discriminatingObservation" class="hint">分辨方式：{{ h.discriminatingObservation }}</p>
            </li>
          </ul>
          <template v-if="selectedDiagnosis.excludedClasses.length > 0">
            <h4>已排除</h4>
            <ul>
              <li v-for="(e, i) in selectedDiagnosis.excludedClasses" :key="i">
                <code>{{ e.failureClass }}</code>：{{ e.reason }}
              </li>
            </ul>
          </template>
          <h4>最便宜的下一步</h4>
          <p>{{ selectedDiagnosis.cheapestNextTest.description }}</p>
          <p v-if="selectedDiagnosis.cheapestNextTest.command"><code>{{ selectedDiagnosis.cheapestNextTest.command }}</code></p>
          <p class="hint">能分辨：{{ selectedDiagnosis.cheapestNextTest.distinguishes.join("、") }}</p>
        </template>
      </Drawer>

      <Drawer :open="selectedClaim !== null" :title="selectedClaim?.claimId ?? ''" @close="selectedClaim = null">
        <template v-if="selectedClaim">
          <p>{{ selectedClaim.statement }}</p>
          <p>適用範圍：{{ selectedClaim.scope }}</p>
          <p>估計目標（estimand_id）：<code>{{ selectedClaim.estimandId }}</code></p>
          <p>預期方向（expected_direction）：<code>{{ selectedClaim.expectedDirection }}</code></p>
          <p>預期結論（expected_conclusion）：<code>{{ selectedClaim.expectedConclusion }}</code></p>
          <template v-if="selectedClaim.auditResult">
            <h4>機械檢查</h4>
            <table>
              <tbody>
                <tr><th>reference_exists</th><td>{{ selectedClaim.auditResult.referenceExists }}</td></tr>
                <tr><th>comparison_valid</th><td>{{ selectedClaim.auditResult.comparisonValid ?? "（未檢查）" }}</td></tr>
                <tr><th>estimand_exists</th><td>{{ selectedClaim.auditResult.estimandExists ?? "（未檢查）" }}</td></tr>
                <tr><th>direction_matches</th><td>{{ selectedClaim.auditResult.directionMatches ?? "（未檢查）" }}</td></tr>
                <tr><th>conclusion_matches</th><td>{{ selectedClaim.auditResult.conclusionMatches ?? "（未檢查）" }}</td></tr>
                <tr><th>magnitude_matches</th><td>{{ selectedClaim.auditResult.magnitudeMatches ?? "（未填 stated_magnitude）" }}</td></tr>
              </tbody>
            </table>
            <p v-if="selectedClaim.auditResult.scopeReasoning" class="hint">{{ selectedClaim.auditResult.scopeReasoning }}</p>
          </template>
          <p v-else class="hint">還沒有對應的主張稽核結果。</p>

          <h4>研究譜系</h4>
          <p v-if="selectedLineage?.broken" class="errors">
            這條證據鏈有缺口。標示「接不上」的環節下方會說明原因。
          </p>
          <ol v-if="selectedLineage" class="lineage">
            <li v-for="(step, i) in selectedLineage.steps" :key="i" :class="{ missing: step.missing }">
              <span class="badge">{{ step.kind }}</span>
              <strong>{{ step.label }}</strong>
              <p>{{ step.detail }}</p>
              <p v-if="step.ref" class="hint"><code>{{ step.ref }}</code></p>
              <p v-if="step.missing" class="errors">接不上</p>
              <p v-else-if="step.warning" class="hint">⚠ {{ step.warning }}</p>
            </li>
          </ol>
        </template>
      </Drawer>
    </div>
  </section>
  <p v-else class="hint">找不到實驗 ID=<code>{{ id }}</code>。</p>
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
/* lineage 用縮排的直線串起來，讓「這是一條鏈」在畫面上看得出來。 */
.lineage {
  list-style: none;
  padding-left: var(--space-3);
  margin: 0;
  border-left: 2px solid var(--color-border);
}
.lineage li {
  padding: var(--space-2) 0 var(--space-2) var(--space-3);
  position: relative;
}
.lineage li::before {
  content: "";
  position: absolute;
  left: calc(-1 * var(--space-3) - 5px);
  top: 14px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-accent);
}
/* 接不上的環節保留在鏈上並標紅——鏈上少一環跟鏈上有一環接不上不是同一回事。 */
.lineage li.missing::before {
  background: var(--color-bad);
}
.lineage li p {
  margin: var(--space-1) 0 0 0;
}
</style>
