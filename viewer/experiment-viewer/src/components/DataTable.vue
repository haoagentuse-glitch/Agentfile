<script setup lang="ts">
// 共用表格外殼——Runs／Claims／Experiments／generic collections 共用文字篩選、欄位排序、
// 可選分組與點列開 Drawer。欄位內容用具名 slot 客製，不強迫呼叫端使用同一種 cell 型別。
import { computed, ref } from "vue";

export interface DataTableColumn {
  key: string;
  label: string;
}

const props = defineProps<{
  columns: DataTableColumn[];
  rows: Array<Record<string, unknown>>;
  rowKey: (row: Record<string, unknown>) => string;
  selectedKey?: string | null;
  groupable?: boolean;
}>();

const emit = defineEmits<{ select: [row: Record<string, unknown>] }>();

const filterText = ref("");
const sortKey = ref<string | null>(null);
const sortDir = ref<"asc" | "desc">("asc");
const groupKey = ref("");

const filteredRows = computed(() => {
  const query = filterText.value.trim().toLowerCase();
  if (!query) return props.rows;
  return props.rows.filter((row) =>
    Object.values(row).some((value) => String(value ?? "").toLowerCase().includes(query))
  );
});

const sortedRows = computed(() => {
  if (!sortKey.value) return filteredRows.value;
  const key = sortKey.value;
  const dir = sortDir.value === "asc" ? 1 : -1;
  return [...filteredRows.value].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
    return String(av ?? "").localeCompare(String(bv ?? "")) * dir;
  });
});

const groupedRows = computed(() => {
  if (!props.groupable || !groupKey.value) {
    return [{ key: "all", label: null as string | null, rows: sortedRows.value }];
  }

  const groups = new Map<string, Array<Record<string, unknown>>>();
  for (const row of sortedRows.value) {
    const label = String(row[groupKey.value] ?? "（空值）");
    const group = groups.get(label) ?? [];
    group.push(row);
    groups.set(label, group);
  }
  return [...groups.entries()].map(([label, rows]) => ({ key: label, label, rows }));
});

function toggleSort(key: string) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = key;
    sortDir.value = "asc";
  }
}
</script>

<template>
  <div class="data-table">
    <div class="table-controls">
      <input
        v-model="filterText"
        type="text"
        class="filter-input"
        placeholder="篩選…"
        aria-label="篩選表格內容"
      />
      <label v-if="groupable" class="group-control">
        group by
        <select v-model="groupKey" aria-label="依欄位分組">
          <option value="">不分組</option>
          <option v-for="col in columns" :key="col.key" :value="col.key">{{ col.label }}</option>
        </select>
      </label>
    </div>

    <table>
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key">
            <button type="button" class="sort-button" @click="toggleSort(col.key)">
              {{ col.label }}
              <span v-if="sortKey === col.key" class="sort-indicator">{{ sortDir === "asc" ? "▲" : "▼" }}</span>
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-for="group in groupedRows" :key="group.key">
          <tr v-if="group.label !== null" class="group-row">
            <th :colspan="columns.length">{{ group.label }}（{{ group.rows.length }}）</th>
          </tr>
          <tr
            v-for="row in group.rows"
            :key="rowKey(row)"
            :class="{ selected: selectedKey === rowKey(row) }"
            tabindex="0"
            @click="emit('select', row)"
            @keydown.enter="emit('select', row)"
          >
            <td v-for="col in columns" :key="col.key">
              <slot :name="col.key" :row="row">{{ row[col.key] }}</slot>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <p v-if="sortedRows.length === 0" class="hint">沒有符合篩選條件的資料列。</p>
  </div>
</template>

<style scoped>
.data-table {
  overflow-x: auto;
}
.table-controls {
  display: flex;
  align-items: flex-end;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-2);
}
.filter-input {
  width: 100%;
  max-width: 280px;
}
.group-control {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-size: 11px;
}
.group-row th {
  background: rgba(38, 139, 210, 0.08);
  color: var(--color-heading);
}
.group-row:hover {
  cursor: default;
}
.sort-button {
  background: transparent;
  border: none;
  padding: 0;
  font: inherit;
  font-weight: 600;
  color: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.sort-indicator {
  font-size: 9px;
}
</style>