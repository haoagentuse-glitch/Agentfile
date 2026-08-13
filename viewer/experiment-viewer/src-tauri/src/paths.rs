// Path 邊界邏輯：CLI 參數正規化、project root ↔ records/experiments 佈局解析、
// 與 artifact containment 檢查。純 PathBuf 邏輯，可在任何 host OS 上單元測試。
// 真正的「Windows 絕對路徑／UNC 是不是絕對路徑」語意交給目標 OS 的 std::path 判斷，
// classify_root_input 只做形狀辨識（用於 Diagnostics 顯示來源路徑長什麼樣），不重新實作 OS 規則。

use std::ffi::OsStr;
use std::path::{Component, Path, PathBuf};

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum RootPathKind {
    WindowsDrive,
    Unc,
    WslUnc,
    Relative,
}

impl RootPathKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            RootPathKind::WindowsDrive => "windows_drive",
            RootPathKind::Unc => "unc",
            RootPathKind::WslUnc => "wsl_unc",
            RootPathKind::Relative => "relative",
        }
    }
}

pub fn classify_root_input(raw: &str) -> RootPathKind {
    let trimmed = raw.trim();
    if is_unc_path(trimmed) {
        if is_wsl_unc_path(trimmed) {
            return RootPathKind::WslUnc;
        }
        return RootPathKind::Unc;
    }
    if is_windows_drive_path(trimmed) {
        return RootPathKind::WindowsDrive;
    }
    RootPathKind::Relative
}

fn is_windows_drive_path(raw: &str) -> bool {
    let bytes = raw.as_bytes();
    bytes.len() >= 2 && bytes[0].is_ascii_alphabetic() && bytes[1] == b':'
}

fn is_unc_path(raw: &str) -> bool {
    raw.starts_with("\\\\") || raw.starts_with("//")
}

fn is_wsl_unc_path(raw: &str) -> bool {
    let lower = raw.to_ascii_lowercase();
    lower.contains("wsl$") || lower.contains("wsl.localhost")
}

/// CLI 參數（`OsString`，保留原始位元組，不先轉成有損的 `String`）解析成一個可以拿去
/// canonicalize 的路徑。是否為絕對路徑交給編譯目標 OS 的 `Path::is_absolute` 判斷——
/// Windows build 上對 `C:\...`／`\\server\share` 會回 true，不需要自己重新猜規則。
pub fn resolve_initial_root(raw: &OsStr, cwd: &Path) -> PathBuf {
    let candidate = Path::new(raw);
    if candidate.is_absolute() {
        candidate.to_path_buf()
    } else {
        cwd.join(candidate)
    }
}

/// PROJECT_ROOT 契約：使用者可以指到 project 根目錄，也可以（沿用舊習慣）直接指到
/// `<projectRoot>/records/experiments`。兩種輸入都要能可靠推回同一組
/// `(project_root, records_root)`，containment 永遠以 project_root 為界。
/// `canon` 必須已經是 canonicalize 過的路徑（存在、已解掉 `.`/`..`/symlink）。
pub fn resolve_project_layout(canon: &Path) -> (PathBuf, PathBuf) {
    if is_records_experiments_dir(canon) {
        let project_root = canon
            .parent()
            .and_then(Path::parent)
            .map(Path::to_path_buf)
            .unwrap_or_else(|| canon.to_path_buf());
        (project_root, canon.to_path_buf())
    } else {
        let records_root = canon.join("records").join("experiments");
        (canon.to_path_buf(), records_root)
    }
}

fn is_records_experiments_dir(path: &Path) -> bool {
    let mut components: Vec<Component> = path.components().collect();
    let last = components.pop();
    let second_last = components.pop();
    match (second_last, last) {
        (Some(a), Some(b)) => {
            component_eq_ignore_case(a, "records") && component_eq_ignore_case(b, "experiments")
        }
        _ => false,
    }
}

fn component_eq_ignore_case(component: Component, expected: &str) -> bool {
    component
        .as_os_str()
        .to_str()
        .map(|s| s.eq_ignore_ascii_case(expected))
        .unwrap_or(false)
}

#[derive(Debug)]
pub enum ResolveError {
    /// 路徑本身合法（沒有 `..`、沒有絕對路徑覆寫），但實體檔案／目錄不存在——
    /// 呼叫端可能把這個當成「空狀態」（目錄不存在＝這個 profile 還沒有這類紀錄）。
    NotFound,
    /// 路徑不合法（跳脫 root、格式錯誤）或存在但無法讀取（權限等）——一律視為真正的錯誤，
    /// 不得被吞成空狀態。
    Invalid(String),
}

/// 把使用者／manifest 提供的相對路徑釘死在 project root 底下，拒絕任何 `..` 跳脫，
/// 再用 canonicalize 確認真正解析出來的實體路徑仍在 root 內（擋 symlink 跳脫）。
/// 回傳值特意區分「不存在」跟「其他錯誤」——只有前者可以被上層當成空狀態。
pub fn resolve_within_root(root: &Path, relative: &str) -> Result<PathBuf, ResolveError> {
    let relative_path = Path::new(relative);
    let has_root_or_prefix = relative_path.is_absolute()
        || relative_path.has_root()
        || relative_path
            .components()
            .any(|c| matches!(c, Component::Prefix(_) | Component::RootDir));
    if has_root_or_prefix {
        return Err(ResolveError::Invalid(format!("路徑必須是相對路徑：{relative}")));
    }
    if relative_path
        .components()
        .any(|c| matches!(c, Component::ParentDir))
    {
        return Err(ResolveError::Invalid(format!("路徑不可包含 ..：{relative}")));
    }

    let joined = root.join(relative_path);

    let root_canon = std::fs::canonicalize(root).map_err(|e| {
        classify_io_error(e, format!("project root 無法解析：{relative}"))
    })?;
    let joined_canon = std::fs::canonicalize(&joined).map_err(|e| {
        classify_io_error(e, format!("{relative} 無法解析"))
    })?;

    if joined_canon.starts_with(&root_canon) {
        Ok(joined_canon)
    } else {
        Err(ResolveError::Invalid(format!("路徑超出 project root 範圍：{relative}")))
    }
}

fn classify_io_error(e: std::io::Error, context: String) -> ResolveError {
    if e.kind() == std::io::ErrorKind::NotFound {
        ResolveError::NotFound
    } else {
        ResolveError::Invalid(format!("{context}：{e}"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classifies_windows_drive_path() {
        assert_eq!(classify_root_input(r"C:\Users\me\records"), RootPathKind::WindowsDrive);
        assert_eq!(classify_root_input(r"D:\data"), RootPathKind::WindowsDrive);
    }

    #[test]
    fn classifies_unc_path() {
        assert_eq!(classify_root_input(r"\\fileserver\share\records"), RootPathKind::Unc);
        assert_eq!(classify_root_input("//fileserver/share/records"), RootPathKind::Unc);
    }

    #[test]
    fn classifies_wsl_unc_path() {
        assert_eq!(
            classify_root_input(r"\\wsl$\Ubuntu\home\me\records"),
            RootPathKind::WslUnc
        );
        assert_eq!(
            classify_root_input(r"\\wsl.localhost\Ubuntu\home\me\records"),
            RootPathKind::WslUnc
        );
    }

    #[test]
    fn classifies_relative_path() {
        assert_eq!(classify_root_input("records/experiments"), RootPathKind::Relative);
        assert_eq!(classify_root_input("."), RootPathKind::Relative);
    }

    #[test]
    fn root_path_kind_as_str_round_trips_every_variant() {
        assert_eq!(RootPathKind::WindowsDrive.as_str(), "windows_drive");
        assert_eq!(RootPathKind::Unc.as_str(), "unc");
        assert_eq!(RootPathKind::WslUnc.as_str(), "wsl_unc");
        assert_eq!(RootPathKind::Relative.as_str(), "relative");
    }

    #[test]
    fn resolve_initial_root_joins_relative_with_cwd() {
        let cwd = Path::new("/home/me/project");
        let resolved = resolve_initial_root(OsStr::new("records/experiments"), cwd);
        assert_eq!(resolved, PathBuf::from("/home/me/project/records/experiments"));
    }

    #[test]
    fn resolve_initial_root_keeps_absolute_as_is() {
        let cwd = Path::new("/home/me/project");
        let resolved = resolve_initial_root(OsStr::new("/tmp/other-root"), cwd);
        assert_eq!(resolved, PathBuf::from("/tmp/other-root"));
    }

    #[test]
    fn resolve_project_layout_treats_project_root_as_is() {
        let (project_root, records_root) = resolve_project_layout(Path::new("/home/me/my-project"));
        assert_eq!(project_root, PathBuf::from("/home/me/my-project"));
        assert_eq!(records_root, PathBuf::from("/home/me/my-project/records/experiments"));
    }

    #[test]
    fn resolve_project_layout_recovers_project_root_from_records_experiments() {
        let (project_root, records_root) =
            resolve_project_layout(Path::new("/home/me/my-project/records/experiments"));
        assert_eq!(project_root, PathBuf::from("/home/me/my-project"));
        assert_eq!(records_root, PathBuf::from("/home/me/my-project/records/experiments"));
    }

    #[test]
    fn resolve_project_layout_is_case_insensitive_for_the_fixed_subpath() {
        // 比對邏輯本身大小寫不敏感（Windows 檔案系統不分大小寫，使用者可能貼上大小寫
        // 不一致的路徑）。測試路徑用正斜線——反斜線只有在編譯目標是 Windows 時才會被
        // `std::path` 當成分隔符號解析，這裡測的是我們自己的比對邏輯，不是目標 OS 語意。
        let (project_root, _) = resolve_project_layout(Path::new("/proj/Records/Experiments"));
        assert_eq!(project_root, PathBuf::from("/proj"));
    }

    fn make_temp_dir(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("experiment-viewer-test-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn resolve_within_root_accepts_nested_file() {
        let root = make_temp_dir("nested-ok");
        std::fs::create_dir_all(root.join("artifacts")).unwrap();
        std::fs::write(root.join("artifacts/plot.png"), b"fake").unwrap();

        let resolved = resolve_within_root(&root, "artifacts/plot.png").unwrap();
        assert!(resolved.starts_with(std::fs::canonicalize(&root).unwrap()));

        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn resolve_within_root_rejects_dotdot_traversal() {
        let root = make_temp_dir("traversal-dotdot");
        std::fs::create_dir_all(&root).unwrap();

        match resolve_within_root(&root, "../../etc/passwd") {
            Err(ResolveError::Invalid(msg)) => assert!(msg.contains("..")),
            other => panic!("expected Invalid(..), got {other:?}"),
        }

        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn resolve_within_root_rejects_absolute_relative_arg() {
        let root = make_temp_dir("traversal-absolute");

        let absolute = std::env::temp_dir().join("outside-project");
        let absolute = absolute.to_string_lossy();
        match resolve_within_root(&root, &absolute) {
            Err(ResolveError::Invalid(msg)) => assert!(msg.contains("相對路徑")),
            other => panic!("expected Invalid(相對路徑), got {other:?}"),
        }

        #[cfg(windows)]
        for rooted in [r"\Windows\System32", r"C:drive-relative"] {
            match resolve_within_root(&root, rooted) {
                Err(ResolveError::Invalid(msg)) => assert!(msg.contains("相對路徑")),
                other => panic!("expected Invalid(相對路徑), got {other:?}"),
            }
        }

        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn resolve_within_root_rejects_symlink_escape() {
        let root = make_temp_dir("traversal-symlink");
        let outside = make_temp_dir("traversal-symlink-outside");
        std::fs::write(outside.join("secret.txt"), b"secret").unwrap();

        #[cfg(unix)]
        {
            std::os::unix::fs::symlink(outside.join("secret.txt"), root.join("link.txt")).unwrap();
            match resolve_within_root(&root, "link.txt") {
                Err(ResolveError::Invalid(msg)) => assert!(msg.contains("超出 project root 範圍")),
                other => panic!("expected Invalid(超出 project root 範圍), got {other:?}"),
            }
        }

        std::fs::remove_dir_all(&root).unwrap();
        std::fs::remove_dir_all(&outside).unwrap();
    }

    #[test]
    fn resolve_within_root_reports_not_found_for_missing_dir() {
        let root = make_temp_dir("missing-dir");

        match resolve_within_root(&root, "definitions") {
            Err(ResolveError::NotFound) => {}
            other => panic!("expected NotFound, got {other:?}"),
        }

        std::fs::remove_dir_all(&root).unwrap();
    }
}
