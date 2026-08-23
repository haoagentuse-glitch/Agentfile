#!/usr/bin/env bash
# 把隨身包套進目標資料夾。固定多步驟流程：
#   git init → skills/tools 投影 → .claude/ 設定（core+profile 合併）
#   → 規範文件（core+profile 串接）→ tracker 設定 → records → 授權 → .gitignore
# 可重複執行。每次投影都記錄內容雜湊到 .agentfile/manifest.tsv：
#   下游沒動過的檔 → 直接更新；下游改過的檔 → 不動並回報。詳見 docs/adr/0014。
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

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ---------------------------------------------------------------- 投影紀錄
# manifest 每行四欄：<sha256> <bytes> <mode> <目標相對路徑>
#   full   雜湊涵蓋整個檔，長度必須完全相符
#   prefix 雜湊只涵蓋前 bytes 位元組（core+profile 組裝段），其後屬下游
MANIFEST_REL=".agentfile/manifest.tsv"
declare -A MF_HASH MF_BYTES MF_MODE MF_SEEN
NEW_MANIFEST="$WORK/manifest.new"
: > "$NEW_MANIFEST"
N_NEW=0; N_UPDATED=0
CONFLICTS=(); UNKNOWN=(); ORPHANS=()

load_manifest() {
  local f="$TARGET/$MANIFEST_REL" h b m p
  [[ -f "$f" ]] || return 0
  while IFS=$'\t' read -r h b m p; do
    [[ -n "${p:-}" ]] || continue
    MF_HASH["$p"]="$h"; MF_BYTES["$p"]="$b"; MF_MODE["$p"]="$m"
  done < "$f"
}

hash_file() { sha256sum < "$1" | cut -d' ' -f1; }
hash_prefix() { head -c "$2" -- "$1" | sha256sum | cut -d' ' -f1; }
file_bytes() { wc -c < "$1" | tr -d '[:space:]'; }

record() {
  printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> "$NEW_MANIFEST"
  MF_SEEN["$4"]=1
}

write_file() {
  (( DRY )) && return 0
  mkdir -p "$(dirname "$2")"
  cp "$1" "$2"
}

# install_full <組裝好的來源內容檔> <目標相對路徑> <來源說明>
install_full() {
  local srcfile="$1" rel="$2" origin="$3"
  local dst="$TARGET/$rel" src_hash src_bytes dst_hash rec
  src_hash="$(hash_file "$srcfile")"; src_bytes="$(file_bytes "$srcfile")"

  if [[ ! -e "$dst" ]]; then
    echo "  新增：$rel"
    write_file "$srcfile" "$dst"
    record "$src_hash" "$src_bytes" full "$rel"
    N_NEW=$((N_NEW + 1))
    return 0
  fi

  dst_hash="$(hash_file "$dst")"
  rec="${MF_HASH[$rel]:-}"

  if [[ -z "$rec" ]]; then
    if [[ "$dst_hash" == "$src_hash" ]]; then
      record "$src_hash" "$src_bytes" full "$rel"   # backfill，內容一致，靜默納管
    else
      UNKNOWN+=("$rel ← $origin")
    fi
    return 0
  fi

  if [[ "$dst_hash" == "$rec" ]]; then
    if [[ "$src_hash" != "$rec" ]]; then
      echo "  更新：$rel"
      write_file "$srcfile" "$dst"
      N_UPDATED=$((N_UPDATED + 1))
    fi
    record "$src_hash" "$src_bytes" full "$rel"
  elif [[ "$dst_hash" == "$src_hash" ]]; then
    # 下游已經自己改成跟上游一模一樣（例如上一輪手動採納了衝突）。沒有東西要決定，
    # 只把 manifest 對齊；繼續報成衝突會讓真正需要人看的那幾筆被雜訊蓋掉。
    record "$src_hash" "$src_bytes" full "$rel"
  else
    [[ "$src_hash" == "$rec" ]] || CONFLICTS+=("$rel ← $origin")
    record "$rec" "${MF_BYTES[$rel]}" "${MF_MODE[$rel]}" "$rel"
  fi
}

# install_prefix <組裝好的前綴內容檔> <目標相對路徑> <來源說明>
# 目標檔前綴以外的內容屬下游（AGENTS.md 的專案特化章節、.gitignore 的專案規則），更新時原封保留。
install_prefix() {
  local srcfile="$1" rel="$2" origin="$3"
  local dst="$TARGET/$rel" src_hash src_bytes dst_bytes rec rec_bytes dst_prefix=""
  src_hash="$(hash_file "$srcfile")"; src_bytes="$(file_bytes "$srcfile")"

  if [[ ! -e "$dst" ]]; then
    echo "  新增：$rel"
    write_file "$srcfile" "$dst"
    record "$src_hash" "$src_bytes" prefix "$rel"
    N_NEW=$((N_NEW + 1))
    return 0
  fi

  dst_bytes="$(file_bytes "$dst")"
  rec="${MF_HASH[$rel]:-}"

  if [[ -z "$rec" ]]; then
    if (( dst_bytes >= src_bytes )) && [[ "$(hash_prefix "$dst" "$src_bytes")" == "$src_hash" ]]; then
      record "$src_hash" "$src_bytes" prefix "$rel"  # backfill：目標以當前來源為前綴
    else
      UNKNOWN+=("$rel ← $origin")
    fi
    return 0
  fi

  rec_bytes="${MF_BYTES[$rel]}"
  (( dst_bytes >= rec_bytes )) && dst_prefix="$(hash_prefix "$dst" "$rec_bytes")"

  if [[ "$dst_prefix" == "$rec" ]]; then
    if [[ "$src_hash" != "$rec" ]]; then
      echo "  更新：$rel（保留專案特化段）"
      if ! (( DRY )); then
        cat "$srcfile" > "$WORK/merged"
        tail -c "+$((rec_bytes + 1))" -- "$dst" >> "$WORK/merged"
        cat "$WORK/merged" > "$dst"
      fi
      N_UPDATED=$((N_UPDATED + 1))
    fi
    record "$src_hash" "$src_bytes" prefix "$rel"
  else
    [[ "$src_hash" == "$rec" ]] || CONFLICTS+=("$rel ← $origin")
    record "$rec" "$rec_bytes" prefix "$rel"
  fi
}

# 逐檔投影一棵樹；可對同一個 dstrel 呼叫多次做聯集（core 一次、profile 一次）
copy_tree() {
  local src="$1" dstrel="$2" packrel="$3" rel
  [[ -d "$src" ]] || return 0
  while IFS= read -r rel; do
    install_full "$src/$rel" "$dstrel/$rel" "$packrel/$rel"
  done < <(cd "$src" && find . -type f ! -path '*/.venv/*' ! -path '*/.pytest_cache/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name 'settings.local.json' ! -name 'settings.json' ! -name 'gitignore.base' -printf '%P\n' | sort)
}

# 串接 core 與 profile 兩個文字檔到暫存，再以 prefix 模式投影
concat_into() {
  local core_src="$1" profile_src="$2" out="$3"
  cat "$core_src" > "$out"
  if [[ -f "$profile_src" ]]; then
    echo "" >> "$out"
    cat "$profile_src" >> "$out"
  fi
}

pack_revision() {
  local rev
  rev="$(git -C "$PACK" rev-parse --verify HEAD 2>/dev/null || true)"
  [[ -n "$rev" ]] || { echo "無法取得"; return 0; }
  [[ -z "$(git -C "$PACK" status --porcelain 2>/dev/null)" ]] || rev="$rev-dirty"
  echo "$rev"
}

# 只取 owner/name，不寫本機絕對路徑
pack_repo_slug() {
  local url
  url="$(git -C "$PACK" remote get-url origin 2>/dev/null || true)"
  [[ -n "$url" ]] || return 0
  url="${url%.git}"
  case "$url" in
    *://*) echo "$url" | sed -E 's#^[a-z+]+://([^@/]+@)?[^/]+/##' ;;
    *:*)   echo "${url##*:}" ;;
  esac
}

# ---------------------------------------------------------------- 1. 目標資料夾
if [[ -d "$TARGET" ]]; then
  echo "目標已存在：$TARGET"
else
  echo "建立目標資料夾：$TARGET"
  (( DRY )) || mkdir -p "$TARGET"
fi
(( DRY )) || TARGET="$(cd "$TARGET" && pwd)"

echo "啟用 profile：$PROFILE"
load_manifest

if [[ -d "$TARGET/.git" && -n "$(git -C "$TARGET" status --porcelain 2>/dev/null)" ]]; then
  echo "注意：目標工作區有未提交的變更，更新會疊在上面（可用 git diff 回溯）"
fi

# ---------------------------------------------------------------- 2. git init
if [[ -d "$TARGET/.git" ]]; then
  echo "跳過 git init（已是 repo）"
else
  echo "git init"
  (( DRY )) || git -C "$TARGET" init -q
fi

# ---------------------------------------------------------------- 3. skills / tools
# 真實檔案落在 .agents/skills/，Codex 直接掃這裡
copy_tree "$PACK/core/skills" ".agents/skills" "core/skills"
copy_tree "$PACK/profiles/$PROFILE/skills" ".agents/skills" "profiles/$PROFILE/skills"
# 確定性工具與 skill 分離。只有 active profile 的工具會被投射。
copy_tree "$PACK/profiles/$PROFILE/tools" ".agents/tools" "profiles/$PROFILE/tools"

# ---------------------------------------------------------------- 4. .claude/skills symlink
# Claude 讀 .claude/skills，指向同一份，不做第二次複製；symlink 不納入 manifest
if [[ -e "$TARGET/.claude/skills" ]]; then
  echo "跳過（已存在）：.claude/skills"
else
  echo "連結：.claude/skills -> ../.agents/skills"
  if ! (( DRY )); then
    mkdir -p "$TARGET/.claude"
    ln -s ../.agents/skills "$TARGET/.claude/skills"
  fi
fi

# ---------------------------------------------------------------- 5. .claude/ 其餘內容
# .claude/skills 在包內是 symlink，find -type f 不會下探，故不重複
copy_tree "$PACK/core/.claude" ".claude" "core/.claude"
copy_tree "$PACK/profiles/$PROFILE/.claude" ".claude" "profiles/$PROFILE/.claude"

# settings.json 不是檔案複製，是內容合併（core 的允許清單 + profile 的允許清單）。
# 下游要加自己的權限請寫 .claude/settings.local.json，不要改這個檔。
PROFILE_SETTINGS="$PACK/profiles/$PROFILE/.claude/settings.json"
if [[ -f "$PROFILE_SETTINGS" ]]; then
  jq -s '.[0].permissions.allow += .[1].permissions.allow | .[0].permissions.deny += (.[1].permissions.deny // []) | .[0]' \
    "$PACK/core/.claude/settings.json" "$PROFILE_SETTINGS" > "$WORK/settings.json"
  install_full "$WORK/settings.json" ".claude/settings.json" "core/.claude/settings.json + profiles/$PROFILE/.claude/settings.json"
else
  install_full "$PACK/core/.claude/settings.json" ".claude/settings.json" "core/.claude/settings.json"
fi

# ---------------------------------------------------------------- 6. 規範文件
# AGENTS.md 由 core + profile 串接組裝，專案特化章節追加於末尾，更新時保留
concat_into "$PACK/core/AGENTS.md" "$PACK/profiles/$PROFILE/AGENTS.md" "$WORK/AGENTS.md"
install_prefix "$WORK/AGENTS.md" "AGENTS.md" "core/AGENTS.md + profiles/$PROFILE/AGENTS.md"
install_full "$PACK/CLAUDE.md" "CLAUDE.md" "CLAUDE.md"

# ---------------------------------------------------------------- 7. tracker 設定與 records
# vendored skill 讀 docs/agents/，取代上游的 per-repo setup 步驟（profile 無關，core 擁有）
copy_tree "$PACK/core/.claude/templates/agents" "docs/agents" "core/.claude/templates/agents"
# profile 擁有的 canonical schema。definitions/runs 這類使用者產生的內容不預建。
copy_tree "$PACK/profiles/$PROFILE/records" "records" "profiles/$PROFILE/records"

# ---------------------------------------------------------------- 8. 第三方授權
install_full "$PACK/docs/THIRD_PARTY_LICENSES.md" "docs/THIRD_PARTY_LICENSES.md" "docs/THIRD_PARTY_LICENSES.md"

# ---------------------------------------------------------------- 9. .gitignore
concat_into "$PACK/core/.claude/templates/gitignore.base" "$PACK/profiles/$PROFILE/.claude/templates/gitignore.base" "$WORK/gitignore"
install_prefix "$WORK/gitignore" ".gitignore" "core/.claude/templates/gitignore.base + profiles/$PROFILE/.claude/templates/gitignore.base"

# ---------------------------------------------------------------- 10. 落地投影紀錄
for rel in "${!MF_HASH[@]}"; do
  [[ -n "${MF_SEEN[$rel]:-}" ]] || ORPHANS+=("$rel")
done

REV="$(pack_revision)"
SLUG="$(pack_repo_slug)"
if ! (( DRY )); then
  mkdir -p "$TARGET/.agentfile"
  sort -t$'\t' -k4 "$NEW_MANIFEST" > "$TARGET/$MANIFEST_REL"
  jq -n --arg repo "$SLUG" --arg rev "$REV" --arg profile "$PROFILE" \
        --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '(if $repo == "" then {} else {agentfile_repo: $repo} end)
     + {agentfile_revision: $rev, profile: $profile, applied_at: $at}' \
    > "$TARGET/.agentfile/source.json"
fi

# ---------------------------------------------------------------- 11. 摘要
echo
echo "摘要"
echo "  來源    ${SLUG:-（無 remote）} @ $REV"
echo "  profile $PROFILE"
echo "  目標    $TARGET"
echo "  結果    新增 $N_NEW／更新 $N_UPDATED／衝突 ${#CONFLICTS[@]}／不明來歷 ${#UNKNOWN[@]}／上游已移除 ${#ORPHANS[@]}"

if (( ${#CONFLICTS[@]} )); then
  echo
  echo "衝突（下游與上游都改過，未動目標檔，請手動比對後覆蓋）："
  printf '  %s\n' "${CONFLICTS[@]}"
fi
if (( ${#UNKNOWN[@]} )); then
  echo
  echo "不明來歷（無投影紀錄且內容與上游不同，未動目標檔，手動處理一次後即自動納管）："
  printf '  %s\n' "${UNKNOWN[@]}"
fi
if (( ${#CONFLICTS[@]} || ${#UNKNOWN[@]} )); then
  echo
  echo "  比對方式：diff $PACK/<來源> $TARGET/<路徑>"
fi
if (( ${#ORPHANS[@]} )); then
  echo
  echo "上游已移除（未自動刪除，確認後手動處理）："
  printf '  %s\n' "${ORPHANS[@]}"
  echo "  一次刪除：（cd $TARGET && rm -f $(printf '%q ' "${ORPHANS[@]}"))"
fi

# ---------------------------------------------------------------- 12. Runtime 檢查
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
if (( DRY )); then
  echo "以上為 --dry-run 預覽，未寫入任何檔案。"
else
  echo "完成（profile：$PROFILE）。下一步：在 $TARGET 開 Claude Code，跑 /kickoff 完成 GitHub 與標籤設定。"
  echo "（尚未 commit——這支腳本本身不 commit；後續改動依 AGENTS.md 會自動 commit，不用手動先 commit。）"
fi
