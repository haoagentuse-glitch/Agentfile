# 決策帳本

- 決定｜`agentfile build` 在建置時解析 profile 繼承，輸出完整且獨立的發行目錄。｜證據｜`tests/test_build.py` 驗證 core 隔離、experimental 繼承、雙技能目錄與逐位元確定性。｜什麼會推翻它｜第二個以上 profile 出現無法用 layer 與碰撞失敗表達的合法覆寫需求。
- 決定｜複製後的 Agentfile 檔案屬於目標專案，不保存安裝狀態，也不建立上下游回報協定。｜證據｜目標使用方式只需 build 與 copy；舊投影同步需要額外定義衝突、刪除與版本語意。｜什麼會推翻它｜三個以上專案反覆遺漏安全更新，且可用無狀態差異工具處理。
- 決定｜一般軟體生命週期採固定版本的 `obra/superpowers`，Agentfile 只增加中文輸出與文件優先規則。｜證據｜superpowers 已提供設計、計畫、TDD、驗證與審查的完整接力。｜什麼會推翻它｜實跑顯示其中一個必要階段無法在 Claude Code 與 Codex 的檔案式技能入口工作。
- 決定｜experimental 的確定性操作統一由 `experiment_records` CLI 提供，skill 不持有腳本。｜證據｜schema、生命週期、比較、claim audit 與 Compute Gate 共用同一套結構化契約與測試。｜什麼會推翻它｜出現必須使用不同 runtime 或無法共同鎖定依賴的確定性工具。
- 決定｜Viewer 是獨立 Windows 原生工具，不進入任何 Agentfile 發行包。｜證據｜Viewer 有自己的 Tauri、Vue、Rust、Windows PE 與 installer 發行流程。｜什麼會推翻它｜Viewer 改成 profile 執行期不可分割的必要元件，並由新 ADR 取代 ADR 0012 與 0023。
