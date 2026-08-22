<script setup lang="ts">
import { computed, ref } from "vue";
import { useProjectStore } from "../store/project";
import DataTable, { type DataTableColumn } from "../components/DataTable.vue";
import Drawer from "../components/Drawer.vue";
import type { GenericRecord, GenericRecordCollection } from "../lib/canonical";
import { getByPath } from "../lib/dot-path";

const { snapshot } = useProjectStore();

const metricColumns: DataTableColumn[] = [
  { key: "name", label: "名稱" },
  { key: "displayName", label: "顯示名稱" },
  { key: "type", label: "類型" },
  { key: "direction", label: "方向" },
  { key: "unit", label: "單位" },
  { key: "format", label: "格式" },
  { key: "aggregation", label: "彙總方式" },
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
        // 原值直接放進去，不先轉字串——缺值、物件、陣列的顯示規則由 DataTable
        // 的 cell-value 統一決定，在這裡先壓成 "—" 會把型別資訊丟掉。
        row[path] = getByPath(r.fields, path);
      }
      return row;
    });
  }
  return collection.records.map((r) => ({ __id: r.id, id: r.id, sourcePath: r.sourcePath }));
}

const selectedRecord = ref<GenericRecord | null>(null);
// 表格塞不下的長值走這裡，不是把整格撐開讓那一列讀不了。
const expanded = ref<{ label: string; content: string } | null>(null);

function openRecord(collection: GenericRecordCollection, row: Record<string, unknown>) {
  selectedRecord.value = collection.records.find((r) => r.id === row.__id) ?? null;
}
</script>

<template>
  <section>
    <h2>紀錄</h2>

    <h3>指標定義（{{ metricRows.length }}）</h3>
    <DataTable v-if="metricRows.length > 0" :columns="metricColumns" :rows="metricRows" :row-key="(row) => String(row.name)" groupable />
    <p v-else class="hint">沒有任何指標定義。</p>

    <template v-if="genericCollections.length > 0">
      <div v-for="collection in genericCollections" :key="collection.name">
        <h3>{{ collection.name }}（{{ collection.records.length }}，viewer.json 額外集合）</h3>
        <DataTable
          :columns="columnsFor(collection)"
          :rows="rowsFor(collection)"
          :row-key="(row) => String(row.__id)"
          groupable
          @select="(row) => openRecord(collection, row)"
          @expand="(payload) => (expanded = payload)"
        />
      </div>
    </template>
    <p v-else class="hint">沒有 viewer.json 定義的額外紀錄集合。</p>

    <Drawer :open="selectedRecord !== null" :title="selectedRecord?.id ?? ''" @close="selectedRecord = null">
      <pre v-if="selectedRecord">{{ JSON.stringify(selectedRecord.fields, null, 2) }}</pre>
    </Drawer>

    <Drawer :open="expanded !== null" :title="expanded?.label ?? ''" @close="expanded = null">
      <pre v-if="expanded">{{ expanded.content }}</pre>
    </Drawer>
  </section>
</template>
