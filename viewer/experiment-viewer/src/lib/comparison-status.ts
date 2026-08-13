// comparisonValid=false 不等於 confounded=true——兩者是 comparison-result.schema.json
// 裡獨立的欄位。抽成一個純函式讓 Compare 分頁的呈現邏輯可以獨立測試，不用起 Vue
// component harness 就能驗證「invalid 不會被誤講成 confounded」這條規則。

import type { CanonicalComparison } from "./canonical";

export type ComparisonStatus = "confounded" | "invalid" | "valid";

export function describeComparisonStatus(
  comparison: Pick<CanonicalComparison, "confounded" | "comparisonValid">
): ComparisonStatus {
  if (comparison.confounded) return "confounded";
  if (!comparison.comparisonValid) return "invalid";
  return "valid";
}
