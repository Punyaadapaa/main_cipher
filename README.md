# >_ MainCipher — Aplikasi Kriptografi Klasik Online (GUI Web)

Aplikasi web untuk enkripsi dan dekripsi menggunakan 8 cipher klasik. Memenuhi spesifikasi tugas mata kuliah Kriptografi.

## Fitur Utama

1. **8 Cipher Klasik:**
   - **Shift Cipher** (Caesar, geser 1 angka)
   - **Substitution Cipher** (monoalfabet, tabel permutasi 26 huruf)
   - **Affine Cipher** ($C = (a \cdot P + b) \pmod m$)
   - **Vigenere Cipher** (kunci alfabet diulang)
   - **Playfair Cipher** (matriks $5 \times 5$, I/J digabung)
   - **Hill Cipher** (matriks $n \times n$ per blok)
   - **Permutation Cipher** (permutasi $1 \dots m$ per blok)
   - **One-Time Pad (OTP)** (kunci dari file huruf acak sepanjang pesan)

2. **Dua Mode Input:**
   - **Mode Teks:** memproses alfabet A–Z. Karakter non-huruf diabaikan. Cipherteks dapat diformat *tanpa spasi* atau *kelompok 5 huruf*.
   - **Mode File:** membaca dan mengenkripsi seluruh byte file sembarang (termasuk header file) dengan aritmetika modulo 256. Hasil disimpan sebagai `.dat` dengan metadata magic `PYCF` untuk pemulihan nama & ekstensi asli secara otomatis saat didekripsi.

3. **Fitur Tambahan:**
   - Pembangkit file kunci OTP acak (default 50.000 huruf)
   - Mode Terang / Gelap (Light / Dark Theme)
   - Simpan hasil plaintext / ciphertext ke file `.txt`

---

## Cara Menjalankan

1. **Install Dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Jalankan Aplikasi:**
   ```bash
   python chiper_app.py
   ```
   Akses di browser: `http://127.0.0.1:5000`

---

## Cara Menjalankan Tes

```bash
python -m pytest
```

---

## Struktur Proyek

```
Tugas Kelompok/
├── ciphers.py          # Logika 8 cipher klasik (mod 26 & mod 256)
├── chiper_app.py       # Server Flask & route API (/api/text, /api/file, /api/genkey)
├── templates/
│   └── index.html      # Antarmuka web
├── static/
│   ├── style.css       # Styling responsif & tema terang/gelap
│   └── app.js          # Logika frontend & handler API
├── test_ciphers.py     # 45 unit test logika cipher (round-trip, vektor klasik)
├── test_app.py        # 14 integration test route & UI Flask (total 59 tes)
├── requirements.txt
└── README.md
```
