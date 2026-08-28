# claim-writer@1

把一次比較的結果，寫成一個可稽核的候選研究主張。

輸出型別：`prompt-output.schema.json#/$defs/claimWriterOutput`

## 輸入

凍結的 Experiment Contract、比較結果，以及相關的 run 紀錄。

## 你要做的事

1. 寫一句只講一個可驗證命題的 `statement`。
2. 選 `claim_type`。
3. 寫 `scope`：這個結論適用到哪裡為止——哪個資料集、哪個評估集、哪些模型與版本、幾次執行。
4. 填 `evidence_refs`，每一筆盡量帶 `locator` 指到具體欄位。
5. 列出你想得到的替代解釋（`alternative_explanations`）。

## 硬規則

`statement` 一次只說一個命題。「A 提升了 X 而且 B 也變好」是兩個主張，分開寫。

數字要跟證據對得上。`stated_magnitude` 必須能在引用的比較結果裡找到同一個值。

`scope` 寧可寫窄。寫窄了稽核會判 `fully_supported`；寫寬了會判 `overreaching`。

引用的比較結果如果 `comparison_valid` 是 `false`，不要寫因果類型的主張。條件沒守住或沒有共同基準時，數字不能拿來歸因。

複現次數不足時，據實寫進 `scope`，不要略過。

`status` 固定 `candidate`。是否成立由稽核決定，不由你決定。

`evidence_refs` 不得為空。沒有引用的結論不是主張，是意見。
