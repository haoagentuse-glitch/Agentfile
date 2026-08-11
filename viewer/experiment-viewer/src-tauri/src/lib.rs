mod paths;

use std::path::{Path, PathBuf};
use tauri::State;
use tauri_plugin_opener::OpenerExt;

use paths::ResolveError;

// 啟動時的 PROJECT_ROOT 只算一次：CLI 有給就用 CLI（相對於當時 cwd、用 OsString 解析，
// 不先轉成有損的 String），沒給就是 None，前端會退回 folder picker。存進 managed state
// 而不是重算，因為 cwd 只有啟動當下有意義，之後使用者可能已經 cd 到別的地方。
struct InitialRoot(Option<String>);

#[tauri::command]
fn initial_project_root(state: State<InitialRoot>) -> Option<String> {
    state.0.clone()
}

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct ProjectLayout {
    project_root: String,
    records_root: String,
    root_kind: String,
}

fn path_to_string(path: &Path) -> Result<String, String> {
    path.to_str()
        .map(|s| s.to_string())
        .ok_or_else(|| format!("{} 含有無法轉成 UTF-8 的路徑字元", path.display()))
}

// PROJECT_ROOT 契約：使用者可以指到 project 根目錄，也可以（沿用舊習慣）直接指到
// `<projectRoot>/records/experiments`——兩種輸入都在這裡統一推回同一組
// (project_root, records_root)，之後所有 containment 檢查都以 project_root 為界，
// 不是 records_root。`root_kind` 是輸入路徑的形狀（Windows drive／UNC／WSL UNC／相對），
// 純粹給 Diagnostics 顯示用，不影響解析邏輯本身。
#[tauri::command]
fn resolve_project_layout(input: String) -> Result<ProjectLayout, String> {
    let root_kind = paths::classify_root_input(&input).as_str().to_string();
    let canon = std::fs::canonicalize(&input).map_err(|e| format!("{input} 無法解析：{e}"))?;
    if !canon.is_dir() {
        return Err(format!("{input} 不是資料夾"));
    }
    let (project_root, records_root) = paths::resolve_project_layout(&canon);
    Ok(ProjectLayout {
        project_root: path_to_string(&project_root)?,
        records_root: path_to_string(&records_root)?,
        root_kind,
    })
}

// 目錄不存在＝這個 profile 還沒有這類紀錄的空狀態；其他錯誤（權限、跳脫 root）一律
// 往上拋成真正的錯誤，不能被吞掉偽裝成空狀態。回傳值是已經 containment 驗證過、
// 相對 project_root 的路徑（用 Rust 的 PathBuf::join 組出來），前端只把它們原樣傳回
// read_project_file，不自己再切割或拼字串。
#[tauri::command]
fn list_project_dir(root: String, relative: String) -> Result<Vec<String>, String> {
    let resolved = match paths::resolve_within_root(&PathBuf::from(root), &relative) {
        Ok(p) => p,
        Err(ResolveError::NotFound) => return Ok(Vec::new()),
        Err(ResolveError::Invalid(msg)) => return Err(msg),
    };
    let entries = match std::fs::read_dir(&resolved) {
        Ok(e) => e,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => return Err(format!("讀取目錄 {relative} 失敗：{e}")),
    };
    let mut relative_paths = Vec::new();
    for entry in entries {
        let entry = entry.map_err(|e| e.to_string())?;
        let child = Path::new(&relative).join(entry.file_name());
        relative_paths.push(path_to_string(&child)?);
    }
    relative_paths.sort();
    Ok(relative_paths)
}

// 所有跨 project root 邊界的讀取都走這裡，而不是讓前端直接呼叫 fs plugin——
// artifact 路徑來自資料內容（run-envelope 的 artifacts[]、viewer.json 的 dir mapping），
// 不是使用者親手選的，必須在 Rust 這層做 containment 檢查，Vue 不該自己切割或拼 OS path。
#[tauri::command]
fn read_project_file(root: String, relative: String) -> Result<String, String> {
    let resolved = match paths::resolve_within_root(&PathBuf::from(root), &relative) {
        Ok(p) => p,
        Err(ResolveError::NotFound) => return Err(format!("{relative} 不存在")),
        Err(ResolveError::Invalid(msg)) => return Err(msg),
    };
    std::fs::read_to_string(&resolved).map_err(|e| format!("讀取 {relative} 失敗：{e}"))
}

// 專給「這個檔案存不存在」這種是非題用（例如判斷 viewer.json 在不在）——
// 跟 read_project_file 分開,這樣呼叫端不需要靠字串比對錯誤訊息去猜是不是 NotFound。
#[tauri::command]
fn path_exists(root: String, relative: String) -> Result<bool, String> {
    match paths::resolve_within_root(&PathBuf::from(root), &relative) {
        Ok(_) => Ok(true),
        Err(ResolveError::NotFound) => Ok(false),
        Err(ResolveError::Invalid(msg)) => Err(msg),
    }
}

// Artifacts 分頁「開啟」按鈕專用：containment 與 OS opener 都封裝在同一個 Rust command。
// 前端拿不到已解析的絕對路徑，也不需要 opener:allow-open-path 這個過寬的 capability。
// 開啟操作預期檔案確實存在；NotFound 在這裡是真正的錯誤，不是空狀態。
#[tauri::command]
fn open_artifact(app: tauri::AppHandle, root: String, relative: String) -> Result<(), String> {
    let resolved = match paths::resolve_within_root(&PathBuf::from(root), &relative) {
        Ok(p) => p,
        Err(ResolveError::NotFound) => return Err(format!("{relative} 不存在")),
        Err(ResolveError::Invalid(msg)) => return Err(msg),
    };
    let path = path_to_string(&resolved)?;
    app.opener()
        .open_path(path, None::<&str>)
        .map_err(|e| format!("開啟 {relative} 失敗：{e}"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let cli_root = std::env::args_os().nth(1).map(|raw| {
        let cwd = std::env::current_dir().unwrap_or_default();
        paths::resolve_initial_root(&raw, &cwd)
            .to_string_lossy()
            .into_owned()
    });

    tauri::Builder::default()
        .manage(InitialRoot(cli_root))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            initial_project_root,
            resolve_project_layout,
            read_project_file,
            list_project_dir,
            path_exists,
            open_artifact
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::ProjectLayout;

    #[test]
    fn project_layout_serializes_for_the_typescript_contract() {
        let layout = ProjectLayout {
            project_root: "project".to_string(),
            records_root: "project/records/experiments".to_string(),
            root_kind: "relative".to_string(),
        };

        assert_eq!(
            serde_json::to_value(layout).unwrap(),
            serde_json::json!({
                "projectRoot": "project",
                "recordsRoot": "project/records/experiments",
                "rootKind": "relative"
            })
        );
    }
}
