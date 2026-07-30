"""Gercek emir acmadan, hipotetik (kagit uzerinde) pozisyon durumunu ve
kapanan islem gecmisini strateji basina ayri dosyalarda tutar."""
from __future__ import annotations

import json
import os

_KLASOR = os.path.dirname(__file__)
_GECMIS_DOSYASI = os.path.join(_KLASOR, "kagit_gecmis.jsonl")


def _durum_dosyasi(strateji_adi: str) -> str:
    return os.path.join(_KLASOR, f"kagit_durum_{strateji_adi}.json")


def durum_kaydet(strateji_adi: str, veri: dict) -> None:
    with open(_durum_dosyasi(strateji_adi), "w") as f:
        json.dump(veri, f)


def durum_oku(strateji_adi: str) -> dict | None:
    yol = _durum_dosyasi(strateji_adi)
    if not os.path.exists(yol):
        return None
    with open(yol) as f:
        return json.load(f)


def durum_temizle(strateji_adi: str) -> None:
    yol = _durum_dosyasi(strateji_adi)
    if os.path.exists(yol):
        os.remove(yol)


def gecmise_ekle(kayit: dict) -> None:
    with open(_GECMIS_DOSYASI, "a") as f:
        f.write(json.dumps(kayit) + "\n")


def gecmisi_oku(strateji_adi: str | None = None) -> list[dict]:
    if not os.path.exists(_GECMIS_DOSYASI):
        return []
    kayitlar = []
    with open(_GECMIS_DOSYASI) as f:
        for satir in f:
            satir = satir.strip()
            if not satir:
                continue
            kayit = json.loads(satir)
            if strateji_adi is None or kayit.get("strateji") == strateji_adi:
                kayitlar.append(kayit)
    return kayitlar
