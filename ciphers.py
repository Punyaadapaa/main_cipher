"""
Logika 7 cipher klasik untuk aplikasi kriptografi.

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
    """Ubah string kunci '3 1 4, 2' menjadi daftar [3, 1, 4, 2]."""
    try:
        return [int(x) for x in re.split(r"[\s,;]+", s.strip()) if x]
    except ValueError:
        raise KeyErr("Kunci harus berupa angka (dipisah spasi/koma).")


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
        raise KeyErr(f"Matriks kunci tidak punya balikan mod {mod} (det = {d}).")
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
# Tujuh cipher. Kontrak sama: (data, key, enc, mod, keybytes=None) -> list int
# ---------------------------------------------------------------------------

def shift(data, key, enc, mod, keybytes=None):
    """Shift (Caesar): C = (P + k) mod 26."""
    k = angka(key)
    if len(k) != 1:
        raise KeyErr("Shift: masukkan 1 angka.")
    geser = k[0] if enc else -k[0]
    return [(x + geser) % mod for x in data]


def affine(data, key, enc, mod, keybytes=None):
    """Affine: C = (a*P + b) mod 26. Dekripsi: P = a^-1 * (C - b).
    a harus relatif prima dengan mod agar punya balikan."""
    k = angka(key)
    if len(k) != 2:
        raise KeyErr("Affine: masukkan 2 angka 'a b'.")
    a, b = k
    if math.gcd(a, mod) != 1:
        raise KeyErr(f"Affine: a harus relatif prima dengan {mod}.")
    if enc:
        return [(a * x + b) % mod for x in data]
    ai = pow(a, -1, mod)
    return [(ai * (x - b)) % mod for x in data]


def vigenere(data, key, enc, mod, keybytes=None):
    """Vigenere: C = (P + k_i) mod 26, kunci diulang sepanjang pesan.
    Mode teks memakai huruf kunci; mode file memakai byte kunci."""
    teks = mod == 26
    if teks:
        kk = [ord(c) - 65 for c in key.upper() if "A" <= c <= "Z"]
        if not kk:
            raise KeyErr("Vigenere: kunci kosong (teks mode butuh huruf).")
    else:
        kk = list(key.encode())
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
            raise KeyErr("Substitusi: kunci harus permutasi 26 huruf berbeda.")
    else:
        k = list(range(256))
        random.Random(key).shuffle(k)
    if not enc:
        balikan = [0] * mod
        for i, v in enumerate(k):
            balikan[v] = i
        k = balikan
    return [k[x] for x in data]


def hill(data, key, enc, mod, keybytes=None):
    """Hill: pecah pesan jadi blok n huruf, C = K * P (mod 26) per blok.
    Dekripsi memakai K^-1. Sisa panjang dipad 'X' (teks) / byte 0 (file)."""
    k = angka(key)
    n = math.isqrt(len(k))
    if n == 0 or n * n != len(k):
        raise KeyErr("Hill: jumlah angka kunci harus kuadrat sempurna (4, 9, 16, ...).")
    m = [[v % mod for v in k[i * n:(i + 1) * n]] for i in range(n)]
    mi = matriks_balikan(m, mod)  # selalu dicek: kunci buruk ketahuan saat enkripsi juga
    mat = m if enc else mi
    teks = mod == 26
    if enc:
        data = data + [23 if teks else 0] * (-len(data) % n)
    elif len(data) % n:
        raise KeyErr(f"Hill: panjang cipherteks harus kelipatan {n}.")
    out = []
    for i in range(0, len(data), n):
        blok = data[i:i + n]
        out += [sum(mat[r][c] * blok[c] for c in range(n)) % mod for r in range(n)]
    if not enc and teks:
        # buang padding 'X' (23) yang ditambahkan saat enkripsi (maks. n-1 buah)
        for _ in range(n - 1):
            if out and out[-1] == 23:
                out.pop()
    return out


def permutation(data, key, enc, mod, keybytes=None):
    """Permutation cipher: urus ulang huruf dalam blok sepanjang m
    sesuai kunci permutasi 1..m (mis. '3 1 4 2')."""
    p = angka(key)
    m = len(p)
    if m == 0 or sorted(p) != list(range(1, m + 1)):
        raise KeyErr("Permutasi: kunci harus permutasi 1..m, mis. '3 1 4 2'.")
    teks = mod == 26
    if enc:
        data = data + [23 if teks else 0] * (-len(data) % m)
    elif len(data) % m:
        raise KeyErr(f"Permutasi: panjang cipherteks harus kelipatan {m}.")
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
    if not enc and teks:
        # buang padding 'X' (23) yang ditambahkan saat enkripsi (maks. m-1 buah)
        for _ in range(m - 1):
            if out and out[-1] == 23:
                out.pop()
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
        raise KeyErr(f"OTP: kunci ({len(kk)}) lebih pendek dari pesan ({len(data)}).")
    tanda = 1 if enc else -1
    return [(x + tanda * kk[i]) % mod for i, x in enumerate(data)]


def playfair(data, key, enc, mod, keybytes=None):
    """Playfair Cipher 5x5: pasangan huruf (digraph), I dan J digabung.
    Hanya mendukung mode teks (alfabet 26 huruf)."""
    if mod != 26:
        raise KeyErr("Playfair hanya mendukung mode teks (alfabet), bukan file biner.")
    kata = [c for c in key.upper() if "A" <= c <= "Z"]
    if not kata:
        raise KeyErr("Playfair: kunci harus berupa kata kunci alfabet (mis. MONARCHY).")
    
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
            raise KeyErr("Playfair: panjang cipherteks harus genap untuk didekripsi.")
        for i in range(0, len(huruf), 2):
            out += proses_pasang(huruf[i], huruf[i + 1])
            
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
        raise KeyErr("Cipher tidak dikenal.")
    return fungsi(data, key, enc, mod, keybytes)
