# AGENTS.md

這個專案使用 superpowers 技能包。技能檔為上游原文，未翻譯、未改寫。

## 開場必做

@.agents/skills/using-superpowers/SKILL.md

上面那行如果沒有被展開，就自己讀 `.agents/skills/using-superpowers/SKILL.md` 並照它做，再回應任何東西。那份檔案是整包的啟動器：它規定任何回應之前先查有沒有適用的技能。少了它，其餘 13 個技能不會被觸發。

## 技能命名對照

技能檔內部互相引用時寫成 `superpowers:<名稱>`，那是上游以外掛安裝時的命名空間。這一包是複製進專案的，技能以裸名稱定址。

```
技能檔裡寫的            這裡對應到
superpowers:brainstorming   →   brainstorming
superpowers:<任何名稱>       →   <任何名稱>
```

十四個 superpowers 技能都在 `.agents/skills/`。`agentfile build` 會建立內容相同的 `.claude/skills/` 實體副本。

## 這一包的邊界

- 技能檔逐字保留英文。上游明文要求不得在沒有 eval 證據的情況下改寫技能內容，翻譯會使試用結果無法歸因。
- 自然語言回應仍然用中文。
- 上游的 `AGENTS.md` 與 `CLAUDE.md` 是 superpowers repo 自己的貢獻者守則，講怎麼對它發 PR，不適用於這裡，沒有複製過來。
