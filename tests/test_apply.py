"""apply.sh 的投影與更新行為驗收。

每個測試都把這包複製一份到 tmp_path 當「上游」，再對另一個 tmp 目錄跑真的
apply.sh，不做 mock。改上游就是改那份複本，不動真的 repo。

判定表見 docs/adr/0014。
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[1]
PACK_PARTS = ("core", "profiles", "apply.sh", "CLAUDE.md")
IGNORE = shutil.ignore_patterns(
    ".venv", "__pycache__", "*.pyc", ".pytest_cache", "node_modules", ".git"
)

SKILL_REL = ".agents/skills/rule-check/SKILL.md"
SKILL_SRC = "core/skills/rule-check/SKILL.md"
KICKOFF_REL = ".claude/commands/kickoff.md"
KICKOFF_SRC = "core/.claude/commands/kickoff.md"


@pytest.fixture
def pack(tmp_path):
    """上游隨身包的可寫複本。沒有 .git，所以 revision 走「無法取得」分支。"""
    dst = tmp_path / "pack"
    dst.mkdir()
    for part in PACK_PARTS:
        src = PACK / part
        if src.is_dir():
            shutil.copytree(src, dst / part, ignore=IGNORE, symlinks=True)
        else:
            shutil.copy2(src, dst / part)
    (dst / "docs").mkdir()
    shutil.copy2(
        PACK / "docs/THIRD_PARTY_LICENSES.md", dst / "docs/THIRD_PARTY_LICENSES.md"
    )
    return dst


@pytest.fixture
def target(tmp_path):
    return tmp_path / "downstream"


def apply(pack, target, *args, profile="software"):
    result = subprocess.run(
        [str(pack / "apply.sh"), str(target), "--profile", profile, *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def manifest(target):
    """{目標相對路徑: (sha256, bytes, mode)}"""
    rows = {}
    text = (target / ".agentfile/manifest.tsv").read_text()
    for line in text.splitlines():
        h, size, mode, rel = line.split("\t")
        rows[rel] = (h, int(size), mode)
    return rows


def summary(stdout, field):
    """從摘要那行取一個計數，例如 summary(out, "更新")。"""
    line = next(ln for ln in stdout.splitlines() if ln.strip().startswith("結果"))
    for chunk in line.split("結果", 1)[1].split("／"):
        chunk = chunk.strip()
        if chunk.startswith(field):
            return int(chunk[len(field):])
    raise AssertionError(f"摘要沒有 {field}：{line}")


# --------------------------------------------------------------- provenance


def test_first_apply_writes_provenance(pack, target):
    apply(pack, target, profile="experimental")

    source = json.loads((target / ".agentfile/source.json").read_text())
    assert source["profile"] == "experimental"
    assert source["agentfile_revision"]
    assert source["applied_at"].endswith("Z")
    # 不得寫入本機絕對路徑
    assert str(pack) not in json.dumps(source)
    assert "agentfile_repo" not in source  # 複本沒有 git remote

    rows = manifest(target)
    assert rows["AGENTS.md"][2] == "prefix"
    assert rows[".gitignore"][2] == "prefix"
    assert rows[SKILL_REL][2] == "full"


def test_experimental_cli_survives_projection(pack, target):
    """確定性工具投影後仍只能由單一公開 CLI 執行。"""
    apply(pack, target, profile="experimental")
    tool = target / ".agents" / "tools" / "experiment-records"
    package = tool / "src" / "experiment_records"

    for module in ("compare_runs.py", "claim_audit.py", "compute_gate.py"):
        assert (package / module).is_file()
    for stale in (
        ".agents/skills/compare-runs/compare_runs.py",
        ".agents/skills/claim-audit/claim_audit.py",
        ".agents/skills/compute-gate/compute_gate.py",
    ):
        assert not (target / stale).exists()

    for command in ("compare-runs", "claim-audit", "compute-gate"):
        result = subprocess.run(
            [
                "uv", "run", "--offline", "--frozen", "--project", str(tool),
                "python", "-m", "experiment_records", command, "--help",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

def test_rerun_changes_nothing(pack, target):
    apply(pack, target)
    out = apply(pack, target)

    assert summary(out, "新增") == 0
    assert summary(out, "更新") == 0
    assert summary(out, "衝突") == 0
    assert summary(out, "不明來歷") == 0
    assert summary(out, "上游已移除") == 0


# --------------------------------------------------------------- 判定表


def test_upstream_fix_reaches_downstream(pack, target):
    """回歸：468dfde 修好的 kickoff.md 曾經因為「已存在」而傳不到下游。"""
    apply(pack, target)
    src = pack / KICKOFF_SRC
    src.write_text(src.read_text() + "\n上游修正。\n")

    out = apply(pack, target)

    assert "上游修正。" in (target / KICKOFF_REL).read_text()
    assert summary(out, "更新") == 1
    assert KICKOFF_REL in out


def test_downstream_edit_alone_is_silent(pack, target):
    apply(pack, target)
    dst = target / SKILL_REL
    dst.write_text(dst.read_text() + "\n本專案補充。\n")

    out = apply(pack, target)

    assert dst.read_text().endswith("本專案補充。\n")
    assert summary(out, "更新") == 0
    assert summary(out, "衝突") == 0
    assert SKILL_REL not in out


def test_both_sides_changed_is_conflict(pack, target):
    apply(pack, target)
    dst = target / SKILL_REL
    dst.write_text(dst.read_text() + "\n本專案補充。\n")
    src = pack / SKILL_SRC
    src.write_text(src.read_text() + "\n上游補充。\n")

    out = apply(pack, target)

    assert dst.read_text().endswith("本專案補充。\n")  # 未被覆寫
    assert "上游補充。" not in dst.read_text()
    assert summary(out, "衝突") == 1
    assert "衝突（" in out and SKILL_REL in out


def test_conflict_keeps_reporting_until_resolved(pack, target):
    apply(pack, target)
    dst = target / SKILL_REL
    dst.write_text(dst.read_text() + "\n本專案補充。\n")
    src = pack / SKILL_SRC
    src.write_text(src.read_text() + "\n上游補充。\n")

    apply(pack, target)
    out = apply(pack, target)

    assert summary(out, "衝突") == 1


def test_conflict_stops_reporting_once_downstream_matches_upstream(pack, target):
    """人工採納衝突之後就不該再報。兩邊已經一模一樣，沒有東西要決定。

    繼續報成衝突會讓真正需要人看的那幾筆被雜訊蓋掉——下游採納一次之後，
    每一次 apply 都會再看到同一批已解決的檔案。
    """
    apply(pack, target)
    dst = target / SKILL_REL
    dst.write_text(dst.read_text() + "\n本專案補充。\n")
    src = pack / SKILL_SRC
    src.write_text(src.read_text() + "\n上游補充。\n")
    apply(pack, target)

    # 人工採納：把上游那份原樣覆蓋過去。
    dst.write_text(src.read_text())
    out = apply(pack, target)

    assert summary(out, "衝突") == 0
    assert SKILL_REL not in out
    assert dst.read_text() == src.read_text()

    # 採納之後 manifest 已對齊，下一次上游再改就回到正常的更新路徑。
    src.write_text(src.read_text() + "\n上游再改一次。\n")
    out = apply(pack, target)

    assert summary(out, "更新") == 1
    assert dst.read_text().endswith("上游再改一次。\n")


# --------------------------------------------------------------- prefix 模式


def test_agents_md_keeps_project_section_while_upstream_updates(pack, target):
    apply(pack, target)
    tail = "\n## 本專案特化\n\n只有這個專案適用的規則。\n"
    agents = target / "AGENTS.md"
    agents.write_text(agents.read_text() + tail)

    core = pack / "core/AGENTS.md"
    core.write_text(core.read_text().replace("## 核心原則", "## 核心原則（已更新）", 1))
    out = apply(pack, target)

    text = agents.read_text()
    assert "## 核心原則（已更新）" in text  # 上游條文換新
    assert text.endswith(tail)  # 專案特化段原封保留
    assert summary(out, "更新") == 1
    assert summary(out, "衝突") == 0


def test_editing_upstream_section_downstream_is_conflict(pack, target):
    """改的是受管前綴本身，不是追加段——這種沒有機制能自動合併。"""
    apply(pack, target)
    agents = target / "AGENTS.md"
    agents.write_text(agents.read_text().replace("## 核心原則", "## 我自己改的標題", 1))

    core = pack / "core/AGENTS.md"
    core.write_text(core.read_text() + "\n上游新規則。\n")
    out = apply(pack, target)

    assert "上游新規則。" not in agents.read_text()
    assert summary(out, "衝突") == 1


# --------------------------------------------------------------- backfill


def test_backfill_adopts_identical_files(pack, target):
    """既有專案沒有 manifest：內容與上游相同的檔應靜默納管，不需旗標。"""
    apply(pack, target)
    (target / ".agentfile/manifest.tsv").unlink()

    out = apply(pack, target)
    assert summary(out, "不明來歷") == 0
    assert SKILL_REL in manifest(target)

    # 納管後，上游更新就能套用
    src = pack / SKILL_SRC
    src.write_text(src.read_text() + "\n上游補充。\n")
    apply(pack, target)
    assert "上游補充。" in (target / SKILL_REL).read_text()


def test_backfill_adopts_agents_md_with_project_section(pack, target):
    apply(pack, target)
    tail = "\n## 本專案特化\n\n只有這個專案適用的規則。\n"
    agents = target / "AGENTS.md"
    agents.write_text(agents.read_text() + tail)
    (target / ".agentfile/manifest.tsv").unlink()

    out = apply(pack, target)

    assert summary(out, "不明來歷") == 0
    assert manifest(target)["AGENTS.md"][2] == "prefix"
    assert agents.read_text().endswith(tail)


def test_backfill_reports_diverged_file_as_unknown(pack, target):
    apply(pack, target)
    dst = target / SKILL_REL
    dst.write_text(dst.read_text() + "\n本專案補充。\n")
    (target / ".agentfile/manifest.tsv").unlink()

    out = apply(pack, target)

    assert summary(out, "不明來歷") == 1
    assert "不明來歷（" in out and SKILL_REL in out
    assert dst.read_text().endswith("本專案補充。\n")
    assert SKILL_REL not in manifest(target)


# --------------------------------------------------------------- 其餘行為


def test_upstream_removal_is_reported_not_deleted(pack, target):
    apply(pack, target)
    (pack / SKILL_SRC).unlink()

    out = apply(pack, target)

    assert summary(out, "上游已移除") == 1
    assert SKILL_REL in out
    assert (target / SKILL_REL).exists()


def test_settings_json_merges_both_layers_and_updates(pack, target):
    apply(pack, target)
    settings = json.loads((target / ".claude/settings.json").read_text())
    core_allow = json.loads((pack / "core/.claude/settings.json").read_text())
    profile_allow = json.loads(
        (pack / "profiles/software/.claude/settings.json").read_text()
    )
    assert settings["permissions"]["allow"] == (
        core_allow["permissions"]["allow"] + profile_allow["permissions"]["allow"]
    )

    core_allow["permissions"]["allow"].append("Bash(echo:*)")
    (pack / "core/.claude/settings.json").write_text(json.dumps(core_allow, indent=2))
    out = apply(pack, target)

    assert summary(out, "更新") == 1
    assert "Bash(echo:*)" in (target / ".claude/settings.json").read_text()


def test_dry_run_writes_nothing_on_fresh_target(pack, target):
    apply(pack, target, "--dry-run")
    assert not target.exists()


def test_dry_run_writes_nothing_on_existing_target(pack, target):
    apply(pack, target)
    before = manifest(target)
    src = pack / KICKOFF_SRC
    src.write_text(src.read_text() + "\n上游修正。\n")
    kickoff_before = (target / KICKOFF_REL).read_text()

    out = apply(pack, target, "--dry-run")

    assert summary(out, "更新") == 1  # 有報告
    assert (target / KICKOFF_REL).read_text() == kickoff_before  # 但沒動
    assert manifest(target) == before
