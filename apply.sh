#!/usr/bin/env bash
# 把隨身包套進目標資料夾。固定多步驟流程：
#   git init → skills 投影 → .claude/ 設定 → 規範文件 → tracker 設定 → 授權 → .gitignore
# 已存在的檔案一律跳過，不覆寫、不刪除。
set -euo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "用法: $(basename "$0") <目標資料夾> [--dry-run]"
  echo "  --dry-run  只印出會做什麼，不實際動作"
  exit 1
}

[[ $# -ge 1 ]] || usage
TARGET="$1"; shift
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

[[ "$(cd "$TARGET" 2>/dev/null && pwd || echo "")" != "$PACK" ]] || {
  echo "錯誤：目標不能是隨身包自己"; exit 1; }

run() { if (( DRY )); then echo "  [dry-run] $*"; else "$@"; fi; }

# 逐檔複製一棵樹，已存在者跳過
copy_tree() {
  local src="$1" dstroot="$2" label="$3"
  echo "複製 $label"
  while IFS= read -r rel; do
    local dst="$dstroot/$rel"
    if [[ -e "$dst" ]]; then
      echo "  跳過（已存在）：$label$rel"
    else
      echo "  複製：$label$rel"
      run mkdir -p "$(dirname "$dst")"
      run cp "$src/$rel" "$dst"
    fi
  done < <(cd "$src" && find . -type f ! -name 'settings.local.json' -printf '%P\n' | sort)
}

# 1. 目標資料夾
if [[ -d "$TARGET" ]]; then
  echo "目標已存在：$TARGET"
  if [[ -n "$(ls -A "$TARGET" 2>/dev/null)" ]]; then
    echo "  內容不為空，既有檔案不會被覆寫："
    ls -A "$TARGET" | sed 's/^/    /'
  fi
else
  echo "建立目標資料夾：$TARGET"
  run mkdir -p "$TARGET"
fi
(( DRY )) || TARGET="$(cd "$TARGET" && pwd)"

# 2. git init
if [[ -d "$TARGET/.git" ]]; then
  echo "跳過 git init（已是 repo）"
else
  echo "git init"
  run git -C "$TARGET" init -q
fi

# 3. skills：真實檔案落在 .agents/skills/，Codex 直接掃這裡
copy_tree "$PACK/skills" "$TARGET/.agents/skills" ".agents/skills/"

# 4. Claude 讀 .claude/skills，指向同一份，不做第二次複製
if [[ -e "$TARGET/.claude/skills" ]]; then
  echo "跳過（已存在）：.claude/skills"
else
  echo "連結：.claude/skills -> ../.agents/skills"
  run mkdir -p "$TARGET/.claude"
  run ln -s ../.agents/skills "$TARGET/.claude/skills"
fi

# 5. .claude/ 其餘內容。.claude/skills 在包內是 symlink，find -type f 不會下探，故不重複
copy_tree "$PACK/.claude" "$TARGET/.claude" ".claude/"

# 6. 規範文件
for f in AGENTS.md CLAUDE.md; do
  if [[ -e "$TARGET/$f" ]]; then
    echo "跳過（已存在）：$f"
  else
    echo "複製：$f"
    run cp "$PACK/$f" "$TARGET/$f"
  fi
done

# 7. tracker 與 domain 設定：vendored skill 讀這兩個檔，取代上游的 per-repo setup 步驟
copy_tree "$PACK/.claude/templates/agents" "$TARGET/docs/agents" "docs/agents/"

# 8. 授權：vendored skill 為 MIT，需隨行
copy_tree "$PACK/LICENSES" "$TARGET/LICENSES" "LICENSES/"

# 9. .gitignore
if [[ -e "$TARGET/.gitignore" ]]; then
  echo "跳過（已存在）：.gitignore"
else
  echo "複製：.gitignore"
  run cp "$PACK/.claude/templates/gitignore.base" "$TARGET/.gitignore"
fi

# 10. Runtime 檢查。只回報，不安裝、不修改使用者層設定。
echo
echo "外部 runtime（機器層依賴，不隨這包攜帶）："
need() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "  有   $1"
  else
    echo "  缺   $1 — $2"
  fi
}
need gh "issue 流程需要它：https://cli.github.com"
need uv "https://docs.astral.sh/uv"
need memsearch '跨 session 記憶需要它：uv tool install "memsearch[onnx]"'

if command -v memsearch >/dev/null 2>&1; then
  provider=$(memsearch config get embedding.provider 2>/dev/null | tr -d '[:space:]')
  if [[ "$provider" != "onnx" && "$provider" != "ollama" ]]; then
    echo "  注意 memsearch embedding provider 是 '${provider:-未設定}'，需要 API key"
    echo "       要用本機模型：memsearch config set embedding.provider onnx"
  fi
fi

echo
echo "對話擷取需要各 agent 的官方整合，各機器裝一次，本腳本不代勞："
echo "  Claude Code  /plugin marketplace add zilliztech/memsearch-plugins"
echo "               /plugin install memsearch"
echo "  Codex        bash <memsearch repo>/plugins/codex/scripts/install.sh"

echo
echo "完成。下一步：在 $TARGET 開 Claude Code，跑 /kickoff 完成 GitHub 與標籤設定。"
echo "（尚未 commit —— 依 AGENTS.md，commit 需明確指示。）"
