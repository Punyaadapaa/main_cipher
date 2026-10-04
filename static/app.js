// Logika antarmuka: kirim form ke /api/*, tampilkan hasil atau unduh file.
const $=id=>document.getElementById(id);
const H={shift:"Satu angka, mis. 3",substitution:"26 huruf berbeda (permutasi alfabet), mis. QWERTYUIOPASDFGHJKLZXCVBNM",
affine:"Dua angka 'a b'; a relatif prima dengan 26 (file: 256), mis. 7 3",vigenere:"Kata kunci bebas panjang, mis. LEMON",
hill:"Matriks n×n baris demi baris, mis. 3 3 2 5 (2×2). Determinan harus koprima mod 26 (teks) / ganjil (file, mod 256)",
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
