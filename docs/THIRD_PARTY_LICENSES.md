# 第三方授權

本專案包含下列第三方內容。MIT 全文附於本頁。Apache-2.0 全文見 [packages/core-superpowers/docs/licenses/APACHE-2.0.txt](../packages/core-superpowers/docs/licenses/APACHE-2.0.txt)。

| 來源 | 內容 | 固定版本 | 授權與 Copyright |
|---|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | core 工作流 | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`（v6.3.0） | MIT；Copyright (c) 2025 Jesse Vincent |
| [fcakyon/phd-skills](https://github.com/fcakyon/phd-skills) | 研究技能 | 各技能 frontmatter 所列 commit | MIT；Copyright (c) 2026 Fatih Cagatay Akyon |
| [mattpocock/skills](https://github.com/mattpocock/skills) | Agent 寫作與設計技能 | 各技能 frontmatter 所列 commit | MIT；Copyright (c) 2026 Matt Pocock |
| [streamlit/streamlit](https://github.com/streamlit/streamlit) | `developing-with-streamlit` | `4a57917ccc0c339c00a7026d1f8370bcd68f8ed3` | Apache-2.0 |
| [Paldom/streamlit-custom-style](https://github.com/Paldom/streamlit-custom-style) | `streamlit-custom-style` | `4a95a35bce6b3d17d6b6ee30c054af5678ac3126` | MIT；Copyright (c) 2026 Paldom |
| [21st-dev/skill](https://github.com/21st-dev/skill) | 7 個 `21st-*` 技能 | `0d77001a77fe8540bb07ed68d09092ee08546ed3` | Apache-2.0；Copyright 2026 21st.dev |
| [starc007/ui-components](https://github.com/starc007/ui-components) | `beui` | `10c283e433a8f4f0ac0736684d4426ab612b9f55` | MIT；Copyright (c) 2026 Saurabh Chauhan |
| [greensock/gsap-skills](https://github.com/greensock/gsap-skills) | 8 個 `gsap-*` Agent Skills | `aed9cfd3277740755f6bfc1155c7aa645403b760` | MIT；Copyright (c) 2026 GreenSock |
| [twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill) | `swiftui-pro` 1.1 | `be297ff80dddec529af1f9b1f1f114aab6c9d11c` | MIT；Copyright (c) 2026 Paul Hudson |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | 10 個設計、動效與 Swift 技能 | `d23d7f88a2e21c9e4b1418c7abe420f5c1052ba7` | MIT；Copyright (c) 2026 Emil Kowalski |
| [Appllama/appllama-skills](https://github.com/Appllama/appllama-skills) | `appllama-usage` | `629818a094844bd383cbcc336e6bc1d953fc193f` | MIT；Copyright (c) 2026 Antmind Ventures Private Limited |
| [Nutlope/hallmark](https://github.com/Nutlope/hallmark) | `hallmark` | `13ac0ec7e148655948100b6396439e481361d690` | MIT；Copyright (c) 2026 Hallmark contributors |
| [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | `design-taste-frontend` | `ccbc15639c97057cbfcf32ecebc38ef716e4bb37` | MIT；Copyright (c) 2026 Leonxlnx |

## Vendor 調整

- `21st-ai`：移除 description 內的角括號 placeholder，並在該檔 metadata 記錄修改。
- `21st-ui-*`：把 Codex default prompt 修正為實際的 `21st-ui-*` Skill 名稱。
- `review-animations`、`pick-ui-library`：把不支援的 `disable-model-invocation` 轉成 Codex `agents/openai.yaml` policy。
- `hallmark`：把頂層 `version` 移到 `metadata.version`。
- `swiftui-pro`：只發行 1.1 Skill。排除上游套件內嵌的 1.0 相容副本與指向該副本的 plugin manifest。
- 上游 Markdown：正規化行尾空白與檔尾空行，以通過本專案的 diff gate；不改變語意。

## MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
