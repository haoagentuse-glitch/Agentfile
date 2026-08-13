// viewer.json 的 format 使用小而明確的 d3-format 子集合：
// `.N%` 把 ratio 乘 100 後保留 N 位；`.Nf` 保留 N 位小數。其他值忠實回退原始數字。
// precision 限制 0–20；超界格式不得讓不可信 manifest 觸發 toFixed RangeError。
function precisionOf(format: string | undefined, suffix: "%" | "f"): number | null {
  const match = new RegExp(`^\\.(\\d+)${suffix}$`).exec(format ?? "");
  if (!match) return null;
  const precision = Number(match[1]);
  return precision <= 20 ? precision : null;
}

export function formatMetricValue(value: number | null, format?: string): string {
  if (value === null) return "—";

  const percentPrecision = precisionOf(format, "%");
  if (percentPrecision !== null) return `${(value * 100).toFixed(percentPrecision)}%`;

  const fixedPrecision = precisionOf(format, "f");
  if (fixedPrecision !== null) return value.toFixed(fixedPrecision);

  return String(value);
}

export function formatIncludesUnit(format?: string): boolean {
  return precisionOf(format, "%") === null;
}