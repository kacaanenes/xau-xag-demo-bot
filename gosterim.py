"""Hangi aciklarin 'gosterim' (stratejinin sinyali olmadan, elle acilmis)
oldugunu isaretler.

NEDEN: Stratejinin olculen avantaji SADECE esik asildiginda girilen
islemlerden geliyor. Esiksiz acilan gosterim pozisyonlari bu avantaji
tasimaz - bu yuzden gercek bir sinyal geldiginde bunlarin yerini
stratejinin kendi pozisyonuna birakmasi gerekir. Strateji pozisyonlari ise
normal kurala tabidir: stop/hedefe kadar tutulur, her barda kapatilip
yeniden acilmaz (yoksa sinyal birkac bar surdugunde surekli girip cikma
olusurdu)."""
from __future__ import annotations

import json
import os

_DOSYA = os.path.join(os.path.dirname(__file__),
                      f"gosterim_pozisyonlari{os.getenv('HESAP_ETIKETI', '')}.json")


def _oku() -> list[str]:
    if not os.path.exists(_DOSYA):
        return []
    try:
        with open(_DOSYA) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _yaz(semboller: list[str]) -> None:
    with open(_DOSYA, "w") as f:
        json.dump(sorted(set(semboller)), f)


def isaretle(sembol: str) -> None:
    _yaz(_oku() + [sembol])


def isareti_kaldir(sembol: str) -> None:
    _yaz([s for s in _oku() if s != sembol])


def gosterim_mi(sembol: str) -> bool:
    return sembol in _oku()
