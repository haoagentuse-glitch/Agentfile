// 全域專案狀態——單例 module-level ref，不引入 Pinia：這個 app 只有一份 ProjectSnapshot，
// 不需要多 store／模組化狀態管理的複雜度（YAGNI）。

import { ref } from "vue";
import type { ProjectSnapshot } from "../lib/canonical";
import { loadProject } from "../lib/project-loader";

const snapshot = ref<ProjectSnapshot | null>(null);
const loading = ref(false);
const loadError = ref<string | null>(null);

async function openRoot(root: string): Promise<void> {
  loading.value = true;
  loadError.value = null;
  try {
    snapshot.value = await loadProject(root);
  } catch (e) {
    snapshot.value = null;
    loadError.value = String(e);
  } finally {
    loading.value = false;
  }
}

export function useProjectStore() {
  return { snapshot, loading, loadError, openRoot };
}
