"""[EMEKLI - sadece parite botu kullanir, workflow calistirmiyor]
Acik parite pozisyonunun rasyo-bazli giris/stop/hedef bilgisini yerel
dosyada tutar - MT5'in kendisi 'rasyo pozisyonu' kavramini bilmedigi icin
bu takibi biz yapiyoruz."""
from __future__ import annotations

import json
import os

_HESAP_ETIKETI = os.getenv("HESAP_ETIKETI", "")  # ikinci bir hesapta calisirken state dosyasi carpismasin diye
_DOSYA = os.path.join(os.path.dirname(__file__), f"pozisyon_durumu{_HESAP_ETIKETI}.json")


def kaydet(veri: dict) -> None:
    with open(_DOSYA, "w") as f:
        json.dump(veri, f)


def oku() -> dict | None:
    if not os.path.exists(_DOSYA):
        return None
    with open(_DOSYA) as f:
        return json.load(f)


def temizle() -> None:
    if os.path.exists(_DOSYA):
        os.remove(_DOSYA)
