"""XAUUSD (altin) tek enstruman demo botu.

Strateji secimi OLCUMLE yapildi: varyans orani 0.907 (< 1), yani ortalamaya
donus karakterinde. Mean-reversion backtest'i (basabas @1.0R dahil) 75
islemde %42.7 isabet, brut +%12.76 verdi; ilk yari +%1.59, ikinci yari
+%10.27 (her iki yarida da pozitif). Spread cok dar (0.7bp), 75 islemde
toplam maliyet sadece %0.50 -> NET +%12.26.

SADECE demo hesap icindir. Canli/gercek hesaba asla baglanmamali."""
from __future__ import annotations

import asyncio

from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

from tek_enstruman import TekEnstrumanBot

BOT = TekEnstrumanBot(
    sembol="XAUUSD",
    kontrat_buyuklugu=100,
    strateji="meanrev",
    risk_odul_orani=2.0,
)


async def calistir() -> None:
    try:
        await BOT.calistir()
    except TradeException as e:
        print(f"  Islem su an basarisiz ({e}), piyasa kapali olabilir - sonraki calistirmada tekrar denenecek.")


if __name__ == "__main__":
    asyncio.run(calistir())
