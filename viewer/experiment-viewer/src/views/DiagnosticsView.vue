<script setup lang="ts">
import { computed } from "vue";
import { useProjectStore } from "../store/project";

const { snapshot } = useProjectStore();
const diagnostics = computed(() => snapshot.value?.diagnostics ?? []);
</script>

<template>
  <section>
    <h2>Diagnostics / About</h2>

    <h3>目前的 project</h3>
    <table v-if="snapshot">
      <tbody>
        <tr><th>project root</th><td><code>{{ snapshot.projectRoot }}</code></td></tr>
        <tr><th>records root</th><td><code>{{ snapshot.recordsRoot }}</code></td></tr>
        <tr><th>root path 形狀</th><td>{{ snapshot.rootKind }}</td></tr>
        <tr><th>adapter</th><td>{{ snapshot.adapterKind === "canonical" ? "canonical records（definitions/runs/claims/…）" : "viewer.json manifest" }}</td></tr>
        <tr><th>experiments</th><td>{{ snapshot.experiments.length }}</td></tr>
        <tr><th>comparisons</th><td>{{ snapshot.comparisons.length }}</td></tr>
        <tr><th>metric definitions</th><td>{{ snapshot.metricDefinitions.length }}</td></tr>
        <tr><th>artifacts</th><td>{{ snapshot.artifacts.length }}</td></tr>
      </tbody>
    </table>
    <p v-else class="hint">還沒有選 project root。</p>

    <h3>解析錯誤／警告（{{ diagnostics.length }}）</h3>
    <table v-if="diagnostics.length > 0">
      <thead>
        <tr>
          <th>level</th>
          <th>message</th>
          <th>source</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(d, i) in diagnostics" :key="i">
          <td><span class="badge" :class="d.level === 'error' ? 'badge-bad' : 'badge-warn'">{{ d.level }}</span></td>
          <td>{{ d.message }}</td>
          <td><code v-if="d.sourcePath">{{ d.sourcePath }}</code></td>
        </tr>
      </tbody>
    </table>
    <p v-else class="hint">沒有任何資料解析錯誤或警告。</p>

    <h3>About</h3>
    <p class="hint">
      experiment-viewer 是本機、唯讀的實驗瀏覽器：不寫回、不刪除、不重跑實驗、沒有帳號或雲端同步。
      資料的唯一來源永遠是選定的 project root 資料夾——這裡看到的一切都是它的投影，不是第二份權威副本。
    </p>
  </section>
</template>
