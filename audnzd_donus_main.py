"""AUDNZD ortalamaya donus botu - calistirma girisi.

Hesap 2'de (10k) Donchian kirilim botunun YANINDA calisir. Cakisma yok:
Donchian XAUUSD/XAGUSD'de, bu AUDNZD'de. Ucu birden acik olursa toplam
risk %1.5 (islem basi %0.5).

Iki bot BILINCLI olarak zit ailelerde:
  Donchian (XAU/XAG, 4 saatlik) : TREND takip, hedefsiz, iz suren stop
  bu bot   (AUDNZD, 1 saatlik)  : ORTALAMAYA DONUS, 1R hedef, iz suren yok
Cunku enstrumanlarin olculen karakteri farkli - metaller kalici trend
yapar, AUDNZD dar bantta salinir (varyans orani 0.885-0.934).

Olcum ve gerekceler icin bkz. ortalama_donus_bot.py modul basligi.

SADECE demo hesap icindir - gercek/canli hesaba asla baglanmamali."""
from __future__ import annotations

import asyncio

from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

from ortalama_donus_bot import OrtalamaDonusBot

BOT = OrtalamaDonusBot(sembol="AUDNZD", kontrat_buyuklugu=100000)


async def calistir() -> None:
    try:
        await BOT.calistir()
    except TradeException as e:
        print(f"  Islem su an basarisiz ({e}), piyasa kapali olabilir - "
              f"sonraki calistirmada tekrar denenecek.")


if __name__ == "__main__":
    asyncio.run(calistir())
