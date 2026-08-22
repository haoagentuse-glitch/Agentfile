<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useProjectStore } from "../store/project";
import { statusLabel } from "../lib/status-label";
import DataTable from "../components/DataTable.vue";

const { snapshot } = useProjectStore();
const router = useRouter();

const columns = [
  { key: "experimentId", label: "實驗 ID" },
  { key: "status", label: "狀態" },
  { key: "runs", label: "執行數" },
  { key: "claims", label: "主張數" },
  { key: "gate", label: "Gate 等級" },
];

const rows = computed(() =>
  (snapshot.value?.experiments ?? []).map((e) => ({
    experimentId: e.experimentId,
    status: statusLabel(e.status),
    runs: e.runs.length,
    claims: e.claims.length,
    gate: e.gateState?.currentLevel ?? "—",
  }))
);

function openExperiment(row: Record<string, unknown>) {
  router.push({ name: "experiment-workspace", params: { id: String(row.experimentId) } });
}
</script>

<template>
  <section>
    <h2>實驗（{{ rows.length }}）</h2>
    <DataTable
      v-if="rows.length > 0"
      :columns="columns"
      :rows="rows"
      :row-key="(row) => String(row.experimentId)"
      @select="openExperiment"
    />
    <p v-else class="hint">這個專案根目錄下還沒有任何實驗。</p>
  </section>
</template>
