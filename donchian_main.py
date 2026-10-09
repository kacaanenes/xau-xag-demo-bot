"""Donchian kirilim botu - XAUUSD + XAGUSD, ayni hesapta.

AUDNZD'nin YERINI ALDI (05.08.2026). AUDNZD 15.2 yillik veride maliyetler
dahil -%51 yapiyordu ve hicbir varyanti ileriye yuruyen testten gecmedi;
bu bot ayni testlerin hepsinden gecen ilk kurulum (bkz. donchian_bot.py
docstring'i).

NEDEN IKI ENSTRUMAN AYNI HESAPTA: tekil dususler %32.8 (altin) ve %40.5
(gumus). Ikisi birlikte, islem basi %0.5 riskle, birlesik dusus %26.4'e
iniyor - hareketleri tam ortusmedigi icin. Ayni riskle tek enstruman
calistirmak daha dalgali bir egri verirdi.

Metaller hesabindaki (100k) meanrev botlari DOKUNULMADAN calismaya devam
ediyor - iki aile paralel olcusun diye.

SADECE demo hesap icindir - gercek/canli hesaba asla baglanmamali."""
from __future__ import annotations

import asyncio

from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

from donchian_bot import DonchianBot

BOTLAR = [
    # giris_esigi=90: kanalin tepesinde degil, ust %10'unda gir.
    # Olculdu (14.7 yil, spread dusulmus) - bkz. yon_serisi_donchian:
    #   XAU %100: 426 islem +138.1R (yarilar +0.178/+0.471)
    #   XAU  %90: 533 islem +183.4R (yarilar +0.304/+0.383)
    #   XAG %100: 425 islem  +98.8R (yarilar +0.290/+0.175)
    #   XAG  %90: 542 islem +106.6R (yarilar +0.211/+0.182)
    # Kenar ayni, islem sayisi artiyor, yarilar arasi fark KAPANIYOR.
    DonchianBot(sembol="XAUUSD", kontrat_buyuklugu=100, giris_esigi=90.0),
    DonchianBot(sembol="XAGUSD", kontrat_buyuklugu=5000, giris_esigi=90.0),
]


async def calistir() -> None:
    for bot in BOTLAR:
        try:
            await bot.calistir()
        except TradeException as e:
            print(f"  {bot.sembol}: islem su an basarisiz ({e}), piyasa kapali "
                  f"olabilir - sonraki calistirmada tekrar denenecek.")
        except Exception as e:  # noqa: BLE001 - bir sembol digerini durdurmasin
            print(f"  {bot.sembol}: beklenmeyen hata ({type(e).__name__}: {e}) - "
                  f"diger sembol ile devam ediliyor.")


if __name__ == "__main__":
    asyncio.run(calistir())
