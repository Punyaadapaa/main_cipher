"""
Logika 8 cipher klasik untuk aplikasi kriptografi.

Semua fungsi bekerja pada daftar bilangan bulat:
  - mode teks : mod 26, A=0 .. Z=25 (huruf lain sudah dibuang di route Flask)
  - mode file : mod 256, setiap byte file dianggap elemen Z_256
Setiap cipher punya fungsi sendiri; run() memilih fungsi sesuai nama.
"""
import math
import random
import re


class KeyErr(Exception):
    """Dilempar saat kunci tidak valid — pesannya ditampilkan ke pengguna."""


def angka(s):
    """Convert key string '3 1 4, 2' into list [3, 1, 4, 2]."""
    try:
        return [int(x) for x in re.split(r"[\s,;]+", s.strip()) if x]
    except ValueError:
        raise KeyErr("Key must be numbers (space/comma separated).")


def determinan(m):
    """Determinan matriks persegi (rekursif, ekspansi kofaktor baris pertama)."""
    if len(m) == 1:
        return m[0][0]
    return sum((-1) ** j * m[0][j] * determinan([r[:j] + r[j + 1:] for r in m[1:]])
               for j in range(len(m)))


def matriks_balikan(m, mod):
    """
    Balikan matriks modulo (dipakai dekripsi Hill).

    K^-1 = adj(K) * det(K)^-1 (mod mod); ada hanya jika gcd(det, mod) = 1.
    """
    n = len(m)
    d = determinan(m) % mod
    if math.gcd(d, mod) != 1:
        raise KeyErr(f"Key matrix has no inverse mod {mod} (det = {d}).")
    di = pow(d, -1, mod)
    if n == 1:
        return [[di]]
    adj = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            minor = [r[:j] + r[j + 1:] for k, r in enumerate(m) if k != i]
            adj[j][i] = (-1) ** (i + j) * determinan(minor)
    return [[(di * adj[i][j]) % mod for j in range(n)] for i in range(n)]


# ---------------------------------------------------------------------------
# Padding blok (Hill/Permutation).
#
# Mode teks memakai skema ala PKCS#7: panjang yang bukan kelipatan n dipad
# sebanyak p (1..n) buah karakter bernilai (p-1), dan bila panjang sudah
# kelipatan n tetap ditambah satu blok penuh. Karena jumlah padding ikut
# tersimpan di cipherteks, dekripsi bisa membuangnya dengan pasti (tidak
# menebak), sehingga plainteks berakhiran 'X' betulan tidak ikut terpotong.
#
# Mode file memakai byte 0 sebagai padding; panjang asli disimpan di header
# .dat sehingga route tinggal memotong hasil dekripsi.
# ---------------------------------------------------------------------------

def pad_blok(data, n, mod):
    if mod == 26:
        if n > 26:
            raise KeyErr("Block size too large for text mode (max 26).")
        p = n - (len(data) % n)
        return data + [p - 1] * p
    return data + [0] * (-len(data) % n)


def unpad_blok(out, n, mod):
    if mod != 26:
        return out
    if n > 26 or not out:
        raise KeyErr("Invalid ciphertext for text mode.")
    p = out[-1] + 1
    if p > n or p > len(out) or any(x != out[-1] for x in out[-p:]):
        raise KeyErr("Invalid padding — wrong key or corrupted ciphertext.")
    return out[:-p]


# ---------------------------------------------------------------------------
# Tujuh cipher. Kontrak sama: (data, key, enc, mod, keybytes=None) -> list int
# ---------------------------------------------------------------------------

def shift(data, key, enc, mod, keybytes=None):
    """Shift (Caesar): C = (P + k) mod 26."""
    k = angka(key)
    if len(k) != 1:
        raise KeyErr("Shift: enter a single number.")
    geser = k[0] if enc else -k[0]
    return [(x + geser) % mod for x in data]


def affine(data, key, enc, mod, keybytes=None):
    """Affine: C = (a*P + b) mod 26. Decrypt: P = a^-1 * (C - b).
    a must be coprime with mod to have an inverse."""
    k = angka(key)
    if len(k) != 2:
        raise KeyErr("Affine: enter two numbers 'a b'.")
    a, b = k
    if math.gcd(a, mod) != 1:
        raise KeyErr(f"Affine: a must be coprime with {mod}.")
    if enc:
        return [(a * x + b) % mod for x in data]
    ai = pow(a, -1, mod)
    return [(ai * (x - b)) % mod for x in data]


def vigenere(data, key, enc, mod, keybytes=None):
    """Vigenere: C = (P + k_i) mod 26, key repeated along the message.
    Text mode uses letters; file mode uses bytes."""
    teks = mod == 26
    if teks:
        kk = [ord(c) - 65 for c in key.upper() if "A" <= c <= "Z"]
        if not kk:
            raise KeyErr("Vigenere: key is empty (text mode requires letters).")
    else:
        kk = list(key.encode())
        if not kk:
            raise KeyErr("Vigenere: key is empty (file mode requires at least one character).")
    tanda = 1 if enc else -1
    return [(x + tanda * kk[i % len(kk)]) % mod for i, x in enumerate(data)]


def substitution(data, key, enc, mod, keybytes=None):
    """Substitution monoalfabet: huruf diganti sesuai tabel permutasi 26 huruf.
    Mode file: tabel dibangkitkan acak dari seed = string kunci (deterministik,
    sehingga dekripsi bisa mengulang tabel yang sama)."""
    teks = mod == 26
    if teks:
        k = [ord(c) - 65 for c in key.upper() if "A" <= c <= "Z"]
        if sorted(k) != list(range(26)):
            raise KeyErr("Substitution: key must be a permutation of 26 distinct letters.")
    else:
        if not key:
            raise KeyErr("Substitution: key must not be empty (file mode uses it as the table seed).")
        k = list(range(256))
        random.Random(key).shuffle(k)
    if not enc:
        balikan = [0] * mod
        for i, v in enumerate(k):
            balikan[v] = i
        k = balikan
    return [k[x] for x in data]


def hill(data, key, enc, mod, keybytes=None):
    """Hill: split message into blocks of n letters, C = K * P (mod 26) per block.
    Decrypt uses K^-1. Text mode pads in a PKCS#7-like scheme; file mode
    pads with byte 0 (original length stored in the .dat header)."""
    k = angka(key)
    n = math.isqrt(len(k))
    if n == 0 or n * n != len(k):
        raise KeyErr("Hill: key length must be a perfect square (4, 9, 16, ...).")
    m = [[v % mod for v in k[i * n:(i + 1) * n]] for i in range(n)]
    mi = matriks_balikan(m, mod)  # selalu dicek: kunci buruk ketahuan saat enkripsi juga
    mat = m if enc else mi
    if enc:
        data = pad_blok(data, n, mod)
    elif len(data) % n:
        raise KeyErr(f"Hill: ciphertext length must be a multiple of {n}.")
    out = []
    for i in range(0, len(data), n):
        blok = data[i:i + n]
        out += [sum(mat[r][c] * blok[c] for c in range(n)) % mod for r in range(n)]
    if not enc:
        out = unpad_blok(out, n, mod)
    return out


def permutation(data, key, enc, mod, keybytes=None):
    """Permutation cipher: urus ulang huruf dalam blok sepanjang m
    sesuai kunci permutasi 1..m (mis. '3 1 4 2')."""
    p = angka(key)
    m = len(p)
    if m == 0 or sorted(p) != list(range(1, m + 1)):
        raise KeyErr("Permutation: key must be a permutation 1..m, e.g. '3 1 4 2'.")
    if enc:
        data = pad_blok(data, m, mod)
    elif len(data) % m:
        raise KeyErr(f"Permutation: ciphertext length must be a multiple of {m}.")
    out = []
    for i in range(0, len(data), m):
        blok = data[i:i + m]
        if enc:
            out += [blok[p[j] - 1] for j in range(m)]
        else:
            res = [0] * m
            for j in range(m):
                res[p[j] - 1] = blok[j]
            out += res
    if not enc:
        out = unpad_blok(out, m, mod)
    return out


def otp(data, key, enc, mod, keybytes=None):
    """One-time pad: C = (P + k_i) mod 26 dengan kunci sepanjang pesan.
    Kunci dibaca dari file huruf acak (keybytes); sisa kunci tidak terpakai
    dibiarkan begitu saja."""
    kb = keybytes if keybytes else key.encode()
    teks = mod == 26
    if teks:
        kk = [b - 65 for b in kb.upper() if 65 <= b <= 90]
    else:
        kk = list(kb)
    if len(kk) < len(data):
        raise KeyErr(f"OTP: key ({len(kk)}) is shorter than message ({len(data)}).")
    tanda = 1 if enc else -1
    return [(x + tanda * kk[i]) % mod for i, x in enumerate(data)]


def buang_pengisi_playfair(huruf):
    """Buang huruf pengisi 'X' yang disisipkan Playfair saat enkripsi:
    (a) 'X' di antara dua huruf kembar (mis. LXL -> LL) akibat aturan
        huruf dobel, (b) satu 'X' di ujung hasil padding panjang ganjil."""
    res = []
    i = 0
    while i < len(huruf):
        if i + 2 < len(huruf) and huruf[i + 1] == "X" and huruf[i + 2] == huruf[i]:
            res += [huruf[i], huruf[i + 2]]
            i += 3
        else:
            res.append(huruf[i])
            i += 1
    if res and res[-1] == "X":
        res.pop()
    return res


def playfair(data, key, enc, mod, keybytes=None):
    """Playfair Cipher 5x5: pasangan huruf (digraph), I dan J digabung.
    Hanya mendukung mode teks (alfabet 26 huruf)."""
    if mod != 26:
        raise KeyErr("Playfair supports text mode (alphabet) only, not binary files.")
    kata = [c for c in key.upper() if "A" <= c <= "Z"]
    if not kata:
        raise KeyErr("Playfair: key must be an alphabetic keyword (e.g. MONARCHY).")
    
    mat_list = []
    for c in kata:
        c = "I" if c == "J" else c
        if c not in mat_list:
            mat_list.append(c)
    for c in "ABCDEFGHIKLMNOPQRSTUVWXYZ":
        if c not in mat_list:
            mat_list.append(c)
            
    mat = [mat_list[i * 5:(i + 1) * 5] for i in range(5)]
    pos = {mat[r][c]: (r, c) for r in range(5) for c in range(5)}
    
    huruf = ["I" if chr(65 + v) == "J" else chr(65 + v) for v in data]
    tanda = 1 if enc else -1
    
    def proses_pasang(a, b):
        r1, c1 = pos[a]
        r2, c2 = pos[b]
        if r1 == r2:
            return [mat[r1][(c1 + tanda) % 5], mat[r2][(c2 + tanda) % 5]]
        if c1 == c2:
            return [mat[(r1 + tanda) % 5][c1], mat[(r2 + tanda) % 5][c2]]
        return [mat[r1][c2], mat[r2][c1]]
    
    out = []
    if enc:
        i = 0
        while i < len(huruf):
            a = huruf[i]
            if i + 1 < len(huruf):
                b = huruf[i + 1]
                if a == b:
                    pasang = (a, "X")
                    i += 1
                else:
                    pasang = (a, b)
                    i += 2
            else:
                pasang = (a, "X")
                i += 1
            out += proses_pasang(pasang[0], pasang[1])
    else:
        if len(huruf) % 2 != 0:
            raise KeyErr("Playfair: ciphertext length must be even for decryption.")
        for i in range(0, len(huruf), 2):
            out += proses_pasang(huruf[i], huruf[i + 1])
        out = buang_pengisi_playfair(out)

    return [ord(c) - 65 for c in out]


CIPHERS = {
    "shift": shift,
    "substitution": substitution,
    "affine": affine,
    "vigenere": vigenere,
    "hill": hill,
    "permutation": permutation,
    "otp": otp,
    "playfair": playfair,
}


def run(name, data, key, enc, mod, keybytes=None):
    """Pilih cipher sesuai nama; dipanggil route Flask."""
    fungsi = CIPHERS.get(name)
    if fungsi is None:
        raise KeyErr("Unknown cipher.")
    return fungsi(data, key, enc, mod, keybytes)
