# 決策帳本

- 決定｜experimental 的確定性操作統一由 `experiment_records` CLI 提供，skill 不持有腳本。｜證據｜投影後三個子命令 help 實跑通過；records 197/197。｜什麼會推翻它｜出現必須使用不同 runtime 或無法共同鎖定依賴的確定性工具。
- 決定｜run／lifecycle event 不可變；gate 是 history-only-append 的原子狀態投影；audit 機械輸出排他建立。｜證據｜既有 audit 防覆蓋回歸測試、gate 全套測試與原子 JSON writer。｜什麼會推翻它｜改採每次狀態轉移各自建立 event，且能由 event 重建 gate/audit 投影。
- 決定｜Viewer release gate 必須實際產生 portable PE 與 NSIS installer。｜證據｜Windows NTFS release 實跑，Vitest 104/104、Rust 16/16、兩份 PE 與 SHA-256 驗證通過。｜什麼會推翻它｜交付格式不再包含 Windows 安裝包，並由新 ADR 取代 ADR 0012。
