<script setup lang="ts">
import { computed, ref } from "vue";
import { useProjectStore } from "../store/project";
import DataTable, { type DataTableColumn } from "../components/DataTable.vue";
import Drawer from "../components/Drawer.vue";
import type { GenericRecord, GenericRecordCollection } from "../lib/canonical";
import { getByPath } from "../lib/dot-path";

const { snapshot } = useProjectStore();

const metricColumns: DataTableColumn[] = [
  { key: "name", label: "name" },
  { key: "displayName", label: "display name" },
  { key: "type", label: "type" },
  { key: "direction", label: "direction" },
  { key: "unit", label: "unit" },
  { key: "format", label: "format" },
  { key: "aggregation", label: "aggregation" },
];

const metricRows = computed(() =>
  (snapshot.value?.metricDefinitions ?? []).map((m) => ({
    name: m.name,
    displayName: m.displayName ?? "—",
    type: m.type,
    // 沒有方向定義時忠實顯示「（未定義）」，不是空白讓人誤以為漏資料。
    direction: m.direction ?? "（未定義）",
    unit: m.unit ?? "—",
    format: m.format ?? "—",
    aggregation: m.aggregation,
  }))
);

const genericCollections = computed(() => snapshot.value?.genericCollections ?? []);

// viewer.json 有宣告 columns 就依那個動態畫欄位，不是寫死只顯示 id/source；
// 沒宣告才退回最基本的 id/source 兩欄。
function columnsFor(collection: GenericRecordCollection): DataTableColumn[] {
  if (collection.columns.length > 0) {
    return collection.columns.map((path) => ({ key: path, label: path }));
  }
  return [
    { key: "id", label: "id" },
    { key: "sourcePath", label: "source" },
  ];
}

function rowsFor(collection: GenericRecordCollection): Array<Record<string, unknown>> {
  if (collection.columns.length > 0) {
    return collection.records.map((r) => {
      const row: Record<string, unknown> = { __id: r.id };
      for (const path of collection.columns) {
        row[path] = getByPath(r.fields, path) ?? "—";
      }
      return row;
    });
  }
  return collection.records.map((r) => ({ __id: r.id, id: r.id, sourcePath: r.sourcePath }));
}

const selectedRecord = ref<GenericRecord | null>(null);

function openRecord(collection: GenericRecordCollection, row: Record<string, unknown>) {
  selectedRecord.value = collection.records.find((r) => r.id === row.__id) ?? null;
}
</script>

<template>
  <section>
    <h2>Records</h2>

    <h3>Metric Definitions（{{ metricRows.length }}）</h3>
    <DataTable v-if="metricRows.length > 0" :columns="metricColumns" :rows="metricRows" :row-key="(row) => String(row.name)" groupable />
    <p v-else class="hint">沒有任何 metric definition。</p>

    <template v-if="genericCollections.length > 0">
      <div v-for="collection in genericCollections" :key="collection.name">
        <h3>{{ collection.name }}（{{ collection.records.length }}，viewer.json 額外 collection）</h3>
        <DataTable
          :columns="columnsFor(collection)"
          :rows="rowsFor(collection)"
          :row-key="(row) => String(row.__id)"
          groupable
          @select="(row) => openRecord(collection, row)"
        />
      </div>
    </template>
    <p v-else class="hint">沒有 viewer.json 定義的額外 record collections。</p>

    <Drawer :open="selectedRecord !== null" :title="selectedRecord?.id ?? ''" @close="selectedRecord = null">
      <pre v-if="selectedRecord">{{ JSON.stringify(selectedRecord.fields, null, 2) }}</pre>
    </Drawer>
  </section>
</template>
