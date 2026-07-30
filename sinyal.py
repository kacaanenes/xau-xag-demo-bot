"""Alti gostergenin coguluk oyuna gore XAU/XAG parite sinyali uretir."""
from __future__ import annotations

import teknik

_ESIK = 4  # 6 oydan en az 4'u ayni yonde olmali


def confluence_sinyali_hesapla(df) -> dict:
    kapanis = df["close"]

    ema20 = teknik.ema_serisi(kapanis, 20)
    ema50 = teknik.ema_serisi(kapanis, 50)
    rsi = teknik.rsi_serisi(kapanis, 14)
    macd_cizgisi, macd_sinyal = teknik.macd_hesapla(kapanis)
    orta_bant, _, _ = teknik.bollinger_hesapla(kapanis, 20, 2.0)
    st_df = teknik.supertrend_hesapla(df, 10, 3.0)
    most_df = teknik.most_hesapla(kapanis, 9, 2.0)

    oylar = {
        "EMA20/50": bool(ema20.iloc[-1] > ema50.iloc[-1]),
        "MACD": bool(macd_cizgisi.iloc[-1] > macd_sinyal.iloc[-1]),
        "RSI": bool(rsi.iloc[-1] > 50),
        "SuperTrend": bool(st_df["yukselis_mi"].iloc[-1]),
        "MOST": bool(most_df["yukselis_mi"].iloc[-1]),
        "Bollinger": bool(kapanis.iloc[-1] > orta_bant.iloc[-1]),
    }

    yukselis_oyu = sum(oylar.values())
    dusus_oyu = len(oylar) - yukselis_oyu

    if yukselis_oyu >= _ESIK:
        yon = "AL"
    elif dusus_oyu >= _ESIK:
        yon = "SAT"
    else:
        yon = None

    return {
        "yon": yon,
        "oylar": oylar,
        "yukselis_oyu": yukselis_oyu,
        "dusus_oyu": dusus_oyu,
        "rasyo_son": float(kapanis.iloc[-1]),
    }
