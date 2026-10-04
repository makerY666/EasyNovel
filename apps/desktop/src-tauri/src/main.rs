#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde::{Deserialize, Serialize};
use std::{io::{BufRead, BufReader, Read, Write}, net::{TcpListener, TcpStream}, process::{Child, Command, Stdio}, sync::{Arc, Mutex}, time::Duration};
use tauri::{Manager, State};
#[cfg(windows)] use std::os::windows::{process::CommandExt, io::AsRawHandle};

#[derive(Clone, Serialize, Deserialize)]
struct BackendConfig { base_url: String, token: String }
struct BackendState { config: Arc<Mutex<Option<BackendConfig>>>, error: Arc<Mutex<Option<String>>>, child: Arc<Mutex<Option<Child>>> }

#[tauri::command]
async fn backend_config(state: State<'_, BackendState>) -> Result<BackendConfig, String> {
    for _ in 0..180 {
        if let Some(config) = state.config.lock().unwrap().clone() { return Ok(config); }
        if let Some(error) = state.error.lock().unwrap().clone() { return Err(error); }
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
    Err("本地创作服务启动超时。请检查安装目录与数据目录写入权限。".into())
}

fn local_http(config: &BackendConfig, method: &str, path: &str) -> bool {
    let address = config.base_url.trim_start_matches("http://");
    if let Ok(address) = address.parse() {
        if let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_secs(2)) {
            let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
            let request = format!("{method} {path} HTTP/1.1\r\nHost: {address}\r\nAuthorization: Bearer {}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n", config.token);
            if stream.write_all(request.as_bytes()).is_ok() {
                let mut bytes = [0; 128];
                if let Ok(n) = stream.read(&mut bytes) { return String::from_utf8_lossy(&bytes[..n]).starts_with("HTTP/1.1 200"); }
            }
        }
    }
    false
}

fn main() {
    let state = BackendState { config: Arc::new(Mutex::new(None)), error: Arc::new(Mutex::new(None)), child: Arc::new(Mutex::new(None)) };
    let child_state = state.child.clone(); let ready = state.config.clone(); let error = state.error.clone();
    tauri::Builder::default().manage(state).invoke_handler(tauri::generate_handler![backend_config])
        .setup(move |app| {
            let port = TcpListener::bind("127.0.0.1:0")?.local_addr()?.port();
            let executable = std::env::current_exe()?;
            let bundled = executable.parent().unwrap().join("easynovel-backend.exe");
            let development = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("binaries/easynovel-backend-x86_64-pc-windows-msvc.exe");
            let backend = if bundled.exists() { bundled } else { development };
            let mut command = Command::new(backend);
            command.args(["--port", &port.to_string()]).stdout(Stdio::piped()).stderr(Stdio::null());
            #[cfg(windows)] command.creation_flags(0x08000000);
            match command.spawn() {
                Ok(mut child) => {
                    #[cfg(windows)] unsafe {
                        use windows_sys::Win32::System::JobObjects::*;
                        let job = CreateJobObjectW(std::ptr::null(), std::ptr::null());
                        if !job.is_null() {
                            let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
                            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
                            let configured = SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits as *const _ as *const _, std::mem::size_of_val(&limits) as u32);
                            if configured != 0 { AssignProcessToJobObject(job, child.as_raw_handle() as _); }
                            // This handle deliberately lives until process exit, ensuring bootloader descendants die with the shell.
                        }
                    }
                    let stdout = child.stdout.take().unwrap();
                    *child_state.lock().unwrap() = Some(child);
                    let ready = ready.clone(); let error = error.clone();
                    std::thread::spawn(move || {
                        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                            if let Ok(config) = serde_json::from_str::<BackendConfig>(&line) {
                                for _ in 0..180 {
                                    if local_http(&config, "GET", "/api/v1/health") { *ready.lock().unwrap() = Some(config); return; }
                                    std::thread::sleep(Duration::from_millis(500));
                                }
                                *error.lock().unwrap() = Some("后台进程已启动，但健康检查未通过。".into()); return;
                            }
                        }
                        *error.lock().unwrap() = Some("创作服务异常退出，请重新启动工作台。".into());
                    });
                }
                Err(_) => { *error.lock().unwrap() = Some("无法启动打包的创作服务，请重新安装完整桌面版。".into()); }
            }
            let handle = app.handle().clone();
            app.get_webview_window("main").unwrap().on_window_event(move |event| {
                if let tauri::WindowEvent::Destroyed = event {
                    let state = handle.state::<BackendState>();
                    if let Some(config) = state.config.lock().unwrap().clone() { local_http(&config, "POST", "/api/v1/shutdown"); }
                    if let Some(mut child) = state.child.lock().unwrap().take() {
                        std::thread::sleep(Duration::from_millis(500));
                        if child.try_wait().ok().flatten().is_none() {
                            #[cfg(windows)] { let _ = Command::new("taskkill").args(["/PID", &child.id().to_string(), "/T", "/F"]).creation_flags(0x08000000).status(); }
                            let _ = child.kill(); let _ = child.wait();
                        }
                    }
                }
            });
            Ok(())
        }).run(tauri::generate_context!()).expect("桌面工作站启动失败");
}
