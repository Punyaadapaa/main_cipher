// Logika antarmuka Classic Ciphers (pipeline Plaintext → Cipher → Ciphertext).
"use strict";
const $ = id => document.getElementById(id);

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
}

function perbarui() {
  $("hint").textContent = HINT[$("cipher").value];
  $("otp-key").hidden = $("cipher").value !== "otp";
  const teks = tipeInput() === "teks";
  $("panel-teks").hidden = !teks;
  $("panel-file").hidden = teks;
  tampilOutputTeks(teks);
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
  f.append("text", $("text").value);
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

$("btn-enc").addEventListener("click", () => { setMode("enc"); proses(); });
$("btn-dec").addEventListener("click", () => { setMode("dec"); proses(); });
$("cipher").addEventListener("change", perbarui);
document.querySelectorAll('input[name="input_type"]').forEach(r => r.addEventListener("change", perbarui));
$("save-plain").addEventListener("click", () => unduh($("text").value, mode === "enc" ? "plainteks.txt" : "cipherteks.txt"));
$("save-out").addEventListener("click", () => unduh($("out").value, mode === "enc" ? "cipherteks.txt" : "plainteks.txt"));
$("unduh-file").addEventListener("click", () => { if (hasil.blob) unduh(hasil.blob, hasil.nama); });
$("genkey").addEventListener("click", async () => {
  const r = await fetch("/api/genkey?n=50000");
  if (r.ok) unduh(await r.blob(), "otp_key.txt");
});

perbarui();
