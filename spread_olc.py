"""SPREAD SEANS PROFILI - saat bazli islem maliyeti olcumu.

NEDEN GEREKLI: backtest maliyet modeli tek bir anlik olcume dayaniyordu.
Olculdu ve yaniltici oldugu gorulldu:
    XAUUSD 10:11 UTC -> 0.50   |   19:46 UTC -> 0.21   (2.4 kat fark)
Model 0.50 kullaniyordu; bu altin sonuclarini kotumser, gumusu (0.018
kullanilirken gercek ~0.034) iyimser gosteriyordu.

ONCEKI IKI DENEME NEDEN BASARISIZ OLDU:
  1) MetaApi websocket zaman asimi surecin tamamini dusurdu (8 saat sonra).
  2) Ikinci surum hatayi yakaliyordu ama get_symbol_price cagrisinin
     KENDISI asili kaldi - await'in etrafinda zaman asimi yoktu, dolayisiyla
     surec "canli" gorunup iki gun boyunca hicbir sey yazmadi.

BU SURUM: her cagri asyncio.wait_for ile 20 saniyeye baglanmis, hata
durumunda baglanti sifirlaniyor ve dongu devam ediyor. Boylece tek bir
takilma tum olcumu bitirmiyor.

Kullanim:  python spread_olc.py [saat]     (varsayilan 26 saat)
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import pathlib
import sys

import mt5_veri

YOL = pathlib.Path(__file__).parent / "veri" / "spread_profili.jsonl"
SEMBOLLER = ("XAUUSD", "XAGUSD")
ARALIK_SN = 600
CAGRI_ZAMAN_ASIMI = 20


async def _fiyat(baglanti, sembol):
    return await asyncio.wait_for(baglanti.get_symbol_price(sembol), CAGRI_ZAMAN_ASIMI)


async def olc(saat: float = 26.0):
    YOL.parent.mkdir(exist_ok=True)
    bitis = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=saat)
    yazilan = hatali = 0
    while dt.datetime.now(dt.timezone.utc) < bitis:
        simdi = dt.datetime.now(dt.timezone.utc)
        satir = {"zaman": simdi.isoformat(timespec="seconds"), "saat": simdi.hour}
        try:
            baglanti = await asyncio.wait_for(mt5_veri.baglanti_al(), 60)
            for s in SEMBOLLER:
                f = await _fiyat(baglanti, s)
                satir[s] = round(f["ask"] - f["bid"], 5)
            yazilan += 1
        except Exception as exc:  # noqa: BLE001 - tek olcum basarisiz olabilir
            satir["hata"] = f"{type(exc).__name__}: {str(exc)[:60]}"
            hatali += 1
            # Baglantiyi sifirla ki bir sonraki tur yeniden kurulsun
            mt5_veri._baglanti = None
            mt5_veri._hesap = None
            mt5_veri._api = None
        with open(YOL, "a") as fh:
            fh.write(json.dumps(satir) + "\n")
        print(f"  {satir['zaman'][11:16]} " +
              " ".join(f"{s}={satir.get(s,'HATA')}" for s in SEMBOLLER), flush=True)
        await asyncio.sleep(ARALIK_SN)
    print(f"BITTI - {yazilan} basarili, {hatali} hatali olcum", flush=True)


if __name__ == "__main__":
    asyncio.run(olc(float(sys.argv[1]) if len(sys.argv) > 1 else 26.0))
