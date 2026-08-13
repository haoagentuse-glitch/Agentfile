// 受限的 dot-path 取值——只支援 "a.b.c" 這種物件鍵路徑，不支援陣列索引、萬用字元、
// 運算式或任何腳本。viewer.json 只能用這個，不是完整的 JSONPath engine（AGENTS.md 檢索一節）。
// 陣列一律視為不可穿越——即使某個 key 字面上長得像索引（"0"）或萬用字元（"*"），
// 只要中途經過的是陣列就直接回 undefined，不會被當成合法的陣列存取。

export function getByPath(record: unknown, path: string): unknown {
  if (!path) return undefined;
  let current: unknown = record;
  for (const key of path.split(".")) {
    if (typeof current !== "object" || current === null || Array.isArray(current)) return undefined;
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

export function getStringByPath(record: unknown, path: string | undefined): string | undefined {
  if (!path) return undefined;
  const value = getByPath(record, path);
  return typeof value === "string" ? value : undefined;
}

export function getNumberRecordByPath(record: unknown, path: string | undefined): Record<string, number> {
  if (!path) return {};
  const value = getByPath(record, path);
  if (typeof value !== "object" || value === null || Array.isArray(value)) return {};
  const result: Record<string, number> = {};
  for (const [key, v] of Object.entries(value as Record<string, unknown>)) {
    if (typeof v === "number") result[key] = v;
  }
  return result;
}
