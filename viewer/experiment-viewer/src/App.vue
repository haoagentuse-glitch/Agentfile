<script setup lang="ts">
import { onMounted } from "vue";
import { open } from "@tauri-apps/plugin-dialog";
import NavRail from "./components/NavRail.vue";
import { useProjectStore } from "./store/project";
import { initialProjectRoot } from "./lib/tauri-fs";

const { snapshot, loading, loadError, openRoot } = useProjectStore();

onMounted(async () => {
  // initialProjectRoot() 本身也可能失敗（IPC 錯誤等）——一定要接住，不能讓它變成
  // unhandled promise rejection；失敗一律走 loadError，跟 openRoot() 內部的錯誤處理一致。
  try {
    const cliRoot = await initialProjectRoot();
    if (cliRoot) await openRoot(cliRoot);
  } catch (e) {
    loadError.value = String(e);
  }
});

async function pickRoot() {
  const dir = await open({ directory: true, title: "選擇專案根目錄（records/experiments/ 或 viewer.json 所在資料夾）" });
  if (!dir || Array.isArray(dir)) return;
  await openRoot(dir);
}
</script>

<template>
  <div class="layout">
    <NavRail />
    <main class="content">
      <header class="toolbar">
        <button @click="pickRoot">選擇專案根目錄</button>
        <span v-if="snapshot" class="path">
          <code>{{ snapshot.projectRoot }}</code>
          （{{ snapshot.adapterKind === "canonical" ? "canonical records" : "viewer.json manifest" }}）
        </span>
        <span v-if="loading" class="hint">載入中…</span>
      </header>

      <div v-if="loadError" class="errors">{{ loadError }}</div>

      <RouterView v-if="snapshot" />
      <p v-else-if="!loading" class="hint">
        只讀 <code>records/experiments/</code>（或 viewer.json 指定的資料夾），不寫回、不維護第二份權威副本——資料的唯一來源永遠是選定的專案根目錄。可以直接選擇專案根目錄，也可以沿用舊習慣選 <code>records/experiments/</code> 資料夾本身，兩種都能自動解析。
      </p>
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100%;
}
.content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  min-width: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
}
.path {
  font-size: 12px;
  color: var(--color-text-muted);
  word-break: break-all;
}

@media (max-width: 720px) {
  .layout {
    flex-direction: column;
    height: auto;
    min-height: 100%;
  }
}
</style>
