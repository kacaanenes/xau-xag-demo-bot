"""GIRIS KAYMASI (slippage) kaydi.

NEDEN: demo hesap emirleri idealize sekilde dolduruyor. Olculdu (05.08.2026,
24 cikis): stop ve hedef emirlerinin HEPSI seviyenin tam uzerinde doldu,
kayma sifir. Gercek brokerde boyle olmaz - ozellikle stop emirlerinde
fiyat seviyeyi asarak doldurur ve zarar planlanandan buyuk olur.

Bu modul her ACILIS icin sunu kaydeder:
  - emir gonderilmeden onceki fiyat (lot ve stop hesabinin dayandigi fiyat)
  - emrin fiilen doldugu fiyat
  - aradaki fark = kayma

Birkac hafta sonra gercek kayma dagilimimiz olur ve backtest maliyet
modeline VARSAYIM degil OLCUM koyabiliriz.

Kayit basarisiz olsa bile islem akisi ETKILENMEZ - her sey try/except
icinde ve hata sadece loga yazilir.

SADECE demo hesap icindir.
"""
from __future__ import annotations

import datetime as dt
import json
import os

_HESAP_ETIKETI = os.getenv("HESAP_ETIKETI", "")
_DOSYA = os.path.join(os.path.dirname(__file__), f"kayma_kaydi{_HESAP_ETIKETI}.jsonl")
_AZAMI_SATIR = 500


def kaydet(sembol: str, yon: str, istenen: float, dolan: float, lot: float,
           stop_mesafesi: float) -> None:
    """Bir girisin istenen ve dolan fiyatini yazar.

    kayma_R: kaymanin RISK cinsinden buyuklugu - asil onemli olan bu,
    cunku zararin ne kadarini kaymanin yedigi bununla olculur.
    Isaret: POZITIF = aleyhte (kotu), NEGATIF = lehte."""
    try:
        isaret = 1 if yon == "AL" else -1
        kayma = (dolan - istenen) * isaret          # aleyhte = pozitif
        satir = {
            "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "sembol": sembol, "yon": yon,
            "istenen": round(istenen, 6), "dolan": round(dolan, 6),
            "kayma": round(kayma, 6),
            "kayma_R": round(kayma / stop_mesafesi, 5) if stop_mesafesi else None,
            "lot": lot,
        }
        with open(_DOSYA, "a") as f:
            f.write(json.dumps(satir) + "\n")
        # dosya sinirsiz buyumesin
        with open(_DOSYA) as f:
            satirlar = f.readlines()
        if len(satirlar) > _AZAMI_SATIR:
            with open(_DOSYA, "w") as f:
                f.writelines(satirlar[-_AZAMI_SATIR:])
        if abs(satir["kayma_R"] or 0) > 0.001:
            print(f"  KAYMA: istenen {istenen:.5f} -> dolan {dolan:.5f} "
                  f"({kayma:+.5f} = {satir['kayma_R']:+.4f}R)")
    except Exception as exc:  # noqa: BLE001 - kayit hatasi islemi bozmamali
        print(f"  (Kayma kaydedilemedi: {exc})")


def ozet() -> dict | None:
    """Birikmis kayitlarin ozeti - maliyet modelini guncellemek icin."""
    if not os.path.exists(_DOSYA):
        return None
    try:
        with open(_DOSYA) as f:
            kayitlar = [json.loads(s) for s in f if s.strip()]
    except (json.JSONDecodeError, OSError):
        return None
    if not kayitlar:
        return None
    sonuc = {}
    for k in kayitlar:
        s = k["sembol"]
        sonuc.setdefault(s, []).append(k.get("kayma_R") or 0.0)
    return {s: {"adet": len(v), "ortalama_R": sum(v)/len(v),
                "en_kotu_R": max(v), "aleyhte_oran": sum(1 for x in v if x > 0)/len(v)}
            for s, v in sonuc.items()}


if __name__ == "__main__":
    o = ozet()
    if not o:
        print("Henuz kayit yok.")
    else:
        print(f"{'sembol':<10}{'adet':>6}{'ort. kayma_R':>15}{'en kotu':>10}{'aleyhte %':>11}")
        for s, v in o.items():
            print(f"{s:<10}{v['adet']:>6}{v['ortalama_R']:>+15.5f}{v['en_kotu_R']:>+10.5f}"
                  f"{v['aleyhte_oran']*100:>10.0f}%")
