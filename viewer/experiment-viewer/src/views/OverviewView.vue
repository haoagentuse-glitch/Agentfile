<script setup lang="ts">
import { computed } from "vue";
import { useProjectStore } from "../store/project";
import type { MetricDirection } from "../lib/canonical";
import { statusLabel } from "../lib/status-label";

const { snapshot } = useProjectStore();

const experiments = computed(() => snapshot.value?.experiments ?? []);
const allRuns = computed(() => experiments.value.flatMap((e) => e.runs));

const runStatusCounts = computed(() => {
  const counts: Record<string, number> = {};
  for (const r of allRuns.value) counts[r.status] = (counts[r.status] ?? 0) + 1;
  return counts;
});

const comparisons = computed(() => snapshot.value?.comparisons ?? []);
const validComparisons = computed(() => comparisons.value.filter((c) => c.comparisonValid && !c.confounded));
const confoundedComparisons = computed(() => comparisons.value.filter((c) => c.confounded));
const invalidComparisons = computed(() => comparisons.value.filter((c) => !c.comparisonValid && !c.confounded));

const allClaims = computed(() => experiments.value.flatMap((e) => e.claims));
const verdictCounts = computed(() => {
  const counts: Record<string, number> = {};
  for (const c of allClaims.value) {
    const verdict = c.auditResult?.finalVerdict ?? "尚未稽核";
    counts[verdict] = (counts[verdict] ?? 0) + 1;
  }
  return counts;
});

const metricDirectionByName = computed(() => {
  const map = new Map<string, MetricDirection>();
  // 沒有方向定義的 metric 不進這張表——查不到就代表「不判定」，不是預設某個方向。
  for (const m of snapshot.value?.metricDefinitions ?? []) {
    if (m.direction) map.set(m.name, m.direction);
  }
  return map;
});

interface CredibleChange {
  experimentId: string;
  runA: string;
  runB: string;
  metric: string;
  direction: "improvement" | "regression";
  relativeDiff: number | null;
}

// 規則 6：只有 comparison_valid（且非 confounded，validComparisons 已濾掉）且 metric
// 有方向定義才算數——沒有方向定義的 metric 不進這個清單，不猜方向。
const credibleChanges = computed<CredibleChange[]>(() => {
  const out: CredibleChange[] = [];
  for (const c of validComparisons.value) {
    for (const m of c.metrics) {
      if (!m.computed || !m.definitionConsistent || m.absoluteDiff === null) continue;
      const direction = metricDirectionByName.value.get(m.metric);
      if (!direction) continue;
      const improved = direction === "higher_is_better" ? m.absoluteDiff > 0 : m.absoluteDiff < 0;
      const worsened = direction === "higher_is_better" ? m.absoluteDiff < 0 : m.absoluteDiff > 0;
      if (improved) {
        out.push({ experimentId: c.experimentId, runA: c.runA, runB: c.runB, metric: m.metric, direction: "improvement", relativeDiff: m.relativeDiff });
      } else if (worsened) {
        out.push({ experimentId: c.experimentId, runA: c.runA, runB: c.runB, metric: m.metric, direction: "regression", relativeDiff: m.relativeDiff });
      }
    }
  }
  return out;
});

const diagnostics = computed(() => snapshot.value?.diagnostics ?? []);

const lastUpdated = computed(() => {
  const timestamps = allRuns.value.map((r) => r.createdAt).filter((t): t is string => Boolean(t));
  return timestamps.length > 0 ? [...timestamps].sort().at(-1) : null;
});
</script>

<template>
  <section>
    <h2>總覽</h2>

    <div class="stat-grid">
      <div class="stat">
        <div class="stat-value">{{ experiments.length }}</div>
        <div class="stat-label">實驗數</div>
      </div>
      <div v-for="(count, status) in runStatusCounts" :key="`run-${status}`" class="stat">
        <div class="stat-value">{{ count }}</div>
        <div class="stat-label">執行：{{ statusLabel(String(status)) }}</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ validComparisons.length }}</div>
        <div class="stat-label">有效比較</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ confoundedComparisons.length }}</div>
        <div class="stat-label">已混雜的比較</div>
      </div>      <div class="stat">
        <div class="stat-value">{{ invalidComparisons.length }}</div>
        <div class="stat-label">無效比較</div>
      </div>
      <div v-for="(count, verdict) in verdictCounts" :key="`claim-${verdict}`" class="stat">
        <div class="stat-value">{{ count }}</div>
        <div class="stat-label">主張：{{ statusLabel(String(verdict)) }}</div>
      </div>
    </div>

    <p class="hint">最近更新：<code>{{ lastUpdated ?? "（無資料）" }}</code></p>

    <h3>可信的改善與退步</h3>
    <p class="hint">只列 comparison_valid 為 true、非 confounded，且 指標有 higher_is_better 或 lower_is_better 方向定義的結果。</p>
    <table v-if="credibleChanges.length > 0">
      <thead>
        <tr>
          <th>實驗</th>
          <th>執行 A → 執行 B</th>
          <th>指標</th>
          <th>結果</th>
          <th>相對差異</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(c, i) in credibleChanges" :key="i">
          <td>{{ c.experimentId }}</td>
          <td>{{ c.runA }} → {{ c.runB }}</td>
          <td>{{ c.metric }}</td>
          <td>
            <span class="badge" :class="c.direction === 'improvement' ? 'badge-good' : 'badge-bad'">{{ c.direction === "improvement" ? "改善（improvement）" : "退步（regression）" }}</span>
          </td>
          <td>{{ c.relativeDiff !== null ? (c.relativeDiff * 100).toFixed(1) + "%" : "—" }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="hint">目前沒有符合條件的比較結果。</p>

    <h3>資料錯誤摘要（{{ diagnostics.length }}）</h3>
    <ul v-if="diagnostics.length > 0" class="diagnostics-list">
      <li v-for="(d, i) in diagnostics" :key="i" :class="d.level === 'error' ? 'errors' : 'hint'">
        [{{ statusLabel(d.level) }}] {{ d.message }} <code v-if="d.sourcePath">{{ d.sourcePath }}</code>
      </li>
    </ul>
    <p v-else class="hint">沒有任何資料解析錯誤。</p>
  </section>
</template>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(150px, 100%), 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.stat {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: var(--space-2) var(--space-3);
}
.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-heading);
}
.stat-label {
  font-size: 11px;
  color: var(--color-text-muted);
}
.diagnostics-list {
  list-style: none;
  padding: 0;
  font-size: 12px;
}
.diagnostics-list li {
  padding: 2px 0;
}
</style>
