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
    # BASABAS KURALI KAPALI (01.10.2026 - olculerek kaldirildi).
    #
    # Eskiden kar 1R'ye ulasinca stop girise cekiliyordu (basabas_r=1.0).
    # Esleştirilmis test (iki versiyon da BIREBIR AYNI islem kumesini alir,
    # 14.7 yil, bar-ici stop/hedef tespitli):
    #     XAUUSD  acik -0.1002R/islem (-129.0R)  ->  kapali +0.0365R (+47.0R)
    #     XAGUSD  acik -0.1128R/islem (-139.0R)  ->  kapali +0.0287R (+35.4R)
    #     fark XAU -0.1366R/islem (+-0.0473), XAG -0.1415R (+-0.0501) - ANLAMLI
    #
    # NEDEN zarar veriyordu: 1288 islemin 406'si basabasta (0R) kapaniyordu.
    # Kural olmasaydi o 406'nin 193'u hedefe (+2R), 213'u stopa (-1R) giderdi.
    #     213 kaybedeni kurtarir  -> +213R
    #     193 kazanani oldurur    -> -386R   (hedef 2R oldugu icin iki kat)
    #     NET -173R
    # Kurtardiginda 1R kazandiriyor, oldurdugunde 2R kaybettiriyor; iki olay
    # ise neredeyse esit siklikta. Isabetin %34.5'ten %19.5'e dusmesi budur.
    basabas_r=None,
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
