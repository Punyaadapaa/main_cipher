// KriptaTool - Modern Web Interface for Classic Ciphers
// Pipeline: Input → Transform → Output

"use strict";

const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

const HINT = {
  shift: "Satu angka 0-25 (misal: 3)",
  substitution: "26 huruf berbeda (permutasi A-Z), misal: QWERTYUIOPASDFGHJKLZXCVBNM",
  affine: "Dua angka 'a b' (a koprima dengan 26), misal: 5,8",
  vigenere: "Kata kunci (huruf A-Z), misal: LEMON",
  hill: "Matriks n×n baris demi baris (kuadrat), misal: 3,3,2,5 (2×2)",
  permutation: "Permutasi 1..m dipisah spasi, misal: 2 1 4 3",
  otp: "Unggah file kunci berisi huruf acak (minimal panjang pesan)"
};

let mode = "enc";
let fileBlob = null;
let fileName = null;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  setupUI();
  updateUI();
});

function setupUI() {
  // Mode switch (Input) — support both names
  $$("input[name='input_type'], input[name='input-mode']").forEach(radio => {
    radio.addEventListener("change", () => updateUI());
  });

  // Format switch (Output)
  $$("input[name='output-format']").forEach(radio => {
    radio.addEventListener("change", () => updateUI());
  });

  // Action buttons — support both new and legacy ids
  const encBtn = $("btn-enc") || $("btn-encode");
  const decBtn = $("btn-dec") || $("btn-decode");
  if(encBtn) encBtn.addEventListener("click", () => { setMode("enc"); processCipher(); });
  if(decBtn) decBtn.addEventListener("click", () => { setMode("dec"); processCipher(); });

  // Cipher change
  $("cipher-select").addEventListener("change", updateUI);

  // Buttons
  $("btn-transform").addEventListener("click", processCipher);
  $("btn-clear-in").addEventListener("click", () => {
    $("plaintext").value = "";
    $("plaintext").focus();
  });
  $("btn-clear-out").addEventListener("click", () => {
    $("ciphertext").value = "";
  });
  $("btn-clear-file").addEventListener("click", () => {
    fileBlob = null;
    fileName = null;
    updateUI();
  });

  // File input
  const dropzone = $(".file-dropzone");
  const fileInput = $("input-file");
  const fileNameSpan = $("file-name");

  dropzone.addEventListener("click", () => fileInput.click());
  
  fileInput.addEventListener("change", (e) => {
    if (e.target.files[0]) {
      fileNameSpan.textContent = e.target.files[0].name;
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "var(--accent-color)";
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.style.borderColor = "var(--card-border)";
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "var(--card-border)";
    if (e.dataTransfer.files[0]) {
      fileInput.files = e.dataTransfer.files;
      fileNameSpan.textContent = e.dataTransfer.files[0].name;
    }
  });

  // Save buttons
  $("btn-save-plain").addEventListener("click", () => {
    downloadText($("plaintext").value, "plaintext.txt");
  });

  $("btn-save-out").addEventListener("click", () => {
    if (fileBlob && fileName) {
      downloadBlob(fileBlob, fileName);
    } else {
      downloadText($("ciphertext").value, "ciphertext.txt");
    }
  });

  // OTP Generate
  $("btn-genkey").addEventListener("click", async () => {
    try {
      const r = await fetch("/api/genkey?n=50000");
      if (r.ok) {
        const blob = await r.blob();
        downloadBlob(blob, "otp_key.txt");
      }
    } catch (e) {
      alert("Gagal generate kunci: " + e.message);
    }
  });
}

function syncSwitches(){
  document.querySelectorAll('.mode-switch .switch-label, .format-switch .switch-label').forEach(l=>{
    const inp=l.querySelector('input'); if(inp) l.classList.toggle('active', inp.checked);
  });
}
function updateUI() {
  syncSwitches();
  // Show/hide OTP keyfile section
  const isOtp = $("cipher-select").value === "otp";
  $("otp-group").hidden = !isOtp;
  $("key-group").hidden = isOtp;

  // Update hint
  const cipher = $("cipher-select").value;
  const hintEl = $("key-hint");
  if (hintEl) hintEl.textContent = HINT[cipher] || "";

  // Show/hide file input section — support input_type (new) and input-mode (legacy)
  let modeInput = document.querySelector('input[name="input_type"]:checked') || document.querySelector('input[name="input-mode"]:checked');
  const isFileInput = modeInput ? modeInput.value === "file" : false;
  $("file-input").hidden = !isFileInput;
  if (isFileInput) { $("plaintext").hidden = true; } else { $("plaintext").hidden = false; }
  $("plaintext").disabled = isFileInput;

  // Update output area visibility
  const isFileOutput = fileBlob !== null;
  if (isFileOutput) {
    $("file-output").hidden = false;
    $("ciphertext").hidden = true;
    $("output-filename").textContent = fileName || "output.dat";
  } else {
    $("file-output").hidden = true;
    $("ciphertext").hidden = false;
  }
}

function setMode(m) {
  mode = m;
  const encBtn = $("btn-enc") || $("btn-encode");
  const decBtn = $("btn-dec") || $("btn-decode");
  if(encBtn) encBtn.classList.toggle("active", m === "enc");
  if(decBtn) decBtn.classList.toggle("active", m === "dec");
}

function getFormat() {
  const selected = document.querySelector('input[name="output-format"]:checked');
  return selected ? selected.value : "compact";
}

async function processCipher() {
  $("cipher-status").textContent = "";
  try {
    let mi = document.querySelector('input[name="input_type"]:checked') || document.querySelector('input[name="input-mode"]:checked');
    if ((mi ? mi.value : "text") === "text") {
      await processText();
    } else {
      await processFile();
    }
  } catch (e) {
    $("cipher-status").textContent = "Error: " + e.message;
  }
}

async function processText() {
  const cipher = $("cipher-select").value;
  const key = $("cipher-key").value.trim();
  const text = $("plaintext").value.trim();

  // Validate input
  if (!text) {
    throw new Error("Plaintext kosong. Masukkan teks terlebih dahulu.");
  }

  const hasLetter = /[A-Za-z]/.test(text);
  if (!hasLetter) {
    throw new Error("Teks harus mengandung huruf A-Z.");
  }

  const formData = new FormData();
  formData.append("cipher", cipher);
  formData.append("mode", mode);
  formData.append("key", key);
  formData.append("text", text);
  formData.append("group", getFormat());

  const file = $("otp-keyfile").files[0];
  if (file) formData.append("keyfile", file);

  const resp = await fetch("/api/text", { method: "POST", body: formData });
  const data = await resp.json();

  if (!resp.ok) {
    throw new Error(data.error || "Gagal memproses");
  }

  // Update output
  $("ciphertext").value = data.result;
  const charCount = data.result.replace(/ /g, "").length;
  $("cipher-status").textContent = `${mode === "enc" ? "Enkripsi" : "Dekripsi"} berhasil • ${charCount} karakter`;
}

async function processFile() {
  const fileInput = $("input-file");
  const file = fileInput.files[0];
  
  if (!file) {
    throw new Error("Pilih file terlebih dahulu.");
  }

  const cipher = $("cipher-select").value;
  const key = $("cipher-key").value.trim();

  const formData = new FormData();
  formData.append("cipher", cipher);
  formData.append("mode", mode);
  formData.append("key", key);
  formData.append("file", file);

  const fileKey = $("otp-keyfile").files[0];
  if (fileKey) formData.append("keyfile", fileKey);

  const resp = await fetch("/api/file", { method: "POST", body: formData });

  if (!resp.ok) {
    const data = await resp.json();
    throw new Error(data.error || "Gagal memproses file");
  }

  fileBlob = await resp.blob();
  fileName = resp.headers.get("X-Filename") || file.name + (mode === "enc" ? ".dat" : "");
  
  updateUI();
  $("cipher-status").textContent = "File " + (mode === "enc" ? "terenkripsi" : "terdekripsi") + " berhasil";
}

function downloadText(content, filename) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  downloadBlob(blob, filename);
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
