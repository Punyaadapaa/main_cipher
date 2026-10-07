-- schema.sql
CREATE TABLE mahasiswa (
    id INTEGER PRIMARY KEY,
    nama TEXT,
    nim TEXT,
    jurusan TEXT
);

INSERT INTO mahasiswa VALUES
(1, 'Daffa Arkhan', 'L0324010', 'Informatika'),
(2, 'Budi Santoso', 'L0324011', 'Informatika'),
(3, 'Citra Dewi',   'L0324012', 'Informatika');