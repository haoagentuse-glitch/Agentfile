// 測試專用的 tauri-fs 替身，用 Node 內建 fs 讀 tests/fixtures/ 底下的真實檔案，
// 讓 adapter／project-loader 測試不需要真的跑在 Tauri runtime 裡。鏡射 Rust 端
// src-tauri/src/paths.rs 的邏輯（NotFound 與其他錯誤分開、project root ↔
// records/experiments 佈局解析），保持跟 production 行為一致。
// 只在 `vi.mock("../tauri-fs", ...)` 底下使用，不是產品程式碼的一部分。

import { promises as fs } from "node:fs";
import path from "node:path";
import type { ProjectLayout } from "../tauri-fs";

export async function initialProjectRoot(): Promise<string | null> {
  return null;
}

function isNotFound(e: unknown): boolean {
  return typeof e === "object" && e !== null && "code" in e && (e as { code: unknown }).code === "ENOENT";
}

// 鏡射 paths::resolve_project_layout：使用者可能指到 project 根目錄，也可能直接指到
// `<projectRoot>/records/experiments`，兩種輸入都要推回同一組 (projectRoot, recordsRoot)。
export async function resolveProjectLayout(input: string): Promise<ProjectLayout> {
  const stat = await fs.stat(input);
  if (!stat.isDirectory()) {
    throw new Error(`${input} 不是資料夾`);
  }
  const canon = path.resolve(input);
  const segments = canon.split(path.sep);
  const last = segments.at(-1)?.toLowerCase();
  const secondLast = segments.at(-2)?.toLowerCase();

  if (last === "experiments" && secondLast === "records") {
    const projectRoot = path.join(canon, "..", "..");
    return { projectRoot, recordsRoot: canon, rootKind: "relative" };
  }
  return { projectRoot: canon, recordsRoot: path.join(canon, "records", "experiments"), rootKind: "relative" };
}

// 目錄不存在＝空狀態；目錄其實是檔案（ENOTDIR）之類的其他錯誤要丟出去，
// 不能被吞掉偽裝成空狀態——鏡射 Rust 端 list_project_dir 的行為。
export async function listProjectDir(root: string, relative: string): Promise<string[]> {
  const dir = path.join(root, relative);
  let entries: string[];
  try {
    entries = await fs.readdir(dir);
  } catch (e) {
    if (isNotFound(e)) return [];
    throw e;
  }
  return entries.map((name) => `${relative}/${name}`).sort();
}

export async function readProjectFile(root: string, relative: string): Promise<string> {
  return fs.readFile(path.join(root, relative), "utf-8");
}

export async function pathExists(root: string, relative: string): Promise<boolean> {
  try {
    await fs.access(path.join(root, relative));
    return true;
  } catch (e) {
    if (isNotFound(e)) return false;
    throw e;
  }
}
