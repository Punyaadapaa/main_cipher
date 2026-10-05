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
app.config["TEMPLATES_AUTO_RELOAD"] = True  # template selalu dibaca ulang (dev)
MAGIC = b"PYCF"


def keyfile():
    """Read OTP keyfile (None if not uploaded)."""
    f = request.files.get("keyfile")
    return f.read() if f and f.filename else None


@app.errorhandler(KeyErr)
def keyerr(e):
    """Invalid key/input -> JSON error message for UI."""
    return jsonify(error=str(e)), 400


@app.post("/api/text")
def api_text():
    """Encrypt/decrypt text (A-Z only, others discarded)."""
    f = request.form
    mode = f.get("mode")
    cipher = f.get("cipher")
    if mode not in ("enc", "dec"):
        raise KeyErr("Mode must be 'enc' or 'dec'.")
    if not cipher:
        raise KeyErr("Select a cipher first.")
    enc = mode == "enc"
    letters = [ord(c) - 65 for c in f.get("text", "").upper() if "A" <= c <= "Z"]
    if not letters:
        raise KeyErr("Message must contain at least one A-Z letter.")
    out = "".join(chr(65 + v) for v in run(cipher, letters, f.get("key", ""), enc, 26, keyfile()))
    if enc and f.get("group") == "5":
        out = " ".join(out[i:i + 5] for i in range(0, len(out), 5))
    return jsonify(result=out)


@app.post("/api/file")
def api_file():
    """Encrypt/decrypt file byte-by-byte (mod 256).
    
    Ciphertext stored as .dat: identifier (PYCF), original filename (for restore), plaintext length (for padding removal), ciphertext.
    """
    f = request.form
    mode = f.get("mode")
    cipher = f.get("cipher")
    if mode not in ("enc", "dec"):
        raise KeyErr("Mode must be 'enc' or 'dec'.")
    if not cipher:
        raise KeyErr("Select a cipher first.")
    enc = mode == "enc"
    up = request.files.get("file")
    if not up:
        raise KeyErr("Please select a file first.")
    raw = up.read()
    if enc:
        name = up.filename.encode()
        body = bytes(run(cipher, list(raw), f.get("key", ""), True, 256, keyfile()))
        blob = MAGIC + struct.pack(">H", len(name)) + name + struct.pack(">Q", len(raw)) + body
        fn = up.filename + ".dat"
    else:
        if raw[:4] != MAGIC:
            raise KeyErr("File is not ciphertext from this app.")
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
        raise KeyErr("Key letter count must be a number.")
    if n < 1:
        raise KeyErr("Key letter count must be at least 1.")
    n = min(n, 5_000_000)
    txt = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(n))
    return send_file(io.BytesIO(txt.encode()), as_attachment=True, download_name="otp_key.txt")


@app.get("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=False)
