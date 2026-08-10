# Graphify 列為 optional 的未來結構檢索層，v1 不啟用

三種檢索各有分工：字面用 `rg`、語意與歷史用 memsearch，但「現行程式碼的結構」（symbol、import、call、dependency、影響範圍）目前沒有工具負責——多檔案探索或多 agent 重複讀檔時，只能整檔讀或用 `rg` 硬猜，成本隨 repo 複雜度上升。

研究了 Graphify（本機 tree-sitter 靜態分析、零 LLM 呼叫、40+ 語言，跟主流 AI coding agent 都有整合），符合「結構檢索」這個缺口。決定：列為 optional 的未來層，v1 不安裝、不啟用。原則見 AGENTS.md「檢索」一節。

## 啟用門檻

不是「聽起來有用」就裝。等以下任一項有實際證據才評估啟用：

- repo 複雜度：單一改動要跨讀的檔案數，人工判斷已經吃力
- 多 agent 重複讀同一批檔案探結構，讀檔/token 成本可觀測地重複
- 有 `docs/eval/` 的實測資料佐證，不是「架構上看起來該有」

## 若啟用，範圍限制

Graphify 預設會把 markdown、文件、架構圖也吃進同一張圖裡——這跟 memsearch 的職責重疊，且提供一鍵 git commit hook 讓圖自動重建。兩者都不能照預設用：

- 只准餵程式碼路徑。`docs/`、`CONTEXT.md`、`docs/adr/`、conversation memory、Issue、task state 一律排除——這些已經各有 SSoT 擁有者，見 AGENTS.md 職責邊界表。一旦這些邊界混進同一個檢索工具，「檢索結果」會悄悄變成「決策依據」。
- 不裝自動重建 hook。graph 是可刪除重建的衍生產物，建置時機由人／agent 按需觸發，不綁進 git 生命週期。

## Consequences

- 現在：三層分工少一層，遇到深度呼叫鏈或大量跨檔探索時只能靠 `rg`／整檔讀，成本較高但可接受——目前沒有專案複雜到讓這個成本被實測看見。
- 之後真的啟用：多一個外部依賴，機器層安裝，走跟 memsearch 一樣的「`apply.sh` 只檢查不攜帶」模式；graph 資料夾本身是本機衍生物，比照 `.memsearch/` 處理，不進版控。
- Graphify 本身很新，成長速度極快但生產環境戰績還薄——先觀察，不綁死；`AGENTS.md` 只記原則與門檻，不記版本號或安裝指令，避免這份 ADR 隨工具改版過時。
