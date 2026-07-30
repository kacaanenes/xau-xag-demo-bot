"""XAU/XAG parite serisi uzerinde teknik gostergeler."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema_serisi(seri: pd.Series, periyot: int) -> pd.Series:
    return seri.ewm(span=periyot, adjust=False).mean()


def rsi_serisi(seri: pd.Series, periyot: int = 14) -> pd.Series:
    fark = seri.diff()
    kazanc = fark.clip(lower=0)
    kayip = -fark.clip(upper=0)
    ort_kazanc = kazanc.ewm(alpha=1 / periyot, adjust=False).mean()
    ort_kayip = kayip.ewm(alpha=1 / periyot, adjust=False).mean()
    rs = ort_kazanc / ort_kayip.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100.0)


def macd_hesapla(seri: pd.Series, hizli: int = 12, yavas: int = 26, sinyal: int = 9):
    macd_cizgisi = ema_serisi(seri, hizli) - ema_serisi(seri, yavas)
    sinyal_cizgisi = ema_serisi(macd_cizgisi, sinyal)
    return macd_cizgisi, sinyal_cizgisi


def bollinger_hesapla(seri: pd.Series, periyot: int = 20, sapma: float = 2.0):
    orta = seri.rolling(periyot).mean()
    std = seri.rolling(periyot).std()
    ust = orta + sapma * std
    alt = orta - sapma * std
    return orta, ust, alt


def atr_kapanis_bazli(seri: pd.Series, periyot: int = 14) -> pd.Series:
    """XAU/XAG rasyosu gibi 'sentetik' serilerde high/low, iki ayri
    enstrumanin teorik en-kotu-senaryo birlesimi oldugu icin gercek bir
    bar-ici aralik degil - bu yuzden ATR'yi (dolayisiyla stop/hedef
    mesafesini) olmasi gerekenden genis hesaplatabilir. Bu fonksiyon sadece
    kapanis-kapanis farkina dayanir, daha guvenilir bir volatilite olcusu
    verir."""
    return seri.diff().abs().ewm(alpha=1 / periyot, adjust=False).mean()


def atr_serisi(df: pd.DataFrame, periyot: int = 14) -> pd.Series:
    onceki_kapanis = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - onceki_kapanis).abs(),
        (df["low"] - onceki_kapanis).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / periyot, adjust=False).mean()


def supertrend_hesapla(df: pd.DataFrame, periyot: int = 10, carpan: float = 3.0) -> pd.DataFrame:
    atr = atr_serisi(df, periyot)
    orta_fiyat = (df["high"] + df["low"]) / 2
    ust_bant_ham = orta_fiyat + carpan * atr
    alt_bant_ham = orta_fiyat - carpan * atr

    ust_bant = ust_bant_ham.copy()
    alt_bant = alt_bant_ham.copy()
    yukselis_mi = pd.Series(True, index=df.index)

    for i in range(1, len(df)):
        if df["close"].iloc[i - 1] > ust_bant.iloc[i - 1]:
            yukselis_mi.iloc[i] = True
        elif df["close"].iloc[i - 1] < alt_bant.iloc[i - 1]:
            yukselis_mi.iloc[i] = False
        else:
            yukselis_mi.iloc[i] = yukselis_mi.iloc[i - 1]

        if yukselis_mi.iloc[i]:
            alt_bant.iloc[i] = max(alt_bant_ham.iloc[i], alt_bant.iloc[i - 1])
        else:
            ust_bant.iloc[i] = min(ust_bant_ham.iloc[i], ust_bant.iloc[i - 1])

    supertrend = np.where(yukselis_mi, alt_bant, ust_bant)
    return pd.DataFrame({"supertrend": supertrend, "yukselis_mi": yukselis_mi}, index=df.index)


def most_hesapla(seri: pd.Series, periyot: int = 9, yuzde: float = 2.0) -> pd.DataFrame:
    mavg = seri.ewm(span=periyot, adjust=False).mean()
    oran = yuzde / 100

    most = mavg.copy()
    yukselis_mi = pd.Series(True, index=seri.index)

    for i in range(1, len(seri)):
        onceki_most = most.iloc[i - 1]
        if mavg.iloc[i] > onceki_most:
            deger = mavg.iloc[i] * (1 - oran)
            if deger < onceki_most:
                deger = onceki_most
            yukselis_mi.iloc[i] = True
        else:
            deger = mavg.iloc[i] * (1 + oran)
            if deger > onceki_most:
                deger = onceki_most
            yukselis_mi.iloc[i] = False
        most.iloc[i] = deger

    return pd.DataFrame({"most": most, "yukselis_mi": yukselis_mi}, index=seri.index)
