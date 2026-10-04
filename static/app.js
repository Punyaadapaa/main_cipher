// Logika antarmuka Classic Ciphers (pipeline Plaintext → Cipher → Ciphertext).
"use strict";
const $ = id => document.getElementById(id);
(function initTheme(){
  const btn = document.getElementById("theme-toggle");
  if(!btn) return;
  const lbl = document.getElementById("ti-label");
  const apply = t => {
    document.documentElement.setAttribute("data-theme", t);
    if (lbl) lbl.textContent = (t === "dark") ? "Gelap" : "Terang";
    try{ localStorage.setItem("cc-theme", t); }catch(e){}
  };
  apply(document.documentElement.getAttribute("data-theme") || "light");
  btn.addEventListener("click", ()=>{
    const cur = document.documentElement.getAttribute("data-theme") || "light";
    apply(cur === "dark" ? "light" : "dark");
  });
})();

const HINT = {
  shift: "Satu angka, mis. 3",
  substitution: "26 huruf berbeda (permutasi alfabet), mis. QWERTYUIOPASDFGHJKLZXCVBNM",
  affine: "Dua angka 'a b'; a relatif prima dengan 26 (teks) / ganjil untuk file (mod 256), mis. 7 3",
  vigenere: "Kata kunci bebas panjang, mis. LEMON",
  hill: "Matriks n×n baris demi baris, mis. 3 3 2 5 (2×2). Determinan koprima mod 26 (teks) / ganjil (file)",
  permutation: "Permutasi 1..m, mis. 3 1 2 (blok m huruf)",
  otp: "Unggah file kunci. Jika kosong, isi kolom kunci dengan huruf kunci."
};

let mode = "enc";
const hasil = { blob: null, nama: null };

const tipeInput = () => document.querySelector('input[name="input_type"]:checked').value;
const formatGroup = () => document.querySelector('input[name="group"]:checked').value;

function setMode(m) {
  mode = m;
  $("btn-enc").classList.toggle("active", m === "enc");
  $("btn-dec").classList.toggle("active", m === "dec");
  $("btn-enc").setAttribute("aria-selected", m === "enc");
  $("btn-dec").setAttribute("aria-selected", m === "dec");
}

function perbarui() {
  const c = $("cipher").value;
  $("hint").textContent = HINT[c];
  $("otp-key").hidden = c !== "otp";
  // stepper SHIFT khusus cipher shift; kunci teks disembunyikan saat stepper aktif
  const isShift = c === "shift";
  $("shift-box").hidden = !isShift;
  $("key-group").hidden = isShift;
  if (isShift) sinkronShift();
  const teks = tipeInput() === "teks";
  $("panel-teks").hidden = !teks;
  $("panel-file").hidden = teks;
  tampilOutputTeks(teks);
}

/* ---- stepper SHIFT (ala cryptii: − 7 a→h +) ---- */
function shiftNilai() {
  const n = parseInt($("key").value, 10);
  return Number.isFinite(n) ? ((n % 26) + 26) % 26 : 0;
}
function sinkronShift() {
  const n = shiftNilai();
  $("shift-num").textContent = n;
  $("shift-map").textContent = String.fromCharCode(97 + n);
}
function ubahShift(d) {
  const n = ((shiftNilai() + d) % 26 + 26) % 26;
  $("key").value = String(n);
  sinkronShift();
  proses();
}

function tampilOutputTeks(teks) {
  $("out-area").hidden = !teks;
  $("file-result").hidden = teks;
}

function dataForm() {
  const f = new FormData();
  f.append("cipher", $("cipher").value);
  f.append("mode", mode);
  f.append("key", $("key").value);
  const kf = $("keyfile").files[0];
  if (kf) f.append("keyfile", kf);
  return f;
}

async function prosesTeks() {
  const f = dataForm();
  const teks = $("text").value;
  // hasil otomatis: saat pesan kosong, bersihkan hasil tanpa menampilkan error
  if (!/[A-Za-z]/.test(teks)) {
    $("err").textContent = "";
    $("out").value = "";
    $("status-line").textContent = teks ? "Tunggu ada huruf A-Z…" : "";
    $("out-title").textContent = mode === "enc" ? "Ciphertext" : "Plaintext";
    return;
  }
  f.append("text", teks);
  f.append("group", formatGroup());
  const r = await fetch("/api/text", { method: "POST", body: f });
  const j = await r.json();
  if (!r.ok) { $("err").textContent = j.error; return; }
  $("out-title").textContent = mode === "enc" ? "Ciphertext" : "Plaintext";
  $("out").value = j.result;
  $("status-line").textContent = `${mode === "enc" ? "Encoded" : "Decoded"} ${j.result.replace(/ /g, "").length} chars`;
}

async function prosesFile() {
  const u = $("file").files[0];
  if (!u) { $("err").textContent = "Pilih file terlebih dahulu."; return; }
  const f = dataForm();
  f.append("file", u);
  const r = await fetch("/api/file", { method: "POST", body: f });
  if (!r.ok) { $("err").textContent = (await r.json()).error; return; }
  hasil.blob = await r.blob();
  hasil.nama = decodeURIComponent(r.headers.get("X-Filename"));
  $("out-title").textContent = mode === "enc" ? "Ciphertext (file .dat)" : "Plaintext (file asli)";
  $("hasil-file").textContent = mode === "enc"
    ? "Enkripsi selesai: " + hasil.nama + " — seluruh byte asli ikut terenkripsi; file tak bisa dibuka aplikasi aslinya sebelum didekripsi."
    : "Dekripsi selesai: " + hasil.nama + " — file asli dipulihkan dan bisa dibuka lagi.";
  tampilOutputTeks(false);
  $("status-line").textContent = "File siap diunduh";
}

async function proses() {
  $("err").textContent = "";
  $("status-line").textContent = "";
  try {
    if (tipeInput() === "teks") await prosesTeks();
    else await prosesFile();
  } catch (e) {
    $("err").textContent = "Gagal memproses: " + e.message;
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

/* ---- hasil otomatis: proses ulang dengan debounce tiap kontrol berubah ---- */
let timerAuto = null;
function autoProses(delay) {
  clearTimeout(timerAuto);
  timerAuto = setTimeout(proses, delay === undefined ? 250 : delay);
}

$("btn-enc").addEventListener("click", () => { setMode("enc"); proses(); });
$("btn-dec").addEventListener("click", () => { setMode("dec"); proses(); });
$("btn-encrypt").addEventListener("click", () => { setMode("enc"); proses(); });
$("btn-decrypt").addEventListener("click", () => { setMode("dec"); proses(); });
$("cipher").addEventListener("change", () => { perbarui(); autoProses(0); });
$("shift-dec").addEventListener("click", () => ubahShift(-1));
$("shift-inc").addEventListener("click", () => ubahShift(1));
$("text").addEventListener("input", () => autoProses());
$("key").addEventListener("input", () => {
  if ($("cipher").value === "shift") sinkronShift();
  autoProses();
});
document.querySelectorAll('input[name="input_type"]').forEach(r => r.addEventListener("change", () => { perbarui(); autoProses(0); }));
document.querySelectorAll('input[name="group"]').forEach(r => r.addEventListener("change", () => autoProses(0)));
$("keyfile").addEventListener("change", () => autoProses(0));
$("save-plain").addEventListener("click", () => unduh($("text").value, mode === "enc" ? "plainteks.txt" : "cipherteks.txt"));
$("save-out").addEventListener("click", () => unduh($("out").value, mode === "enc" ? "cipherteks.txt" : "plainteks.txt"));
$("unduh-file").addEventListener("click", () => { if (hasil.blob) unduh(hasil.blob, hasil.nama); });
$("genkey").addEventListener("click", async () => {
  const r = await fetch("/api/genkey?n=50000");
  if (r.ok) unduh(await r.blob(), "otp_key.txt");
});

perbarui();
