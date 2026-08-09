# 跨 session 記憶預設不進版控

ADR 0001 把 `.memsearch/memory/*.md` 定為「可攜 SSoT，跟著 repo 進版控」。這假設每個套用這包的專案都適合把對話記憶公開跟著 repo 走，但 `apply.sh` 套到任意目標專案時事先不知道那個 repo 是 public 還是 private，也不該為了問一次「這個 repo 會 public 嗎」而打斷套用流程——這包的定位是自包含、不需要額外互動設定。

改為預設 `.memsearch/` 整個目錄不進版控，視為機器層本機資料。需要記憶跨機器、跨 clone 帶著走時，使用者自己在該專案的 `.gitignore` 手動加回 `!.memsearch/memory/*.md`——一次性、明確的選擇，而非套用時的預設值。

## Consequences

- 多數專案的對話記憶留在本機，不會因為套用這包就預設把記憶內容推上可能是 public 的 repo。
- 真的需要記憶跟著 repo 走的人，機制沒被拿掉，只是不再是預設，改成手動選擇。
- ADR 0001 其餘結論（機器層／專案層分工、`apply.sh` 不碰使用者層外掛設定）不受影響，只有「預設追蹤 `memory/*.md`」這條被取代。
