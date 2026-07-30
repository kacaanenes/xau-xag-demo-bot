"""Her bacak icin ATR bazli stop-loss / kar-al hesaplar. Minimum risk
felsefesi: sabit kucuk lot + dar stop."""
from __future__ import annotations

import teknik

SL_ATR_CARPANI = 1.5
RISK_ODUL_ORANI = 1.5
LOT = 0.01

# Bacak-seviyesi stoplar artik asil karar mekanizmasi degil, sadece dongu
# calismazsa diye bir felaket guvenlik agi - bu yuzden normalden cok daha
# genis tutuluyor. Asil kapama karari rasyonun kendi stop/hedefine gore
# main.py'de veriliyor.
GUVENLIK_AGI_CARPANI = 4.0

RATIO_SL_ATR_CARPANI = 1.5
RATIO_RISK_ODUL_ORANI = 2.0  # mean-reversion icin olculen en iyi risk/odul


def stop_ve_hedef_hesapla(df, giris_fiyati: float, alis_mi: bool, atr_carpani: float = SL_ATR_CARPANI) -> dict:
    atr = teknik.atr_serisi(df, 14).iloc[-1]
    stop_mesafesi = atr_carpani * atr
    hedef_mesafesi = RISK_ODUL_ORANI * stop_mesafesi

    if alis_mi:
        stop = giris_fiyati - stop_mesafesi
        hedef = giris_fiyati + hedef_mesafesi
    else:
        stop = giris_fiyati + stop_mesafesi
        hedef = giris_fiyati - hedef_mesafesi

    return {"stop_loss": round(stop, 5), "take_profit": round(hedef, 5), "atr": float(atr)}


def rasyo_stop_hedef_hesapla(rasyo_df, giris_orani: float, alis_mi: bool) -> dict:
    """Parite (XAU/XAG) serisinin kendi ATR'sine gore ortak stop/hedef -
    iki bacagi birlikte kapatma kararinda kullanilir. Kapanis-bazli ATR
    kullanilir: rasyonun high/low'u iki ayri enstrumanin teorik en-kotu-
    senaryo birlesimi oldugu icin gercek bar-ici aralik degil - bunu ATR'ye
    sokmak stop/hedefi gereginden genis hesaplatiyordu (olculdu, duzeltildi)."""
    atr = teknik.atr_kapanis_bazli(rasyo_df["close"], 14).iloc[-1]
    stop_mesafesi = RATIO_SL_ATR_CARPANI * atr
    hedef_mesafesi = RATIO_RISK_ODUL_ORANI * stop_mesafesi

    if alis_mi:
        stop = giris_orani - stop_mesafesi
        hedef = giris_orani + hedef_mesafesi
    else:
        stop = giris_orani + stop_mesafesi
        hedef = giris_orani - hedef_mesafesi

    return {"stop_orani": round(stop, 5), "hedef_orani": round(hedef, 5), "atr_orani": float(atr)}
