"""Her bacak icin ATR bazli stop-loss / kar-al hesaplar. Minimum risk
felsefesi: sabit kucuk lot + dar stop."""
from __future__ import annotations

import teknik

SL_ATR_CARPANI = 1.5
RISK_ODUL_ORANI = 1.5
LOT = 0.01  # artik kullanilmiyor, geriye uyumluluk icin birakildi

# Bacak-seviyesi stoplar artik asil karar mekanizmasi degil, sadece dongu
# calismazsa diye bir felaket guvenlik agi - bu yuzden normalden cok daha
# genis tutuluyor. Asil kapama karari rasyonun kendi stop/hedefine gore
# main.py'de veriliyor.
GUVENLIK_AGI_CARPANI = 4.0

RATIO_SL_ATR_CARPANI = 1.5
RATIO_RISK_ODUL_ORANI = 2.0  # mean-reversion icin olculen en iyi risk/odul

XAU_KONTRAT_BUYUKLUGU = 100  # oz/lot
XAG_KONTRAT_BUYUKLUGU = 5000  # oz/lot

# Sabit dolar riski yerine, hesap bakiyesinin YUZDESI kadar risk hedeflenir.
# Sabit $30, 100.000 USD hesapta %0.03 gibi anlamsiz kucuk bir risk demekti
# (bu yuzden kazaniIrken bile kazanc cuzi kaliyordu) - %1 (profesyonel risk
# yonetiminde "dusuk ama anlamli" kabul edilen seviye), hesap buyuklugune
# gore olcekleniyor: genis stop -> kucuk lot, dar stop -> buyuk lot, ama
# risk her zaman bakiyenin sabit bir yuzdesi kalir.
RISK_YUZDESI = 0.01  # bakiyenin %1'i
MIN_LOT = 0.01
LOT_ADIMI = 0.01


def lot_hesapla(stop_mesafesi_fiyat: float, kontrat_buyuklugu: float, bakiye: float,
                 risk_yuzdesi: float = RISK_YUZDESI) -> float:
    if stop_mesafesi_fiyat <= 0:
        return MIN_LOT
    hedef_risk_usd = bakiye * risk_yuzdesi
    lot_ham = hedef_risk_usd / (stop_mesafesi_fiyat * kontrat_buyuklugu)
    lot = round(lot_ham / LOT_ADIMI) * LOT_ADIMI
    return max(round(lot, 2), MIN_LOT)


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
