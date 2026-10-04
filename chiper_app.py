"""
Aplikasi Kriptografi Klasik (GUI Web, Flask)
Jalankan:  pip install flask  &&  python cipher_app.py   ->  buka http://127.0.0.1:5000

Mode TEKS : alfabet 26 huruf (A-Z). Karakter non-huruf dibuang.
Mode FILE : semua byte (termasuk header) diproses dengan versi mod 256 dari cipher yang sama.
"""
import io, math, random, re, secrets, struct
from urllib.parse import quote
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)
MAGIC = b"PYCF"


class KeyErr(Exception):
    pass


def ints(s):
    try:
        return [int(x) for x in re.split(r"[\s,;]+", s.strip()) if x]
    except ValueError:
        raise KeyErr("Kunci harus berupa angka (dipisah spasi/koma).")


def det(m):
    if len(m) == 1:
        return m[0][0]
    return sum((-1) ** j * m[0][j] * det([r[:j] + r[j + 1:] for r in m[1:]]) for j in range(len(m)))


def inv_matrix(m, M):
    n = len(m)
    d = det(m) % M
    if math.gcd(d, M) != 1:
        raise KeyErr(f"Matriks kunci tidak punya balikan mod {M} (det = {d}).")
    di = pow(d, -1, M)
    if n == 1:
        return [[di]]
    adj = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            minor = [r[:j] + r[j + 1:] for k, r in enumerate(m) if k != i]
            adj[j][i] = (-1) ** (i + j) * det(minor)
    return [[(di * adj[i][j]) % M for j in range(n)] for i in range(n)]


def run(name, data, key, enc, M, keybytes=None):
    """data: list int (0..M-1). Mengembalikan list int hasil."""
    txt = M == 26
    sg = 1 if enc else -1
    if name == "shift":
        k = ints(key)
        if len(k) != 1:
            raise KeyErr("Shift: masukkan 1 angka.")
        return [(x + sg * k[0]) % M for x in data]

    if name == "affine":
        k = ints(key)
        if len(k) != 2:
            raise KeyErr("Affine: masukkan 2 angka 'a b'.")
        a, b = k
        if math.gcd(a, M) != 1:
            raise KeyErr(f"Affine: a harus relatif prima dengan {M}.")
        if enc:
            return [(a * x + b) % M for x in data]
        ai = pow(a, -1, M)
        return [(ai * (x - b)) % M for x in data]

    if name == "vigenere":
        kk = [ord(c) - 65 for c in key.upper() if "A" <= c <= "Z"] if txt else list(key.encode())
        if not kk:
            raise KeyErr("Vigenere: kunci kosong (teks mode butuh huruf).")
        return [(x + sg * kk[i % len(kk)]) % M for i, x in enumerate(data)]

    if name == "substitution":
        if txt:
            k = [ord(c) - 65 for c in key.upper() if "A" <= c <= "Z"]
            if sorted(k) != list(range(26)):
                raise KeyErr("Substitusi: kunci harus permutasi 26 huruf berbeda.")
        else:
            k = list(range(256))
            random.Random(key).shuffle(k)
        if not enc:
            inv = [0] * M
            for i, v in enumerate(k):
                inv[v] = i
            k = inv
        return [k[x] for x in data]

    if name == "hill":
        k = ints(key)
        n = math.isqrt(len(k))
        if n == 0 or n * n != len(k):
            raise KeyErr("Hill: jumlah angka kunci harus kuadrat sempurna (4, 9, 16, ...).")
        m = [[v % M for v in k[i * n:(i + 1) * n]] for i in range(n)]
        mi = inv_matrix(m, M)
        mat = m if enc else mi
        if enc:
            data = data + [23 if txt else 0] * (-len(data) % n)  # pad 'X' / 0
        elif len(data) % n:
            raise KeyErr(f"Hill: panjang cipherteks harus kelipatan {n}.")
        out = []
        for i in range(0, len(data), n):
            blk = data[i:i + n]
            out += [sum(mat[r][c] * blk[c] for c in range(n)) % M for r in range(n)]
        return out

    if name == "permutation":
        p = ints(key)
        m = len(p)
        if m == 0 or sorted(p) != list(range(1, m + 1)):
            raise KeyErr("Permutasi: kunci harus permutasi 1..m, mis. '3 1 4 2'.")
        if enc:
            data = data + [23 if txt else 0] * (-len(data) % m)
        elif len(data) % m:
            raise KeyErr(f"Permutasi: panjang cipherteks harus kelipatan {m}.")
        out = []
        for i in range(0, len(data), m):
            blk = data[i:i + m]
            if enc:
                out += [blk[p[j] - 1] for j in range(m)]
            else:
                res = [0] * m
                for j in range(m):
                    res[p[j] - 1] = blk[j]
                out += res
        return out

    if name == "otp":
        kb = keybytes if keybytes else key.encode()
        kk = [b - 65 for b in kb.upper() if 65 <= b <= 90] if txt else list(kb)
        if len(kk) < len(data):
            raise KeyErr(f"OTP: kunci ({len(kk)}) lebih pendek dari pesan ({len(data)}).")
        return [(x + sg * kk[i]) % M for i, x in enumerate(data)]

    raise KeyErr("Cipher tidak dikenal.")


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