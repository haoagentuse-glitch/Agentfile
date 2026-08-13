<script setup lang="ts">
// 規則 6：只有 comparisonValid 為 true 且 metric 有 higher/lower-is-better 方向定義時，
// 才顯示 improvement/regression；否則一律顯示中性的 change，不猜方向。
// unit／format 來自 manifest 的 metric catalog（viewer.json），canonical metric definition
// 沒有這兩個欄位時就是 undefined，退回顯示原始數字。
import { computed } from "vue";
import type { MetricDirection } from "../lib/canonical";
import { formatIncludesUnit, formatMetricValue } from "../lib/metric-format";

const props = defineProps<{
  value: number | null;
  unit?: string;
  format?: string;
  direction?: MetricDirection;
  comparisonValid: boolean;
  diff: number | null;
}>();

const displayValue = computed(() => {
  return formatMetricValue(props.value, props.format);
});

const badge = computed(() => {
  if (!props.comparisonValid || !props.direction || props.diff === null) {
    return { label: "change", cls: "badge" };
  }
  const improved = props.direction === "higher_is_better" ? props.diff > 0 : props.diff < 0;
  const worsened = props.direction === "higher_is_better" ? props.diff < 0 : props.diff > 0;
  if (improved) return { label: "improvement", cls: "badge badge-good" };
  if (worsened) return { label: "regression", cls: "badge badge-bad" };
  return { label: "no change", cls: "badge" };
});
</script>

<template>
  <span class="metric-value">
    <span class="value">{{ displayValue }}</span>
    <span v-if="unit && formatIncludesUnit(format)" class="unit">{{ unit }}</span>
    <span :class="badge.cls">{{ badge.label }}</span>
  </span>
</template>

<style scoped>
.metric-value {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.unit {
  color: var(--color-text-muted);
  font-size: 11px;
}
</style>
