"""
Tes ciphers.py: vektor klasik tiap cipher, round-trip teks (mod 26),
round-trip byte (mod 256), dan penolakan kunci tidak valid.
"""
import os

import pytest

from ciphers import KeyErr, run


def A(s):
    """Teks -> daftar angka 0..25 (hanya huruf, seperti mode teks aplikasi)."""
    return [ord(c) - 65 for c in s.upper() if "A" <= c <= "Z"]


def S(vals):
    """Daftar angka 0..25 -> teks."""
    return "".join(chr(65 + v) for v in vals)


# ---------- vektor klasik (mode teks, mod 26) ----------

def test_shift_vektor_klasik():
    out = run("shift", A("HELLO"), "3", True, 26)
    assert S(out) == "KHOOR"
    assert S(run("shift", out, "3", False, 26)) == "HELLO"


def test_affine_vektor_klasik():
    # Contoh standar: a=5, b=8
    out = run("affine", A("AFFINECIPHER"), "5 8", True, 26)
    assert S(out) == "IHHWVCSWFRCP"
    assert S(run("affine", out, "5 8", False, 26)) == "AFFINECIPHER"


def test_vigenere_vektor_klasik():
    # Contoh standar: kunci LEMON
    out = run("vigenere", A("ATTACKATDAWN"), "LEMON", True, 26)
    assert S(out) == "LXFOPVEFRNHR"
    assert S(run("vigenere", out, "LEMON", False, 26)) == "ATTACKATDAWN"


def test_substitution_vektor_klasik():
    kunci = "QWERTYUIOPASDFGHJKLZXCVBNM"
    out = run("substitution", A("ABCDXYZ"), kunci, True, 26)
    assert S(out) == "QWERBNM"
    assert S(run("substitution", out, kunci, False, 26)) == "ABCDXYZ"


def test_hill_vektor_2x2():
    # Matriks [[3,3],[2,5]], "HELP" -> "HIAT"
    out = run("hill", A("HELP"), "3 3 2 5", True, 26)
    assert S(out) == "HIAT"
    assert S(run("hill", out, "3 3 2 5", False, 26)) == "HELP"


def test_hill_vektor_3x3():
    # Matriks GYBNQKURP (Wikipedia), "ACT" -> "POH"
    out = run("hill", A("ACT"), "6 24 1 13 16 10 20 17 15", True, 26)
    assert S(out) == "POH"
    assert S(run("hill", out, "6 24 1 13 16 10 20 17 15", False, 26)) == "ACT"


def test_permutation_vektor_klasik():
    out = run("permutation", A("ABCD"), "3 1 4 2", True, 26)
    assert S(out) == "CADB"
    assert S(run("permutation", out, "3 1 4 2", False, 26)) == "ABCD"


def test_otp_vektor_klasik():
    # Contoh standar: kunci XMCKL, "HELLO" -> "EQNVZ"
    out = run("otp", A("HELLO"), "", True, 26, keybytes=b"XMCKL")
    assert S(out) == "EQNVZ"
    assert S(run("otp", out, "", False, 26, keybytes=b"XMCKL")) == "HELLO"


def test_playfair_vektor_klasik():
    # Key: MONARCHY, teks: INSTRUMENT (panjang genap, tanpa huruf dobel)
    out = run("playfair", A("INSTRUMENT"), "MONARCHY", True, 26)
    assert S(run("playfair", out, "MONARCHY", False, 26)) == "INSTRUMENT"


def test_playfair_huruf_j_menjadi_i():
    # Huruf J dipetakan ke I
    out = run("playfair", A("JUMP"), "KEYWORD", True, 26)
    assert S(run("playfair", out, "KEYWORD", False, 26)) == "IUMP"


def test_playfair_huruf_dobel_dan_ganjil():
    # "BALLOON" (7 huruf, ada LL dan OO) -> enkripsi menyisipkan X
    out = run("playfair", A("BALLOON"), "MONARCHY", True, 26)
    assert len(out) % 2 == 0
    # Dekripsi mengembalikan teks dengan X yang disisipkan
    dec = S(run("playfair", out, "MONARCHY", False, 26))
    assert "BA" in dec and "ON" in dec


# ---------- round-trip properti (mode teks) ----------

KUNCI_TEKS = {
    "shift": "7",
    "substitution": "QWERTYUIOPASDFGHJKLZXCVBNM",
    "affine": "5 8",
    "vigenere": "RAHASIA",
    "hill": "3 3 2 5",
    "permutation": "3 1 4 2",
}

PESAN = "SERANGANDIMULAISAATFAJAR"


@pytest.mark.parametrize("nama,kunci", KUNCI_TEKS.items())
def test_round_trip_teks(nama, kunci):
    out = run(nama, A(PESAN), kunci, True, 26)
    assert S(run(nama, out, kunci, False, 26)) == PESAN


def test_round_trip_teks_otp():
    kunci = (b"QWERTYUIOPASDFGHJKLZXCVBNM" * 4)
    out = run("otp", A(PESAN), "", True, 26, keybytes=kunci)
    assert S(run("otp", out, "", False, 26, keybytes=kunci)) == PESAN


# ---------- padding blok (Hill/Permutation) harus dibuang saat dekripsi ----------

def test_hill_padding_x_dibuang_saat_dekripsi():
    # 5 huruf, blok 2 -> enkripsi memad 1 'X'; dekripsi harus kembali 5 huruf
    out = run("hill", A("HELLO"), "3 3 2 5", True, 26)
    assert S(run("hill", out, "3 3 2 5", False, 26)) == "HELLO"


def test_permutation_padding_x_dibuang_saat_dekripsi():
    # 5 huruf, blok 4 -> enkripsi memad 3 'X'; dekripsi harus kembali 5 huruf
    out = run("permutation", A("HELLO"), "3 1 4 2", True, 26)
    assert S(run("permutation", out, "3 1 4 2", False, 26)) == "HELLO"


# ---------- mode file (mod 256, semua byte 0..255) ----------

DATA_BYTES = list(os.urandom(300)) + [0, 255, 128, 10]

KUNCI_FILE = [
    ("shift", "123"),
    ("substitution", "kunci-rahasia"),
    ("affine", "123 45"),
    ("vigenere", "KunciRahasia123"),
    ("hill", "3 3 2 5"),
    ("permutation", "3 1 4 2"),
]


@pytest.mark.parametrize("nama,kunci", KUNCI_FILE)
def test_round_trip_file(nama, kunci):
    out = run(nama, DATA_BYTES, kunci, True, 256)
    assert run(nama, out, kunci, False, 256) == DATA_BYTES


def test_round_trip_file_otp():
    kunci = os.urandom(len(DATA_BYTES))
    out = run("otp", DATA_BYTES, "", True, 256, keybytes=kunci)
    assert run("otp", out, "", False, 256, keybytes=kunci) == DATA_BYTES


# ---------- kunci tidak valid -> KeyErr ----------

KUNCI_BURUK = [
    ("shift", "3 4"),
    ("affine", "2 3"),
    ("affine", "5"),
    ("substitution", "A" * 26),
    ("hill", "1 2 3"),
    ("hill", "2 4 2 4"),
    ("permutation", "1 2 2"),
    ("permutation", "0 1"),
    ("vigenere", "123"),
    ("otp", "A"),
    ("playfair", "123"),
]


@pytest.mark.parametrize("nama,kunci", KUNCI_BURUK)
def test_kunci_tidak_valid(nama, kunci):
    with pytest.raises(KeyErr):
        run(nama, A("TEST"), kunci, True, 26)


def test_playfair_tolak_mode_file():
    with pytest.raises(KeyErr):
        run("playfair", [1, 2, 3], "MONARCHY", True, 256)


def test_cipher_tidak_dikenal():
    with pytest.raises(KeyErr):
        run("cipher_palsu", A("TEST"), "x", True, 26)
