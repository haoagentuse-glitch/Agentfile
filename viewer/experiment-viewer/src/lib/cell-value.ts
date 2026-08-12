// 通用欄位的顯示規則。Records 分頁的欄位由 viewer.json 宣告，值可以是任何東西：
// 缺值、純量、物件、陣列、超長字串。沒有這一層的話 `{{ row[key] }}` 會把物件印成
// `[object Object]`，那是把「有資料但顯示不出來」偽裝成「有一個叫這個名字的值」。
//
// 這裡只決定「怎麼顯示」，不決定「是什麼意思」——不猜型別語意，不做單位換算。

export type CellKind = "empty" | "text" | "number" | "boolean" | "object" | "array";

export interface CellView {
  kind: CellKind;
  // 表格內顯示的文字。已截斷時是截斷後的版本。
  text: string;
  // 需要開 Drawer 才看得完的完整內容；不需要時是 undefined。
  full?: string;
  truncated: boolean;
}

// 表格單格的字數上限。超過就截斷並提供完整內容入口——一格塞進整份 JSON，
// 那一列就沒辦法讀了。
export const MAX_CELL_CHARS = 120;

const EMPTY_TEXT = "—";

function truncate(text: string, kind: CellKind): CellView {
  if (text.length <= MAX_CELL_CHARS) return { kind, text, truncated: false };
  return { kind, text: `${text.slice(0, MAX_CELL_CHARS)}…`, full: text, truncated: true };
}

/** 把任意值轉成可顯示的樣子。未知型別一律有明確 fallback，不會出現 [object Object]。 */
export function toCellView(value: unknown): CellView {
  if (value === null || value === undefined || value === "") {
    return { kind: "empty", text: EMPTY_TEXT, truncated: false };
  }

  if (typeof value === "boolean") {
    return { kind: "boolean", text: String(value), truncated: false };
  }

  if (typeof value === "number") {
    // NaN 與 Infinity 是真的出現過的資料問題，照實顯示，不靜默變成 0 或空白。
    return { kind: "number", text: Number.isFinite(value) ? String(value) : String(value), truncated: false };
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return { kind: "array", text: "[]（空陣列）", truncated: false };
    // 純量陣列直接列出來；含物件的陣列只給筆數，細節留給 Drawer。
    const scalar = value.every((item) => item === null || typeof item !== "object");
    const text = scalar ? value.map((item) => (item === null ? "null" : String(item))).join(", ") : `${value.length} 筆`;
    const view = truncate(text, "array");
    return { ...view, full: view.full ?? JSON.stringify(value, null, 2), truncated: view.truncated };
  }

  if (typeof value === "object") {
    const keys = Object.keys(value as Record<string, unknown>);
    if (keys.length === 0) return { kind: "object", text: "{}（空物件）", truncated: false };
    const text = `{ ${keys.slice(0, 4).join(", ")}${keys.length > 4 ? ", …" : ""} }`;
    return { kind: "object", text, full: JSON.stringify(value, null, 2), truncated: false };
  }

  return truncate(String(value), "text");
}

/** 排序與篩選共用的可比較值。未知型別絕不拋例外——一格壞資料不該讓整張表當掉。 */
export function toComparable(value: unknown): string | number {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return Number.isFinite(value) ? value : Number.MAX_VALUE;
  if (typeof value === "boolean") return String(value);
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      // 循環參照的資料仍然要能排序，只是排在一起。
      return "[circular]";
    }
  }
  return String(value);
}

/** 篩選用的搜尋文字：物件與陣列也要能被搜到，不能只搜得到純量欄位。 */
export function toSearchText(value: unknown): string {
  const comparable = toComparable(value);
  return String(comparable).toLowerCase();
}
