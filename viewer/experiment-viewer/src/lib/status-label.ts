const STATUS_LABELS: Readonly<Record<string, string>> = {
  confounded: "已混雜（confounded）",
  invalid: "無效（invalid）",
  fully_supported: "已支援（fully_supported）",
  partially_supported: "部分支援（partially_supported）",
  unsupported: "不支援（unsupported）",
  unauditable: "無法稽核（unauditable）",
  overreaching: "超出證據範圍（overreaching）",
  supported: "已支援（supported）",
  refuted: "已反駁（refuted）",
  inconclusive: "無法判定（inconclusive）",
  pending: "待處理（pending）",
  running: "執行中（running）",
  completed: "已完成（completed）",
  passed: "通過（passed）",
  failed: "失敗（failed）",
  aborted: "已中止（aborted）",
  error: "錯誤（error）",
  warning: "警告（warning）",
  active: "使用中（active）",
  archived: "已封存（archived）",
  candidate: "候選（candidate）",
  unverified: "未驗證（unverified）",
};

/** 翻譯已知技術狀態，並保留原碼。未知值必須原樣顯示。 */
export function statusLabel(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  return STATUS_LABELS[value] ?? value;
}
