// c6 / CVE-2026-115905 — Rust zip2 "zip cloaking" parser differential.
//
// The deploy service VALIDATES archive entries by their Central-Directory names
// (an allow-list), but EXTRACTS by the Local-File-Header names. A "cloaked" zip
// whose CD name is the approved `bundle.json` while its LFH name is something
// else writes a file the validator never approved — the inspector and the
// extractor disagree (TOCTOU between the two parsers).
//
// Isolated training range — do not deploy.
use std::fs;
use std::io::Read;
use std::path::Path;
use tiny_http::{Method, Response, Server};

const FLAG: &str = "0DAY{z1p2_cl04k1ng_c3ntral_vs_l0cal_h34d3r}";
const EXTRACT: &str = "/app/extract";
const ALLOWED: &str = "bundle.json";

fn u16le(b: &[u8], o: usize) -> usize {
    (b[o] as usize) | ((b[o + 1] as usize) << 8)
}
fn u32le(b: &[u8], o: usize) -> usize {
    (b[o] as usize) | ((b[o + 1] as usize) << 8) | ((b[o + 2] as usize) << 16) | ((b[o + 3] as usize) << 24)
}

// Central-Directory names (what the validator inspects)
fn cd_names(b: &[u8]) -> Vec<String> {
    let mut names = Vec::new();
    let mut i = 0usize;
    while i + 46 <= b.len() {
        if b[i..i + 4] == [0x50, 0x4b, 0x01, 0x02] {
            let nl = u16le(b, i + 28);
            if i + 46 + nl <= b.len() {
                names.push(String::from_utf8_lossy(&b[i + 46..i + 46 + nl]).to_string());
            }
        }
        i += 1;
    }
    names
}

// Local-File-Header (name, stored data) — what the extractor actually writes
fn lfh_entries(b: &[u8]) -> Vec<(String, Vec<u8>)> {
    let mut out = Vec::new();
    let mut i = 0usize;
    while i + 30 <= b.len() {
        if b[i..i + 4] == [0x50, 0x4b, 0x03, 0x04] {
            let comp = u32le(b, i + 18);
            let nl = u16le(b, i + 26);
            let el = u16le(b, i + 28);
            let name_off = i + 30;
            let data_off = name_off + nl + el;
            if data_off + comp <= b.len() {
                let name = String::from_utf8_lossy(&b[name_off..name_off + nl]).to_string();
                let data = b[data_off..data_off + comp].to_vec();
                out.push((name, data));
            }
        }
        i += 1;
    }
    out
}

fn deploy(body: &[u8]) -> (u16, String) {
    // fresh extraction dir per request (no state leaking between deploys)
    let _ = fs::remove_dir_all(EXTRACT);
    let _ = fs::create_dir_all(EXTRACT);
    // 1) validate on Central-Directory names
    for n in cd_names(body) {
        if n != ALLOWED {
            return (403, format!("rejected: entry {:?} is not an approved config name\n", n));
        }
    }
    // 2) extract on Local-File-Header names (the differential)
    for (name, data) in lfh_entries(body) {
        let dest = format!("{}/{}", EXTRACT, name);
        if let Some(parent) = Path::new(&dest).parent() {
            let _ = fs::create_dir_all(parent);
        }
        let _ = fs::write(&dest, &data);
    }
    // 3) a privileged file only a cloaked archive could have written
    match fs::read_to_string(format!("{}/data/unlocked", EXTRACT)) {
        Ok(s) if s.trim() == "yes" => (200, format!("deploy ok\n{}\n", FLAG)),
        _ => (200, "deploy ok (config bundle accepted)\n".to_string()),
    }
}

fn main() {
    let _ = fs::create_dir_all(EXTRACT);
    let server = Server::http("0.0.0.0:80").unwrap();
    println!("[c6] zip-cloak deploy service on :80");
    for mut req in server.incoming_requests() {
        let (code, text) = if *req.method() == Method::Post && req.url() == "/deploy" {
            let mut body = Vec::new();
            let _ = req.as_reader().read_to_end(&mut body);
            deploy(&body)
        } else {
            (200, "Config deploy service. POST a config bundle (.zip) to /deploy\n".to_string())
        };
        let _ = req.respond(Response::from_string(text).with_status_code(code));
    }
}
