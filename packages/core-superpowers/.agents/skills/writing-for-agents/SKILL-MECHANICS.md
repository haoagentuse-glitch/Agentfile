# Skill 機制

[`writing-for-agents`](SKILL.md) 裡專屬 skill 的那個分支：文件是一份 skill 時有什麼不同——frontmatter、叫用方式的選擇，以及 router skill。其餘寫法都在 `SKILL.md` 的通用參考裡。

## 叫用方式

兩種選擇，交換的是那兩種負載：

- **模型叫用**的 skill 保留 `description`，所以 agent 可以自己觸發它——其他 skill 也拿得到它。你照樣可以打它的名字：模型叫用一律**包含**使用者這條路；description 只會多出 agent 的發現能力，永遠不會拿掉人的。description 是這個 skill 最上層的脈絡指標，被迫永遠載入——用永久的脈絡負載換可被發現。內容全是參考的模型叫用 skill 也是共用參考的一種安置處：另一個 skill 可以叫用它，於是好幾個 skill 都需要的參考只存在一個地方。做法：不要寫 `disable-model-invocation`，並寫一份給模型看、帶著觸發分支的 description（`SKILL.md` 的指標撰寫規則全部適用）。
- **使用者叫用**的 skill 把 description 從 agent 的視野裡拿掉：只有人打它的名字才叫得動，其他 skill 都叫不到。脈絡負載為零，但它花的是認知負載——你就是那個必須記得它存在的索引。做法：設 `disable-model-invocation: true`；`description` 變成給人看的——一行摘要，觸發語清單拿掉。

只有在 agent 必須自己拿到這個 skill、或另一個 skill 必須拿到它時，才選模型叫用。如果它永遠只靠手動觸發，就設成使用者叫用，一分脈絡負載都不必付。

兩個使用者叫用的 skill 都需要的共用參考，放在兩者之中都不對——它們都沒有 description，誰也觸發不了誰。把它推到 skill 系統外的一個普通檔案：任何 skill 都能指過去的外部參考。

## 依叫用方式切開

切開的另一刀是依叫用方式（依序列那一刀在 `SKILL.md`）：當你有一個明確的帶頭詞應該獨立觸發它——一個你在 prompt 裡真的會用的觸發詞——或另一個 skill 必須拿到它時，就切出一個模型叫用的 skill。你要為新的、永遠載入的 description 付脈絡負載，所以那份獨立的可及性必須值得。

## Router skill

使用者叫用的 skill 多到你記不住時，那堆積起來的認知負載用一個 **router skill** 解：一個使用者叫用的 skill，列出其他那些以及什麼時候該找哪一個，於是人只要記得一個 skill，不必記一堆。它只能提示，永遠觸發不了它們：使用者叫用的 skill 沒有 description，除了人以外沒有東西拿得到它們。
