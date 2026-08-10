<script setup lang="ts">
import { computed, ref } from "vue";
import { open } from "@tauri-apps/plugin-dialog";
import VChart from "vue-echarts";
import "echarts";
import type { CanonicalClaimAuditResult, CanonicalComparison, CanonicalExperiment } from "./lib/canonical";
import { loadClaimAuditFile, loadComparisonFile, loadRecordsRoot } from "./lib/storage-adapter";

const recordsRoot = ref<string | null>(null);
const experiments = ref<CanonicalExperiment[]>([]);
const loadErrors = ref<string[]>([]);
const selectedExperimentId = ref<string | null>(null);
const comparison = ref<CanonicalComparison | null>(null);
const comparisonError = ref<string | null>(null);
const claimAudit = ref<CanonicalClaimAuditResult | null>(null);
const claimAuditError = ref<string | null>(null);

const selectedExperiment = computed(() =>
  experiments.value.find((e) => e.experimentId === selectedExperimentId.value) ?? null
);

async function pickRecordsRoot() {
  const dir = await open({ directory: true, title: "選 records/experiments/ 資料夾" });
  if (!dir || Array.isArray(dir)) return;
  recordsRoot.value = dir;
  const result = await loadRecordsRoot(dir);
  experiments.value = result.experiments;
  loadErrors.value = result.errors;
  selectedExperimentId.value = result.experiments[0]?.experimentId ?? null;
  comparison.value = null;
}

async function pickComparisonFile() {
  const file = await open({
    multiple: false,
    title: "選 compare-runs 產生的 comparison-result.json",
    filters: [{ name: "JSON", extensions: ["json"] }],
  });
  if (!file || Array.isArray(file)) return;
  comparisonError.value = null;
  try {
    comparison.value = await loadComparisonFile(file);
  } catch (e) {
    comparison.value = null;
    comparisonError.value = String(e);
  }
}

async function pickClaimAuditFile() {
  const file = await open({
    multiple: false,
    title: "選 claim-audit 產生的 claim-audit-result.json",
    filters: [{ name: "JSON", extensions: ["json"] }],
  });
  if (!file || Array.isArray(file)) return;
  claimAuditError.value = null;
  try {
    claimAudit.value = await loadClaimAuditFile(file);
  } catch (e) {
    claimAudit.value = null;
    claimAuditError.value = String(e);
  }
}

const verdictLabel: Record<string, string> = {
  fully_supported: "完全支持",
  partially_supported: "部分支持",
  overreaching: "超出證據範圍",
  unsupported: "不支持",
  unauditable: "無法稽核",
  pending: "待 agent 判斷",
};

const chartOption = computed(() => {
  if (!comparison.value) return null;
  const validMetrics = comparison.value.metrics.filter((m) => m.computed && m.definitionConsistent);
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
</script>

<template>
  <main class="container">
    <h1>experiment-viewer</h1>
    <p class="hint">
      只讀 <code>records/experiments/</code>，不寫回、不維護第二份權威副本——資料的唯一來源仍是那個資料夾。
    </p>

    <section>
      <button @click="pickRecordsRoot">選 records/experiments/ 資料夾</button>
      <span v-if="recordsRoot" class="path">{{ recordsRoot }}</span>
    </section>

    <section v-if="loadErrors.length > 0" class="errors">
      <h3>{{ loadErrors.length }} 筆資料解析失敗</h3>
      <ul>
        <li v-for="err in loadErrors" :key="err">{{ err }}</li>
      </ul>
    </section>

    <section v-if="experiments.length > 0">
      <h2>Experiments</h2>
      <ul class="experiment-list">
        <li
          v-for="exp in experiments"
          :key="exp.experimentId"
          :class="{ selected: exp.experimentId === selectedExperimentId }"
          @click="selectedExperimentId = exp.experimentId"
        >
          <strong>{{ exp.experimentId }}</strong> — {{ exp.status }} — {{ exp.runs.length }} runs
        </li>
      </ul>
    </section>

    <section v-if="selectedExperiment">
      <h3>{{ selectedExperiment.question }}</h3>
      <p><em>{{ selectedExperiment.hypothesis }}</em></p>
      <p>primary metric: <code>{{ selectedExperiment.primaryMetric }}</code></p>
      <table>
        <thead>
          <tr>
            <th>run_id</th>
            <th>status</th>
            <th>baseline_run</th>
            <th>metrics</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="run in selectedExperiment.runs" :key="run.runId">
            <td>{{ run.runId }}</td>
            <td>{{ run.status }}</td>
            <td>{{ run.baselineRun ?? "(baseline)" }}</td>
            <td>{{ Object.keys(run.metrics).join(", ") }}</td>
          </tr>
        </tbody>
      </table>

      <h3>Claims（{{ selectedExperiment.claims.length }}）</h3>
      <table v-if="selectedExperiment.claims.length > 0">
        <thead>
          <tr>
            <th>claim_id</th>
            <th>statement</th>
            <th>metric</th>
            <th>expected_direction</th>
            <th>scope</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="claim in selectedExperiment.claims" :key="claim.claimId">
            <td>{{ claim.claimId }}</td>
            <td>{{ claim.statement }}</td>
            <td>{{ claim.metric }}</td>
            <td>{{ claim.expectedDirection }}</td>
            <td>{{ claim.scope }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="hint">這個 experiment 底下 <code>claims/</code> 還沒有任何 claim。</p>

      <h3>Compute Gate</h3>
      <div v-if="selectedExperiment.gateState">
        <p>目前等級：<strong>{{ selectedExperiment.gateState.currentLevel ?? "尚未申請過任何等級" }}</strong></p>
        <table v-if="selectedExperiment.gateState.history.length > 0">
          <thead>
            <tr>
              <th>level</th>
              <th>status</th>
              <th>decided_at</th>
              <th>reason</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(entry, i) in selectedExperiment.gateState.history"
              :key="i"
              :class="{ 'gate-aborted': entry.status === 'aborted', 'gate-failed': entry.status === 'failed' }"
            >
              <td>{{ entry.level }}</td>
              <td>{{ entry.status }}</td>
              <td>{{ entry.decidedAt }}</td>
              <td>{{ entry.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="hint">這個 experiment 底下 <code>gates/{{ selectedExperiment.experimentId }}.json</code> 還不存在，代表還沒申請過任何 Compute Gate 等級。</p>
    </section>

    <section>
      <h2>比較兩個 run</h2>
      <p class="hint">要先用 <code>compare-runs</code> skill 產生 <code>comparison-result.json</code>，這裡只負責讀跟畫，不重新做可比較性判定。</p>
      <button @click="pickComparisonFile">選 comparison-result.json</button>

      <div v-if="comparisonError" class="errors">{{ comparisonError }}</div>

      <div v-if="comparison">
        <p>{{ comparison.runA }} vs {{ comparison.runB }}</p>
        <p v-if="!comparison.comparisonValid || comparison.confounded" class="confounded">
          ⚠ 這組比較 <strong>confounded</strong>，不得下因果性結論。原因：
          <ul>
            <li v-for="reason in comparison.confoundedReasons" :key="reason">{{ reason }}</li>
          </ul>
        </p>
        <v-chart v-else-if="chartOption" :option="chartOption" style="height: 360px" />
      </div>
    </section>

    <section>
      <h2>Claim Audit</h2>
      <p class="hint">要先用 <code>claim-audit</code> skill 產生 <code>claim-audit-result.json</code>——機械段（引用是否存在、方向與數值對不對）由 <code>claim_audit.py</code> 判定，<code>scope_verdict</code> 這一段是 agent 的語意判斷，這裡只負責讀跟顯示，不重新判定。</p>
      <button @click="pickClaimAuditFile">選 claim-audit-result.json</button>

      <div v-if="claimAuditError" class="errors">{{ claimAuditError }}</div>

      <div v-if="claimAudit">
        <p>claim_id：<code>{{ claimAudit.claimId }}</code></p>
        <p>
          結論：
          <strong :class="{ overreach: claimAudit.finalVerdict === 'overreaching' || claimAudit.finalVerdict === 'unsupported' }">
            {{ verdictLabel[claimAudit.finalVerdict] }}
          </strong>
        </p>
        <table>
          <tbody>
            <tr><th>reference_exists</th><td>{{ claimAudit.referenceExists }}</td></tr>
            <tr><th>comparison_valid</th><td>{{ claimAudit.comparisonValid ?? "（未檢查）" }}</td></tr>
            <tr><th>metric_exists</th><td>{{ claimAudit.metricExists ?? "（未檢查）" }}</td></tr>
            <tr><th>direction_matches</th><td>{{ claimAudit.directionMatches ?? "（未檢查）" }}</td></tr>
            <tr><th>magnitude_matches</th><td>{{ claimAudit.magnitudeMatches ?? "（未填 stated_magnitude，不檢查）" }}</td></tr>
          </tbody>
        </table>
        <ul v-if="claimAudit.mechanicalReasons.length > 0">
          <li v-for="reason in claimAudit.mechanicalReasons" :key="reason">{{ reason }}</li>
        </ul>
        <p v-if="claimAudit.scopeReasoning" class="hint">{{ claimAudit.scopeReasoning }}</p>
      </div>
    </section>
  </main>
</template>

<style scoped>
.container {
  max-width: 960px;
  margin: 0 auto;
  padding: 1.5rem;
  font-family: system-ui, sans-serif;
}
.hint {
  color: #666;
  font-size: 0.9rem;
}
.path {
  margin-left: 0.75rem;
  font-family: monospace;
  font-size: 0.85rem;
}
.experiment-list {
  list-style: none;
  padding: 0;
}
.experiment-list li {
  padding: 0.5rem;
  cursor: pointer;
  border-radius: 4px;
}
.experiment-list li.selected {
  background: #e8e8ff;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  border: 1px solid #ddd;
  padding: 0.4rem;
  text-align: left;
}
.errors {
  color: #a00;
}
.confounded {
  color: #a00;
  font-weight: bold;
}
.overreach {
  color: #a00;
}
.gate-aborted {
  background: #fdecea;
}
.gate-failed {
  background: #fff6e0;
}
</style>
