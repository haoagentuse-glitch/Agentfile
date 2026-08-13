#!/usr/bin/env bash
# 把隨身包套進目標資料夾。固定多步驟流程：
#   git init → skills/tools 投影 → .claude/ 設定（core+profile 合併）
#   → 規範文件（core+profile 串接）→ tracker 設定 → records → 授權 → .gitignore
# 已存在的檔案一律跳過，不覆寫、不刪除。
set -euo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "用法: $(basename "$0") <目標資料夾> [--profile software|experimental] [--dry-run]"
  echo "  --profile  啟用哪個 profile，預設 software"
  echo "  --dry-run  只印出會做什麼，不實際動作"
  exit 1
}

[[ $# -ge 1 ]] || usage
TARGET="$1"; shift
DRY=0
PROFILE="software"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --profile) PROFILE="${2:?--profile 需要值}"; shift 2 ;;
    *) usage ;;
  esac
done

[[ "$PROFILE" == "software" || "$PROFILE" == "experimental" ]] || {
  echo "錯誤：--profile 只接受 software 或 experimental，收到 '$PROFILE'"; exit 1; }

[[ -d "$PACK/profiles/$PROFILE" ]] || {
  echo "錯誤：profiles/$PROFILE 尚未建立（experimental profile 還在 walking skeleton 階段）"; exit 1; }

[[ "$(cd "$TARGET" 2>/dev/null && pwd || echo "")" != "$PACK" ]] || {
  echo "錯誤：目標不能是隨身包自己"; exit 1; }

run() { if (( DRY )); then echo "  [dry-run] $*"; else "$@"; fi; }

# 逐檔複製一棵樹，已存在者跳過；可對同一個 dstroot 呼叫多次做聯集（core 一次、profile 一次）
copy_tree() {
  local src="$1" dstroot="$2" label="$3"
  [[ -d "$src" ]] || return 0
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
  done < <(cd "$src" && find . -type f ! -path '*/.venv/*' ! -path '*/.pytest_cache/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name 'settings.local.json' ! -name 'settings.json' ! -name 'gitignore.base' -printf '%P\n' | sort)
}

# 串接兩個文字檔（core 在前，profile 追加於末尾），已存在則跳過，不覆寫
concat_file() {
  local core_src="$1" profile_src="$2" dst="$3" label="$4"
  if [[ -e "$dst" ]]; then
    echo "跳過（已存在）：$label"
    return 0
  fi
  echo "組裝：$label（core"
  if [[ -f "$profile_src" ]]; then echo -n " + $PROFILE"; fi
  echo "）"
  if (( DRY )); then
    echo "  [dry-run] 串接 $core_src${profile_src:+ + $profile_src} -> $dst"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  cat "$core_src" > "$dst"
  if [[ -f "$profile_src" ]]; then
    echo "" >> "$dst"
    cat "$profile_src" >> "$dst"
  fi
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

echo "啟用 profile：$PROFILE"

# 2. git init
if [[ -d "$TARGET/.git" ]]; then
  echo "跳過 git init（已是 repo）"
else
  echo "git init"
  run git -C "$TARGET" init -q
fi

# 3. skills：core + profile 聯集，真實檔案落在 .agents/skills/，Codex 直接掃這裡
copy_tree "$PACK/core/skills" "$TARGET/.agents/skills" ".agents/skills/"
copy_tree "$PACK/profiles/$PROFILE/skills" "$TARGET/.agents/skills" ".agents/skills/"

# 3b. profile tools：確定性工具與 skill 分離。只有 active profile 的工具會被投射。
copy_tree "$PACK/profiles/$PROFILE/tools" "$TARGET/.agents/tools" ".agents/tools/"

# 4. Claude 讀 .claude/skills，指向同一份，不做第二次複製
if [[ -e "$TARGET/.claude/skills" ]]; then
  echo "跳過（已存在）：.claude/skills"
else
  echo "連結：.claude/skills -> ../.agents/skills"
  run mkdir -p "$TARGET/.claude"
  run ln -s ../.agents/skills "$TARGET/.claude/skills"
fi

# 5. .claude/ 其餘內容：core + profile 聯集。.claude/skills 在包內是 symlink，find -type f 不會下探，故不重複
copy_tree "$PACK/core/.claude" "$TARGET/.claude" ".claude/"
copy_tree "$PACK/profiles/$PROFILE/.claude" "$TARGET/.claude" ".claude/"

# 5b. settings.json 不是「先到先贏」的檔案複製，是內容合併（core 的允許清單 + profile 的允許清單）
if [[ -e "$TARGET/.claude/settings.json" ]]; then
  echo "跳過（已存在）：.claude/settings.json"
else
  echo "合併：.claude/settings.json（core + $PROFILE）"
  if (( DRY )); then
    echo "  [dry-run] jq 合併 core/.claude/settings.json + profiles/$PROFILE/.claude/settings.json"
  else
    run mkdir -p "$TARGET/.claude"
    profile_settings="$PACK/profiles/$PROFILE/.claude/settings.json"
    if [[ -f "$profile_settings" ]]; then
      jq -s '.[0].permissions.allow += .[1].permissions.allow | .[0].permissions.deny += (.[1].permissions.deny // []) | .[0]' \
        "$PACK/core/.claude/settings.json" "$profile_settings" > "$TARGET/.claude/settings.json"
    else
      cp "$PACK/core/.claude/settings.json" "$TARGET/.claude/settings.json"
    fi
  fi
fi

# 6. 規範文件：AGENTS.md 由 core + profile 串接組裝；CLAUDE.md 只有一份，直接複製
concat_file "$PACK/core/AGENTS.md" "$PACK/profiles/$PROFILE/AGENTS.md" "$TARGET/AGENTS.md" "AGENTS.md"
if [[ -e "$TARGET/CLAUDE.md" ]]; then
  echo "跳過（已存在）：CLAUDE.md"
else
  echo "複製：CLAUDE.md"
  run cp "$PACK/CLAUDE.md" "$TARGET/CLAUDE.md"
fi

# 7. tracker 設定：vendored skill 讀這個檔，取代上游的 per-repo setup 步驟（profile 無關，core 擁有）
copy_tree "$PACK/core/.claude/templates/agents" "$TARGET/docs/agents" "docs/agents/"

# 7b. records：profile 擁有的 canonical schema（例如 experimental 的 experiment schema）。
# definitions/runs 這類使用者產生的內容不預建，只投影 schema 這種本包自己 authored 的固定參照。
copy_tree "$PACK/profiles/$PROFILE/records" "$TARGET/records" "records/"

# 8. 第三方授權：單一文件隨專案交付。
if [[ -e "$TARGET/docs/THIRD_PARTY_LICENSES.md" ]]; then
  echo "跳過（已存在）：docs/THIRD_PARTY_LICENSES.md"
else
  echo "複製：docs/THIRD_PARTY_LICENSES.md"
  run mkdir -p "$TARGET/docs"
  run cp "$PACK/docs/THIRD_PARTY_LICENSES.md" "$TARGET/docs/THIRD_PARTY_LICENSES.md"
fi

# 9. .gitignore：core + profile 串接組裝
concat_file "$PACK/core/.claude/templates/gitignore.base" "$PACK/profiles/$PROFILE/.claude/templates/gitignore.base" "$TARGET/.gitignore" ".gitignore"

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
echo "完成（profile：$PROFILE）。下一步：在 $TARGET 開 Claude Code，跑 /kickoff 完成 GitHub 與標籤設定。"
echo "（尚未 commit——這支腳本本身不 commit；後續改動依 AGENTS.md 會自動 commit，不用手動先 commit。）"
