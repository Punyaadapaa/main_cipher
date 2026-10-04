// >_ MainCipher — interface logic: POST to /api/*, render results, download
"use strict";
const $ = id => document.getElementById(id);

(function initTheme(){
  const btn = document.getElementById("theme-toggle");
  if(!btn) return;
  const lbl = document.getElementById("ti-label");
  const sys = () => window.matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light";
  let saved = null;
  try { saved = localStorage.getItem("cc-theme"); } catch(e){}
  const apply = t => {
    document.documentElement.setAttribute("data-theme", t);
    if (lbl) lbl.textContent = (t === "dark") ? "Dark" : "Light";
  };
  apply(saved || sys());
  btn.addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme") || sys();
    const next = (cur === "dark") ? "light" : "dark";
    apply(next);
    try { localStorage.setItem("cc-theme", next); } catch(e){}
  });
})();

const HINT = {
  shift: "Single number, e.g. 3",
  substitution: "26 distinct letters (alphabet permutation), e.g. QWERTYUIOPASDFGHJKLZXCVBNM",
  affine: "Two numbers 'a b'; a must be coprime with 26 (text) / odd for file (mod 256), e.g. 7 3",
  vigenere: "Keyword of any length, e.g. LEMON",
  hill: "n×n matrix row-wise, e.g. 3 3 2 5 (2×2). Determinant must be coprime with 26 (text) / odd (file)",
  permutation: "Permutation 1..m, e.g. 3 1 2 (block of m letters)",
  otp: "Upload a key file. If empty, enter the key letters in the field instead.",
  playfair: "Alphabetic keyword, e.g. MONARCHY (5×5 matrix, I/J merged)"
};

const hasil = { plain: "", cipher: "", blob: null, nama: null };

const hanyaHuruf = s => s.toUpperCase().replace(/[^A-Z]/g, "");
const kelompok5 = s => hanyaHuruf(s).replace(/(.{5})(?=.)/g, "$1 ");

const tipeInput = () => document.querySelector('input[name="input_type"]:checked').value;
const formatGroup = () => document.querySelector('input[name="group"]:checked').value;

function perbarui() {
  $("hint").textContent = HINT[$("cipher").value];
  $("otp-key").hidden = $("cipher").value !== "otp";
  const teks = tipeInput() === "teks";
  $("panel-teks").hidden = !teks;
  $("panel-file").hidden = teks;
  $("fmt-card").hidden = !teks;
}
document.querySelectorAll('input[name="input_type"]').forEach(r => r.addEventListener("change", perbarui));
$("cipher").addEventListener("change", perbarui);
perbarui();

function dataForm(mode) {
  const f = new FormData();
  f.append("cipher", $("cipher").value);
  f.append("mode", mode);
  f.append("key", $("key").value);
  const kf = $("keyfile").files[0];
  if (kf) f.append("keyfile", kf);
  return f;
}

function sedangProses(status) {
  $("btn-enc").disabled = status;
  $("btn-dec").disabled = status;
  $("btn-enc").textContent = status ? "Working…" : "Encrypt!";
  $("btn-dec").textContent = status ? "Working…" : "Decrypt!";
}

function tampilkanHasilTeks(plain, cipher) {
  hasil.plain = plain;
  hasil.cipher = cipher;
  $("out-plain").value = plain;
  $("out-cipher").value = cipher;
  $("grid-teks").hidden = false;
  $("grid-file").hidden = true;
  $("results").hidden = false;
  $("dl-info").textContent = "Ciphertext shown in selected format — use Save to download as .txt";
}

async function prosesTeks(mode) {
  const f = dataForm(mode);
  f.append("text", $("text").value);
  f.append("group", formatGroup());
  const r = await fetch("/api/text", { method: "POST", body: f });
  const j = await r.json();
  if (!r.ok) { $("err").textContent = j.error; return; }
  if (mode === "enc") {
    tampilkanHasilTeks(hanyaHuruf($("text").value), j.result);
  } else {
    const cipherTampil = formatGroup() === "5" ? kelompok5($("text").value) : hanyaHuruf($("text").value);
    tampilkanHasilTeks(j.result, cipherTampil);
  }
}

async function prosesFile(mode) {
  const u = $("file").files[0];
  if (!u) { $("err").textContent = "Please select a file first."; return; }
  const f = dataForm(mode);
  f.append("file", u);
  const r = await fetch("/api/file", { method: "POST", body: f });
  if (!r.ok) { $("err").textContent = (await r.json()).error; return; }
  hasil.blob = await r.blob();
  hasil.nama = decodeURIComponent(r.headers.get("X-Filename"));
  hasil.plain = ""; hasil.cipher = "";
  $("grid-teks").hidden = true;
  $("grid-file").hidden = false;
  $("results").hidden = false;
  $("hasil-file").textContent = mode === "enc"
    ? "Encrypted: " + hasil.nama + " (every byte was encrypted; file cannot be opened before decryption)."
    : "Decrypted: " + hasil.nama + " (original file restored and ready to open).";
  $("dl-info").textContent = "";
}

async function proses(mode) {
  $("err").textContent = "";
  sedangProses(true);
  try {
    if (tipeInput() === "teks") await prosesTeks(mode);
    else await prosesFile(mode);
  } catch (e) {
    $("err").textContent = "Failed: " + e.message;
  } finally {
    sedangProses(false);
  }
}

function unduh(konten, nama, tipe) {
  const blob = konten instanceof Blob ? konten : new Blob([konten], { type: tipe || "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = nama;
  a.click();
  URL.revokeObjectURL(a.href);
}

$("btn-enc").addEventListener("click", () => proses("enc"));
$("btn-dec").addEventListener("click", () => proses("dec"));
$("save-plain").addEventListener("click", () => { if (hasil.plain) unduh(hasil.plain, "plaintext.txt"); else $("err").textContent = "No plaintext to save — run Encrypt or Decrypt first."; });
$("save-cipher").addEventListener("click", () => { if (hasil.cipher) unduh(hasil.cipher, "ciphertext.txt"); else $("err").textContent = "No ciphertext to save — run Encrypt or Decrypt first."; });
$("unduh-file").addEventListener("click", () => { if (hasil.blob) unduh(hasil.blob, hasil.nama); });
$("genkey").addEventListener("click", async () => {
  const r = await fetch("/api/genkey?n=50000");
  if (r.ok) unduh(await r.blob(), "otp_key.txt");
});
