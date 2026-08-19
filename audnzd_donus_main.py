"""AUDNZD ortalamaya donus botu - calistirma girisi.

KENDI HESABINDA calisir - Hesap 3 (100k). Donchian kirilim botu (Hesap 2,
10k) ile AYNI HESAPTA DEGIL; workflow'daki gerekce: lot hesabi ozsermayeye
dayaniyor (bakiye = hesap["equity"]) ve ozsermaye acik pozisyonlarin anlik
kar/zararini da icerir. Ayni hesapta olsalardi Donchian'in acik kari bu
botun lotunu buyutur, dususu kucultturdu. Ayri hesap = ayri ozsermaye,
ayri marj, ayri dusus; iki sistemin performansi bagimsiz olculebilir.

Bu bot kendi hesabinda tek basina calistigi icin ayni anda acik olabilecek
tek pozisyonu vardir - islem basi risk %0.5.

Iki bot (ayri hesaplarda olsalar da) BILINCLI olarak zit ailelerde:
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
