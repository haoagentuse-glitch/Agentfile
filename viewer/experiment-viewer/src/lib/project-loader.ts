// 唯一對外入口：loadProject(root) -> ProjectSnapshot。
// UI 只認這一個函式，不知道底下是 canonical records 目錄慣例還是 viewer.json manifest，
// 也不用自己判斷要挑哪個 adapter、不用碰路徑解析或 I/O（Deep Module）。
//
// PROJECT_ROOT 契約：使用者可能指到 project 根目錄，也可能（沿用舊習慣）直接指到
// `<projectRoot>/records/experiments`——resolveProjectLayout 把兩種輸入都解析回同一組
// (projectRoot, recordsRoot)，之後一律用 projectRoot 做 containment。

import type { ProjectSnapshot } from "./canonical";
import { loadCanonicalProject } from "./canonical-adapter";
import { loadManifestProject, parseViewerManifest } from "./manifest-adapter";
import { pathExists, readProjectFile, resolveProjectLayout } from "./tauri-fs";

const VIEWER_MANIFEST_RELATIVE = "records/experiments/viewer.json";

export async function loadProject(rawRoot: string): Promise<ProjectSnapshot> {
  const layout = await resolveProjectLayout(rawRoot);

  // 只有「檔案真的不存在」才代表這個 profile 沒有自訂 mapping，走 canonical adapter；
  // 任何其他失敗（權限等）都要往上拋，不能跟「不存在」混為一談。
  const manifestPresent = await pathExists(layout.projectRoot, VIEWER_MANIFEST_RELATIVE);
  if (!manifestPresent) {
    return loadCanonicalProject(layout);
  }

  try {
    const manifestText = await readProjectFile(layout.projectRoot, VIEWER_MANIFEST_RELATIVE);
    const manifest = parseViewerManifest(JSON.parse(manifestText));
    return await loadManifestProject(layout, manifest);
  } catch (e) {
    // viewer.json 存在但格式錯誤——回一筆 diagnostics error，不猜測性地退回 canonical
    // adapter 掩蓋設定錯誤。
    return {
      projectRoot: layout.projectRoot,
      recordsRoot: layout.recordsRoot,
      rootKind: layout.rootKind,
      adapterKind: "manifest",
      experiments: [],
      comparisons: [],
      metricDefinitions: [],
      artifacts: [],
      genericCollections: [],
      diagnostics: [{ level: "error", message: String(e), sourcePath: VIEWER_MANIFEST_RELATIVE }],
    };
  }
}
