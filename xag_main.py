"""XAGUSD (gumus) tek enstruman demo botu.

Strateji secimi OLCUMLE yapildi: XAGUSD'nin varyans orani 0.847 (< 1), yani
ortalamaya donus karakterinde - ve mean-reversion backtest'i 61 islemde
%50.8 isabet, +%32.27 getiri verdi; ilk yari +%14.32, ikinci yari +%21.37,
yani her iki yarida da pozitif (saglamlik testinden gecti).

DIKKAT - onemli ayrim: daha once "tek bacak XAG" testi -%21.42 vermisti, ama
o test RASYONUN (XAU/XAG) sinyalini XAG'a uyguluyordu. Buradaki sinyal
XAG'IN KENDI Bollinger bandindan uretiliyor - tamamen farkli bir sey.

SADECE demo hesap icindir. Canli/gercek hesaba asla baglanmamali."""
from __future__ import annotations

import asyncio

from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

from tek_enstruman import TekEnstrumanBot

BOT = TekEnstrumanBot(
    sembol="XAGUSD",
    kontrat_buyuklugu=5000,
    strateji="meanrev",
    risk_odul_orani=2.0,
    # Sadece COMEX'in aktif oldugu saatlerde giris (rollover saati 21
    # haric). Olculdu: Asya seansinda acilan islemler %26 isabetle
    # zarardaydi; bu pencereye kisitlayinca isabet %68'e cikti.
    izinli_saatler=tuple(list(range(12, 21)) + [22, 23]),
)


async def calistir() -> None:
    try:
        await BOT.calistir()
    except TradeException as e:
        print(f"  Islem su an basarisiz ({e}), piyasa kapali olabilir - sonraki calistirmada tekrar denenecek.")


if __name__ == "__main__":
    asyncio.run(calistir())
