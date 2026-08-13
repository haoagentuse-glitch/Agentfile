<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useProjectStore } from "../store/project";
import DataTable from "../components/DataTable.vue";

const { snapshot } = useProjectStore();
const router = useRouter();

const columns = [
  { key: "experimentId", label: "experiment_id" },
  { key: "status", label: "status" },
  { key: "runs", label: "runs" },
  { key: "claims", label: "claims" },
  { key: "gate", label: "gate level" },
];

const rows = computed(() =>
  (snapshot.value?.experiments ?? []).map((e) => ({
    experimentId: e.experimentId,
    status: e.status,
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
    <h2>Experiments（{{ rows.length }}）</h2>
    <DataTable
      v-if="rows.length > 0"
      :columns="columns"
      :rows="rows"
      :row-key="(row) => String(row.experimentId)"
      @select="openExperiment"
    />
    <p v-else class="hint">這個 project root 底下還沒有任何 experiment。</p>
  </section>
</template>
