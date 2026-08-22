<script setup lang="ts">
// Compare 分頁專用：從這個 experiment 既有的 comparison-result 記錄裡選一組來看，
// 不是讓使用者臨時挑兩個 run 現算——viewer 只渲染 compare-runs 已產生的結果（規則 5）。
import type { CanonicalComparison } from "../lib/canonical";
import { describeComparisonStatus } from "../lib/comparison-status";
import { statusLabel } from "../lib/status-label";

const props = defineProps<{
  comparisons: CanonicalComparison[];
  modelValue: CanonicalComparison | null;
}>();
const emit = defineEmits<{ "update:modelValue": [value: CanonicalComparison | null] }>();

function onChange(e: Event) {
  const index = (e.target as HTMLSelectElement).value;
  if (index === "") {
    emit("update:modelValue", null);
    return;
  }
  emit("update:modelValue", props.comparisons[Number(index)] ?? null);
}

function statusSuffix(c: CanonicalComparison): string {
  const status = describeComparisonStatus(c);
  if (status === "confounded") return "　⚠ " + statusLabel(status);
  if (status === "invalid") return "　⚠ " + statusLabel(status);
  return "";
}
</script>

<template>
  <select :value="modelValue ? comparisons.indexOf(modelValue) : ''" @change="onChange">
    <option value="">（選擇一組比較）</option>
    <option v-for="(c, i) in comparisons" :key="i" :value="i">
      {{ c.runA }} 對比 {{ c.runB }}{{ statusSuffix(c) }}
    </option>
  </select>
</template>
