<script setup lang="ts">
import { computed } from "vue";
import { useProjectStore } from "../store/project";
import { statusLabel } from "../lib/status-label";

const { snapshot } = useProjectStore();
const diagnostics = computed(() => snapshot.value?.diagnostics ?? []);
</script>

<template>
  <section>
    <h2>診斷與關於</h2>

    <h3>目前專案</h3>
    <table v-if="snapshot">
      <tbody>
        <tr><th>專案根目錄</th><td><code>{{ snapshot.projectRoot }}</code></td></tr>
        <tr><th>紀錄根目錄</th><td><code>{{ snapshot.recordsRoot }}</code></td></tr>
        <tr><th>根目錄路徑類型</th><td>{{ snapshot.rootKind }}</td></tr>
        <tr><th>資料轉接器</th><td>{{ snapshot.adapterKind === "canonical" ? "標準紀錄（definitions/runs/claims/…）" : "viewer.json 清單" }}</td></tr>
        <tr><th>實驗數</th><td>{{ snapshot.experiments.length }}</td></tr>
        <tr><th>比較數</th><td>{{ snapshot.comparisons.length }}</td></tr>
        <tr><th>指標定義數</th><td>{{ snapshot.metricDefinitions.length }}</td></tr>
        <tr><th>產物數</th><td>{{ snapshot.artifacts.length }}</td></tr>
      </tbody>
    </table>
    <p v-else class="hint">尚未選擇專案根目錄。</p>

    <h3>解析錯誤／警告（{{ diagnostics.length }}）</h3>
    <table v-if="diagnostics.length > 0">
      <thead>
        <tr>
          <th>等級</th>
          <th>訊息</th>
          <th>來源</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(d, i) in diagnostics" :key="i">
          <td><span class="badge" :class="d.level === 'error' ? 'badge-bad' : 'badge-warn'">{{ statusLabel(d.level) }}</span></td>
          <td>{{ d.message }}</td>
          <td><code v-if="d.sourcePath">{{ d.sourcePath }}</code></td>
        </tr>
      </tbody>
    </table>
    <p v-else class="hint">沒有任何資料解析錯誤或警告。</p>

    <h3>關於</h3>
    <p class="hint">
      實驗檢視器是本機、唯讀的實驗瀏覽器：不寫回、不刪除、不重跑實驗、沒有帳號或雲端同步。
      資料的唯一來源永遠是選定的專案根目錄資料夾——這裡看到的一切都是它的投影，不是第二份權威副本。
    </p>
  </section>
</template>
