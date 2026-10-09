use std::process::Command;

fn main() {
    let _ = Command::new("uv")
        .arg("run")
        .arg("uvicorn")
        .arg("main:app")
        .arg("--port")
        .arg("8000")
        .current_dir("F:\\Antigravity\\AstralSage\\core")
        .spawn()
        .expect("failed to execute process")
        .wait();
}
