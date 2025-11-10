import requests
from bs4 import BeautifulSoup
import json

API_URL = "https://banksampah.jakarta.go.id/api/web/index"
DETAIL_URL = "https://banksampah.jakarta.go.id/detail_lokasi/?id="

# ambil daftar bank sampah
resp = requests.get(API_URL)
data = resp.json()

results = []

import re

def parse_coord(val):
    if not val:
        return None
    val = val.strip().replace(",", "")
    # ambil hanya angka, minus, titik
    match = re.search(r"-?\d+(\.\d+)?", val)
    if not match:
        return None
    num = float(match.group())
    if val[-1].upper() in ["S", "W"]:
        return -abs(num)
    return num

for idx, item in enumerate(data, start=1):
    bs_id = item["id"]
    detail_page = requests.get(DETAIL_URL + bs_id)
    soup = BeautifulSoup(detail_page.text, "html.parser")

    # ambil nama
    nama = soup.find("h3", class_="text-color-dark").get_text(strip=True)

    # ambil semua paragraf setelah "Alamat :"
    alamat_paragraf = []
    alamat_section = soup.find("h2", string=lambda x: x and "Alamat" in x)
    if alamat_section:
        for p in alamat_section.find_all_next("p"):
            text = p.get_text(strip=True)
            if text.startswith("Telp"):  # stop kalau sudah sampai telepon
                break
            alamat_paragraf.append(text)
    alamat = " ".join(alamat_paragraf)

    # ambil telepon
    telp = None
    telp_tag = soup.find("p", string=lambda x: x and "Telp" in x)
    if telp_tag:
        telp = telp_tag.get_text(strip=True).replace("Telp :", "").strip()

    result = {
        "id": bs_id,
        "nama": nama,
        "alamat": alamat,
        "telepon": telp,
        "latitude": parse_coord(item["latitude"]),
        "longitude": parse_coord(item["longitude"]),
        "jenis": item["jenis"]
    }

    results.append(result)

    # tampilkan progress di console
    print(f"[{idx}/{len(data)}] {nama} | {alamat} | {telp}")

with open("banksampah.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)