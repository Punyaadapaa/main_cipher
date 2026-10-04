"""
Tes route Flask (chiper_app.py) memakai test client:
alur normal, error ramah untuk input buruk, dan round-trip file.
"""
from io import BytesIO

import pytest

from chiper_app import app


@pytest.fixture()
def klien():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------- alur normal (karakterisasi perilaku yang sudah benar) ----------

def test_halaman_utama(klien):
    r = klien.get("/")
    assert r.status_code == 200
    assert b"Classic Ciphers" in r.data


def test_enkripsi_shift_via_api(klien):
    r = klien.post("/api/text", data={
        "cipher": "shift", "mode": "enc", "key": "3", "text": "HELLO", "group": "0"})
    assert r.status_code == 200
    assert r.get_json()["result"] == "KHOOR"


def test_dekripsi_hasil_kelompok_5(klien):
    enc = klien.post("/api/text", data={
        "cipher": "shift", "mode": "enc", "key": "1", "text": "DUNIA", "group": "5"})
    assert enc.get_json()["result"] == "EVOJB"
    dec = klien.post("/api/text", data={
        "cipher": "shift", "mode": "dec", "key": "1", "text": "EVOJB", "group": "0"})
    assert dec.get_json()["result"] == "DUNIA"


def test_hill_panjang_bukan_kelipatan_pulih_sempurna(klien):
    # 11 huruf, blok 2 -> dipad; dekripsi harus persis 11 huruf semula
    enc = klien.post("/api/text", data={
        "cipher": "hill", "mode": "enc", "key": "3 3 2 5", "text": "HANIEFMENDO", "group": "0"})
    dec = klien.post("/api/text", data={
        "cipher": "hill", "mode": "dec", "key": "3 3 2 5", "text": enc.get_json()["result"], "group": "0"})
    assert dec.get_json()["result"] == "HANIEFMENDO"


def test_permutation_panjang_bukan_kelipatan_pulih_sempurna(klien):
    enc = klien.post("/api/text", data={
        "cipher": "permutation", "mode": "enc", "key": "3 1 4 2", "text": "HANIEFMENDO", "group": "0"})
    dec = klien.post("/api/text", data={
        "cipher": "permutation", "mode": "dec", "key": "3 1 4 2", "text": enc.get_json()["result"], "group": "0"})
    assert dec.get_json()["result"] == "HANIEFMENDO"


def test_otp_via_file_kunci(klien):
    import string
    kunci = ("".join(string.ascii_uppercase) * 4).encode()  # 104 huruf acak-pola
    enc = klien.post("/api/text", data={
        "cipher": "otp", "mode": "enc", "key": "", "text": "SERANG FAJAR", "group": "0",
        "keyfile": (BytesIO(kunci), "otp_key.txt")}, content_type="multipart/form-data")
    assert enc.status_code == 200
    dec = klien.post("/api/text", data={
        "cipher": "otp", "mode": "dec", "key": "", "text": enc.get_json()["result"], "group": "0",
        "keyfile": (BytesIO(kunci), "otp_key.txt")}, content_type="multipart/form-data")
    assert dec.get_json()["result"] == "SERANGFAJAR"


def test_playfair_via_api(klien):
    enc = klien.post("/api/text", data={
        "cipher": "playfair", "mode": "enc", "key": "MONARCHY", "text": "INSTRUMENT", "group": "0"})
    assert enc.status_code == 200
    dec = klien.post("/api/text", data={
        "cipher": "playfair", "mode": "dec", "key": "MONARCHY", "text": enc.get_json()["result"], "group": "0"})
    assert dec.get_json()["result"] == "INSTRUMENT"


def test_playfair_mode_file_ditolak(klien):
    r = klien.post("/api/file", data={
        "cipher": "playfair", "mode": "enc", "key": "MONARCHY",
        "file": (BytesIO(b"ABC"), "test.txt")}, content_type="multipart/form-data")
    assert r.status_code == 400
    assert r.is_json
    assert "Playfair" in r.get_json()["error"]


def test_kunci_buruk_menghasilkan_json_400(klien):
    r = klien.post("/api/text", data={
        "cipher": "shift", "mode": "enc", "key": "3 4", "text": "HELLO", "group": "0"})
    assert r.status_code == 400
    assert r.is_json
    assert "error" in r.get_json()


def test_cipher_tak_dikenal_via_api(klien):
    r = klien.post("/api/text", data={
        "cipher": "cipher_palsu", "mode": "enc", "key": "3", "text": "HELLO", "group": "0"})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_file_tanpa_lampiran(klien):
    r = klien.post("/api/file", data={"cipher": "shift", "mode": "enc", "key": "3"},
                   content_type="multipart/form-data")
    assert r.status_code == 400
    assert r.is_json


def test_enkripsi_dekripsi_file_end_to_end(klien):
    isi = bytes(range(256)) * 3 + b"JPEGDATA"
    r = klien.post("/api/file", data={
        "cipher": "shift", "mode": "enc", "key": "42",
        "file": (BytesIO(isi), "foto.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 200
    assert r.headers["X-Filename"] == "foto.jpg.dat"
    blob = r.data
    assert blob[:4] == b"PYCF"

    r2 = klien.post("/api/file", data={
        "cipher": "shift", "mode": "dec", "key": "42",
        "file": (BytesIO(blob), "foto.jpg.dat")}, content_type="multipart/form-data")
    assert r2.status_code == 200
    assert r2.headers["X-Filename"] == "foto.jpg"
    assert r2.data == isi


def test_genkey_valid(klien):
    r = klien.get("/api/genkey?n=100")
    assert r.status_code == 200
    data = r.data.decode()
    assert len(data) == 100
    assert all("A" <= c <= "Z" for c in data)


# ---------- bug: input buruk harus 400 + pesan ramah, bukan 500 ----------

def test_pesan_tanpa_huruf_alfabet(klien):
    # BUG: sekarang balas 200 dengan hasil kosong
    r = klien.post("/api/text", data={
        "cipher": "shift", "mode": "enc", "key": "3", "text": "123 !!!", "group": "0"})
    assert r.status_code == 400
    assert "huruf alfabet" in r.get_json()["error"]


def test_field_tidak_lengkap_json_400(klien):
    # BUG: sekarang balas 400 HTML generik, bukan JSON ramah
    r = klien.post("/api/text", data={"cipher": "shift", "text": "HELLO"})
    assert r.status_code == 400
    assert r.is_json
    assert "error" in r.get_json()


def test_genkey_n_tidak_valid(klien):
    # BUG: sekarang crash 500
    r = klien.get("/api/genkey?n=abc")
    assert r.status_code == 400
    assert r.is_json
    assert "error" in r.get_json()


# ---------- pemisahan antarmuka: HTML/CSS/JS di templates/ + static/ ----------

def test_aset_css_dan_js_tersedia(klien):
    assert klien.get("/static/style.css").status_code == 200
    assert klien.get("/static/app.js").status_code == 200


def test_halaman_memuat_aset(klien):
    html = klien.get("/").data
    assert b"static/style.css" in html
    assert b"static/app.js" in html


def test_halaman_punya_radio_tipe_input_dan_hasil_berlabel(klien):
    """Redesign: radio Tipe input (Teks/File) + hasil berlabel Plaintext/Ciphertext."""
    html = klien.get("/").data
    assert b'name="input_type"' in html
    assert b"Plaintext" in html
    assert b"Ciphertext" in html
    assert b"btn-enc" in html
    assert b"btn-dec" in html
