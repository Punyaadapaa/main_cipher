"""
Aplikasi Kriptografi Klasik (GUI Web, Flask)
Jalankan:  pip install flask  &&  python chiper_app.py   ->  buka http://127.0.0.1:5000

Mode TEKS : alfabet 26 huruf (A-Z). Karakter non-huruf dibuang.
Mode FILE : semua byte (termasuk header) diproses dengan versi mod 256 dari cipher yang sama.
Struktur  : ciphers.py (logika cipher) · templates/ + static/ (antarmuka) · file ini (route).
"""
import io, secrets, struct
from urllib.parse import quote
from flask import Flask, render_template, request, jsonify, send_file

from ciphers import KeyErr, run

app = Flask(__name__)
MAGIC = b"PYCF"


def keyfile():
    """Baca isi file kunci OTP yang diunggah (None jika tidak ada)."""
    f = request.files.get("keyfile")
    return f.read() if f and f.filename else None


@app.errorhandler(KeyErr)
def keyerr(e):
    """Kunci/input tidak valid -> pesan JSON untuk ditampilkan di UI."""
    return jsonify(error=str(e)), 400


@app.post("/api/text")
def api_text():
    """Enkripsi/dekripsi pesan teks (hanya huruf A-Z yang diproses)."""
    f = request.form
    mode = f.get("mode")
    cipher = f.get("cipher")
    if mode not in ("enc", "dec"):
        raise KeyErr("Mode tidak valid (enc/dec).")
    if not cipher:
        raise KeyErr("Pilih cipher terlebih dahulu.")
    enc = mode == "enc"
    huruf = [ord(c) - 65 for c in f.get("text", "").upper() if "A" <= c <= "Z"]
    if not huruf:
        raise KeyErr("Pesan tidak berisi huruf alfabet (A-Z).")
    out = "".join(chr(65 + v) for v in run(cipher, huruf, f.get("key", ""), enc, 26, keyfile()))
    if enc and f.get("group") == "5":
        out = " ".join(out[i:i + 5] for i in range(0, len(out), 5))
    return jsonify(result=out)


@app.post("/api/file")
def api_file():
    """Enkripsi/dekripsi file sembarang byte demi byte (mod 256).

    Cipherteks disimpan sebagai file .dat berisi: tanda pengenal (PYCF),
    nama file asli (agar ekstensi dipulihkan saat dekripsi), panjang
    plainteks (untuk membuang padding), lalu isi cipherteks.
    """
    f = request.form
    mode = f.get("mode")
    cipher = f.get("cipher")
    if mode not in ("enc", "dec"):
        raise KeyErr("Mode tidak valid (enc/dec).")
    if not cipher:
        raise KeyErr("Pilih cipher terlebih dahulu.")
    enc = mode == "enc"
    up = request.files.get("file")
    if not up:
        raise KeyErr("Pilih file terlebih dahulu.")
    raw = up.read()
    if enc:
        name = up.filename.encode()
        body = bytes(run(cipher, list(raw), f.get("key", ""), True, 256, keyfile()))
        blob = MAGIC + struct.pack(">H", len(name)) + name + struct.pack(">Q", len(raw)) + body
        fn = up.filename + ".dat"
    else:
        if raw[:4] != MAGIC:
            raise KeyErr("File bukan cipherteks dari aplikasi ini.")
        nl = struct.unpack(">H", raw[4:6])[0]
        fn = raw[6:6 + nl].decode()
        olen = struct.unpack(">Q", raw[6 + nl:14 + nl])[0]
        body = list(raw[14 + nl:])
        blob = bytes(run(cipher, body, f.get("key", ""), False, 256, keyfile()))[:olen]
    r = send_file(io.BytesIO(blob), as_attachment=True, download_name=fn)
    r.headers["X-Filename"] = quote(fn)
    r.headers["Access-Control-Expose-Headers"] = "X-Filename"
    return r


@app.get("/api/genkey")
def genkey():
    """Bangkitkan file kunci OTP berisi huruf acak (default 50.000 huruf)."""
    try:
        n = int(request.args.get("n", 50000))
    except ValueError:
        raise KeyErr("Jumlah huruf kunci harus berupa angka.")
    if n < 1:
        raise KeyErr("Jumlah huruf kunci minimal 1.")
    n = min(n, 5_000_000)
    txt = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(n))
    return send_file(io.BytesIO(txt.encode()), as_attachment=True, download_name="otp_key.txt")


@app.get("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=False)
