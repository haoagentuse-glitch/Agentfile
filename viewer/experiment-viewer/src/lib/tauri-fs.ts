// 所有跨 project root 邊界的檔案存取都透過 Rust command，不直接用 @tauri-apps/plugin-fs——
// containment 檢查（擋 `..` 跳脫、擋 symlink 逃出 root）在 Rust 那層做，Vue 只丟相對路徑字串，
// 不切割、不用 '/' 拼 OS path。見 src-tauri/src/paths.rs。

import { invoke } from "@tauri-apps/api/core";

// 啟動時如果有 CLI 參數（`experiment-viewer.exe PROJECT_ROOT`），回傳那個路徑；
// 沒有就回 null，前端退回 folder picker。
export async function initialProjectRoot(): Promise<string | null> {
  return invoke<string | null>("initial_project_root");
}

export interface ProjectLayout {
  projectRoot: string;
  recordsRoot: string;
  rootKind: string;
}

// PROJECT_ROOT 契約：使用者可能指到 project 根目錄，也可能（沿用舊習慣）直接指到
// `<projectRoot>/records/experiments`——這個 command 把兩種輸入都解析回同一組
// (projectRoot, recordsRoot)。containment 之後一律以 projectRoot 為界。
export async function resolveProjectLayout(input: string): Promise<ProjectLayout> {
  return invoke<ProjectLayout>("resolve_project_layout", { input });
}

// 目錄不存在＝這個 profile 還沒有這類紀錄的空狀態，由 Rust 端直接回傳空陣列；
// 其他錯誤（權限、跳脫 root）會被 invoke() 丟出來，呼叫端要接住記成 diagnostic，
// 不可以在這裡 catch-all 吞掉——那樣會把真正的錯誤偽裝成空狀態。
// 回傳值是已經 containment 驗證過、相對 project root 的路徑字串，直接拿去餵
// readProjectFile 即可，不需要（也不應該）自己再拼字串。
export async function listProjectDir(root: string, relative: string): Promise<string[]> {
  return invoke<string[]>("list_project_dir", { root, relative });
}

export async function readProjectFile(root: string, relative: string): Promise<string> {
  return invoke<string>("read_project_file", { root, relative });
}

// 專門回答「這個檔案存不存在」的是非題（例如判斷 viewer.json 在不在），
// 不透過字串比對錯誤訊息去猜測是不是 NotFound。
export async function pathExists(root: string, relative: string): Promise<boolean> {
  return invoke<boolean>("path_exists", { root, relative });
}

// containment 與 OS opener 都在同一個 Rust command；前端不取得絕對路徑，
// 也不需要 opener:allow-open-path capability。
export async function openArtifact(root: string, relative: string): Promise<void> {
  return invoke<void>("open_artifact", { root, relative });
}
