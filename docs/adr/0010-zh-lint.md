# zh-lint：中英夾雜檢查，Institutionalize Repeated Failures 的第一個實例

`AGENTS.md`「輸出」節一直都要求對使用者的一切輸出使用中文。這條規則沒變，變的是「靠人自己複查」這個做法反覆失守：同一個字（`funnel`）在這個 session 裡被抓到三次——使用者抓一次、後續兩輪自查各自又漏掉一次——即使中間已經明確承諾「定稿前自己先查一遍」。

依這包自己在稽核 Graphify 那輪就立下的原則：新增規則、skill 或工具的門檻是「同類失敗反覆發生且有具體證據」，「之後可能會用到」不構成理由。`funnel` 這個案例已經反覆發生，且有三次明確紀錄，達到門檻，所以這輪把它變成 `core/skills/zh-lint/` 這個機械檢查，不再只靠自我提醒。

## 範圍刻意窄

`wordlist.json` 只收這個包實際犯過的詞，不是預先列一份完整的英文技術詞黑名單。列出太廣的字典會抓到 `run`／`commit`／`API`／`hook` 這類這包刻意保留原文的通行技術詞，變成每次都要人工篩掉一堆噪音，跑起來比不跑還煩——這正是這包在稽核別的功能時反覆強調的「context 過度預載」問題，套用在自己身上一樣成立。

`budget` 這個詞本身就示範了為什麼要窄：它同時是散文裡該翻的「算力預算」，也是這包自訂的原則名稱「Context Budget」的一部分。字典法沒辦法一次分辨兩種用法，加了一條排除「`Context Budget` 這個片語裡的 `budget` 不算」的邏輯，而不是乾脆把 `budget`整個從字典拿掉——拿掉會漏掉真違規，這條折衷是實測（見這輪 commit 的驗證紀錄）跑出來的，不是憑空猜的。

## 已知邊界，寫進 SKILL.md 不是藏起來

- 只處理 Markdown（frontmatter／fenced code／inline code 排除邏輯是照 Markdown 語法寫的），拿去掃 `.py`／`.json` 會把程式碼裡的字串常數跟註解一起抓進來，這支腳本自己的原始碼就示範過這個誤判。
- 不掃 vendored skill 本體、`issue-tracker.md` 這類延伸 vendored 生態系的檔案（本來就該是英文）、`.memsearch/` 底下 memsearch 自己產生的逐字稿（不是這包手寫的內容，改了也會被蓋掉）。

## Consequences

- 這是提醒用的 lint，不是 CI gate——這包沒有 CI，跑不跑由使用的人自己判斷，符合「optional 工具不做成 mandatory lifecycle」。
- 白名單會隨著真的抓到新違規而長大，不會一次寫完整；這也是這份 ADR 本身要示範的事——先有具體證據，才擴充規則，不要反過來。
