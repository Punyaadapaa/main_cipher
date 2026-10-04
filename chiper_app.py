"""
Aplikasi Kriptografi Klasik (GUI Web, Flask)
Jalankan:  pip install flask  &&  python cipher_app.py   ->  buka http://127.0.0.1:5000

Mode TEKS : alfabet 26 huruf (A-Z). Karakter non-huruf dibuang.
Mode FILE : semua byte (termasuk header) diproses dengan versi mod 256 dari cipher yang sama.
"""
import io, secrets, struct
from urllib.parse import quote
from flask import Flask, request, jsonify, send_file

from ciphers import KeyErr, run

app = Flask(__name__)
MAGIC = b"PYCF"


def keyfile():
    f = request.files.get("keyfile")
    return f.read() if f and f.filename else None


@app.errorhandler(KeyErr)
def keyerr(e):
    return jsonify(error=str(e)), 400


@app.post("/api/text")
def api_text():
    f = request.form
    enc = f["mode"] == "enc"
    data = [ord(c) - 65 for c in f.get("text", "").upper() if "A" <= c <= "Z"]
    out = "".join(chr(65 + v) for v in run(f["cipher"], data, f.get("key", ""), enc, 26, keyfile()))
    if enc and f.get("group") == "5":
        out = " ".join(out[i:i + 5] for i in range(0, len(out), 5))
    return jsonify(result=out)


@app.post("/api/file")
def api_file():
    f = request.form
    enc = f["mode"] == "enc"
    up = request.files.get("file")
    if not up:
        raise KeyErr("Pilih file terlebih dahulu.")
    raw = up.read()
    if enc:
        name = up.filename.encode()
        body = bytes(run(f["cipher"], list(raw), f.get("key", ""), True, 256, keyfile()))
        blob = MAGIC + struct.pack(">H", len(name)) + name + struct.pack(">Q", len(raw)) + body
        fn = up.filename + ".dat"
    else:
        if raw[:4] != MAGIC:
            raise KeyErr("File bukan cipherteks dari aplikasi ini.")
        nl = struct.unpack(">H", raw[4:6])[0]
        fn = raw[6:6 + nl].decode()
        olen = struct.unpack(">Q", raw[6 + nl:14 + nl])[0]
        body = list(raw[14 + nl:])
        blob = bytes(run(f["cipher"], body, f.get("key", ""), False, 256, keyfile()))[:olen]
    r = send_file(io.BytesIO(blob), as_attachment=True, download_name=fn)
    r.headers["X-Filename"] = quote(fn)
    r.headers["Access-Control-Expose-Headers"] = "X-Filename"
    return r


@app.get("/api/genkey")
def genkey():
    n = min(max(int(request.args.get("n", 50000)), 1), 5_000_000)
    txt = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(n))
    return send_file(io.BytesIO(txt.encode()), as_attachment=True, download_name="otp_key.txt")


PAGE = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Classic Ciphers</title>
<style>
:root{--bg:#f4f5f7;--card:#fff;--tx:#1d2330;--mut:#6b7385;--ac:#2f5bea;--bd:#d9dde5}
@media(prefers-color-scheme:dark){:root{--bg:#14171d;--card:#1e222b;--tx:#e6e9f0;--mut:#8d95a8;--ac:#6c8cff;--bd:#343a48}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px system-ui,sans-serif}
main{max-width:860px;margin:auto;padding:20px}h1{font-size:22px;margin:0 0 14px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px;margin-bottom:14px}
label{display:block;font-weight:600;margin:10px 0 4px}.row{display:flex;gap:12px;flex-wrap:wrap}.row>div{flex:1;min-width:200px}
input,select,textarea{width:100%;padding:8px;border:1px solid var(--bd);border-radius:6px;background:var(--bg);color:var(--tx);font:inherit}
textarea{min-height:110px;font-family:ui-monospace,monospace}
button{padding:8px 16px;border:0;border-radius:6px;background:var(--ac);color:#fff;font:inherit;cursor:pointer;margin:10px 8px 0 0}
button.s{background:transparent;color:var(--ac);border:1px solid var(--ac)}
.tabs button{margin:0 6px 0 0}.hint{color:var(--mut);font-size:13px;margin-top:4px}.err{color:#d33;margin-top:8px}
label.i{display:inline;font-weight:400;margin-right:14px}label.i input{width:auto}
</style></head><body><main><h1>🔐 Classic Ciphers (Shift · Substitution · Affine · Vigenere · Hill · Permutation · OTP)</h1>
<div class="card"><div class="row">
<div><label>Cipher</label><select id="cipher">
<option value="shift">Shift Cipher</option><option value="substitution">Substitution Cipher</option>
<option value="affine">Affine Cipher</option><option value="vigenere">Vigenere Cipher</option>
<option value="hill">Hill Cipher</option><option value="permutation">Permutation Cipher</option>
<option value="otp">One-Time Pad</option></select></div>
<div><label>Operasi</label><select id="mode"><option value="enc">Enkripsi</option><option value="dec">Dekripsi</option></select></div></div>
<label>Kunci</label><input id="key"><div class="hint" id="hint"></div>
<div id="kf" style="display:none"><label>File kunci OTP (huruf acak)</label><input type="file" id="keyfile">
<button class="s" onclick="location='/api/genkey?n=50000'">Bangkitkan kunci acak 50.000 huruf</button></div></div>
<div class="card"><div class="tabs"><button id="t1" onclick="tab(1)">Teks</button><button id="t2" class="s" onclick="tab(2)">File</button></div>
<div id="p1"><label>Pesan</label><textarea id="text"></textarea>
<label>Format cipherteks</label><label class="i"><input type="radio" name="g" value="0" checked> Tanpa spasi</label>
<label class="i"><input type="radio" name="g" value="5"> Kelompok 5 huruf</label><br>
<button onclick="doText()">Proses</button><button class="s" onclick="saveOut()">Simpan hasil ke file</button>
<label>Hasil</label><textarea id="out" readonly></textarea></div>
<div id="p2" style="display:none"><label>File (apa saja, termasuk biner)</label><input type="file" id="file">
<div class="hint">Enkripsi menghasilkan file .dat (nama asli tersimpan di dalamnya). Dekripsi otomatis memulihkan nama &amp; ekstensi asli.</div>
<button onclick="doFile()">Proses &amp; Unduh</button></div>
<div class="err" id="err"></div></div>
<script>
const $=id=>document.getElementById(id);
const H={shift:"Satu angka, mis. 3",substitution:"26 huruf berbeda (permutasi alfabet), mis. QWERTYUIOPASDFGHJKLZXCVBNM",
affine:"Dua angka 'a b'; a relatif prima dengan 26 (file: 256), mis. 7 3",vigenere:"Kata kunci bebas panjang, mis. LEMON",
hill:"Matriks n×n baris demi baris, mis. 3 3 2 5 (2×2). Harus punya balikan mod 26 (file: mod 256)",
permutation:"Permutasi 1..m, mis. 3 1 2 (blok m huruf)",otp:"Unggah file kunci. Jika kosong, isi kolom kunci ini dengan huruf kunci."};
function upd(){$("hint").textContent=H[$("cipher").value];$("kf").style.display=$("cipher").value=="otp"?"block":"none"}
$("cipher").onchange=upd;upd();
function tab(n){$("p1").style.display=n==1?"block":"none";$("p2").style.display=n==2?"block":"none";
$("t1").className=n==1?"":"s";$("t2").className=n==2?"":"s";$("err").textContent=""}
function fd(){const f=new FormData();f.append("cipher",$("cipher").value);f.append("mode",$("mode").value);
f.append("key",$("key").value);const k=$("keyfile").files[0];if(k)f.append("keyfile",k);return f}
async function doText(){$("err").textContent="";const f=fd();f.append("text",$("text").value);
f.append("group",document.querySelector("input[name=g]:checked").value);
const r=await fetch("/api/text",{method:"POST",body:f});const j=await r.json();
if(!r.ok){$("err").textContent=j.error;return}$("out").value=j.result}
function dl(blob,name){const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;a.click()}
function saveOut(){dl(new Blob([$("out").value],{type:"text/plain"}),$("mode").value=="enc"?"cipherteks.txt":"plainteks.txt")}
async function doFile(){$("err").textContent="";const f=fd();const u=$("file").files[0];if(!u){$("err").textContent="Pilih file.";return}
f.append("file",u);const r=await fetch("/api/file",{method:"POST",body:f});
if(!r.ok){$("err").textContent=(await r.json()).error;return}
dl(await r.blob(),decodeURIComponent(r.headers.get("X-Filename")))}
</script></main></body></html>"""


@app.get("/")
def index():
    return PAGE


if __name__ == "__main__":
    app.run(debug=False)