"""XAU/XAG parite stratejilerini gecmis veride GERCEK DOLAR P&L'i uzerinden
olcer - varsayim degil, olcum. Birden fazla strateji varyanti (confluence
esikleri, farkli risk/odul, mean-reversion) ayni harness ile test edilip
karsilastirilabilir."""
from __future__ import annotations

import teknik

ISINMA_BARI = 50  # ilk N bar, gostergelerin (EMA50 vb.) kararlilik kazanmasi icin atlanir
XAU_KONTRAT_BUYUKLUGU = 100  # oz/lot
XAG_KONTRAT_BUYUKLUGU = 5000  # oz/lot


def _yon_serisi_confluence(df, esik: int = 4):
    kapanis = df["close"]
    ema20 = teknik.ema_serisi(kapanis, 20)
    ema50 = teknik.ema_serisi(kapanis, 50)
    rsi = teknik.rsi_serisi(kapanis, 14)
    macd_cizgisi, macd_sinyal = teknik.macd_hesapla(kapanis)
    orta_bant, _, _ = teknik.bollinger_hesapla(kapanis, 20, 2.0)
    st_df = teknik.supertrend_hesapla(df, 10, 3.0)
    most_df = teknik.most_hesapla(kapanis, 9, 2.0)

    yonler = []
    for i in range(len(df)):
        yukselis_oyu = sum([
            ema20.iloc[i] > ema50.iloc[i],
            macd_cizgisi.iloc[i] > macd_sinyal.iloc[i],
            rsi.iloc[i] > 50,
            bool(st_df["yukselis_mi"].iloc[i]),
            bool(most_df["yukselis_mi"].iloc[i]),
            kapanis.iloc[i] > orta_bant.iloc[i],
        ])
        dusus_oyu = 6 - yukselis_oyu
        if yukselis_oyu >= esik:
            yonler.append("AL")
        elif dusus_oyu >= esik:
            yonler.append("SAT")
        else:
            yonler.append(None)
    return yonler


def _yon_serisi_mean_reversion(df, periyot: int = 20, sapma: float = 2.0):
    """XAU/XAG rasyosunun uzun vadede ortalamaya donme egilimi bilinir
    (finans literaturunde 'gold-silver ratio mean reversion'). Rasyo kendi
    Bollinger alt bandinin altina duserse 'asiri dusuk, geri donecek' (AL),
    ust bandin ustune cikarsa 'asiri yuksek, geri donecek' (SAT) varsayilir."""
    kapanis = df["close"]
    orta_bant, ust_bant, alt_bant = teknik.bollinger_hesapla(kapanis, periyot, sapma)

    yonler = []
    for i in range(len(df)):
        if pandas_nan(alt_bant.iloc[i]) or pandas_nan(ust_bant.iloc[i]):
            yonler.append(None)
        elif kapanis.iloc[i] <= alt_bant.iloc[i]:
            yonler.append("AL")
        elif kapanis.iloc[i] >= ust_bant.iloc[i]:
            yonler.append("SAT")
        else:
            yonler.append(None)
    return yonler


def pandas_nan(deger) -> bool:
    return deger != deger  # NaN != NaN


def _pozisyon_simulasyonu(df, yon_serisi, sl_atr_carpani: float, risk_odul_orani: float, sinyal_tersine_cikis: bool,
                           kapanis_bazli_atr: bool = False):
    kapanis = df["close"]
    atr = teknik.atr_kapanis_bazli(kapanis, 14) if kapanis_bazli_atr else teknik.atr_serisi(df, 14)

    islemler = []
    pozisyon = None

    for i in range(ISINMA_BARI, len(df)):
        fiyat = kapanis.iloc[i]

        if pozisyon is not None:
            tetiklendi, sebep = False, None
            if pozisyon["yon"] == "AL":
                if fiyat <= pozisyon["stop"]:
                    tetiklendi, sebep = True, "stop"
                elif fiyat >= pozisyon["hedef"]:
                    tetiklendi, sebep = True, "hedef"
            else:
                if fiyat >= pozisyon["stop"]:
                    tetiklendi, sebep = True, "stop"
                elif fiyat <= pozisyon["hedef"]:
                    tetiklendi, sebep = True, "hedef"

            if not tetiklendi and sinyal_tersine_cikis and yon_serisi[i] is not None and yon_serisi[i] != pozisyon["yon"]:
                tetiklendi, sebep = True, "sinyal_tersine_dondu"

            if tetiklendi:
                kazandi_mi = (fiyat > pozisyon["giris_fiyat"]) if pozisyon["yon"] == "AL" else (fiyat < pozisyon["giris_fiyat"])
                yon_isareti = 1 if pozisyon["yon"] == "AL" else -1
                islemler.append({
                    "yon": pozisyon["yon"],
                    "giris": pozisyon["giris_fiyat"],
                    "cikis": fiyat,
                    "giris_i": pozisyon["giris_i"],
                    "cikis_i": i,
                    "sebep": sebep,
                    "kazandi_mi": kazandi_mi,
                    "getiri_yuzde": (fiyat / pozisyon["giris_fiyat"] - 1) * 100 * yon_isareti,
                })
                pozisyon = None

        if pozisyon is None and yon_serisi[i] is not None:
            atr_deger = atr.iloc[i]
            stop_mesafesi = sl_atr_carpani * atr_deger
            hedef_mesafesi = risk_odul_orani * stop_mesafesi
            if yon_serisi[i] == "AL":
                stop = fiyat - stop_mesafesi
                hedef = fiyat + hedef_mesafesi
            else:
                stop = fiyat + stop_mesafesi
                hedef = fiyat - hedef_mesafesi
            pozisyon = {"yon": yon_serisi[i], "giris_fiyat": fiyat, "stop": stop, "hedef": hedef, "giris_i": i}

    return islemler


def _ozet_hesapla(islemler) -> dict:
    toplam = len(islemler)
    kazanan = sum(1 for t in islemler if t["kazandi_mi"])
    sebep_dagilimi = {}
    for t in islemler:
        sebep_dagilimi[t["sebep"]] = sebep_dagilimi.get(t["sebep"], 0) + 1

    return {
        "toplam_islem": toplam,
        "kazanan": kazanan,
        "kaybeden": toplam - kazanan,
        "isabet_orani": round(kazanan / toplam * 100, 1) if toplam else 0.0,
        "ortalama_getiri_yuzde": round(sum(t["getiri_yuzde"] for t in islemler) / toplam, 4) if toplam else 0.0,
        "toplam_getiri_yuzde": round(sum(t["getiri_yuzde"] for t in islemler), 2) if toplam else 0.0,
        "sebep_dagilimi": sebep_dagilimi,
        "islemler": islemler,
    }


def confluence_backtest(df, esik: int = 4, sl_atr_carpani: float = 1.5, risk_odul_orani: float = 1.5,
                         sinyal_tersine_cikis: bool = True, kapanis_bazli_atr: bool = False) -> dict:
    yon_serisi = _yon_serisi_confluence(df, esik)
    islemler = _pozisyon_simulasyonu(df, yon_serisi, sl_atr_carpani, risk_odul_orani, sinyal_tersine_cikis, kapanis_bazli_atr)
    return _ozet_hesapla(islemler)


def mean_reversion_backtest(df, periyot: int = 20, sapma: float = 2.0, sl_atr_carpani: float = 1.5,
                             risk_odul_orani: float = 1.5, sinyal_tersine_cikis: bool = False,
                             kapanis_bazli_atr: bool = False) -> dict:
    yon_serisi = _yon_serisi_mean_reversion(df, periyot, sapma)
    islemler = _pozisyon_simulasyonu(df, yon_serisi, sl_atr_carpani, risk_odul_orani, sinyal_tersine_cikis, kapanis_bazli_atr)
    return _ozet_hesapla(islemler)


def parite_dolar_pnl_hesapla(islemler, xau_df, xag_df, lot: float = 0.01) -> dict:
    """Rasyo-bazli islemleri, gercek XAUUSD+XAGUSD (0.01 lot her bacak)
    dolar P&L'ine cevirir - boylece farkli hesap bakiyelerine gore kar
    marjini (% getiri) hesaplanabilir."""
    dolar_islemler = []
    for t in islemler:
        i_giris, i_cikis = t["giris_i"], t["cikis_i"]
        xau_giris, xau_cikis = xau_df["close"].iloc[i_giris], xau_df["close"].iloc[i_cikis]
        xag_giris, xag_cikis = xag_df["close"].iloc[i_giris], xag_df["close"].iloc[i_cikis]

        xau_isareti = 1 if t["yon"] == "AL" else -1   # AL -> XAU AL
        xag_isareti = -1 if t["yon"] == "AL" else 1   # AL -> XAG SAT

        xau_pnl = (xau_cikis - xau_giris) * xau_isareti * lot * XAU_KONTRAT_BUYUKLUGU
        xag_pnl = (xag_cikis - xag_giris) * xag_isareti * lot * XAG_KONTRAT_BUYUKLUGU
        dolar_islemler.append({**t, "xau_pnl_usd": xau_pnl, "xag_pnl_usd": xag_pnl, "toplam_pnl_usd": xau_pnl + xag_pnl})

    toplam_dolar = sum(t["toplam_pnl_usd"] for t in dolar_islemler)
    return {
        "toplam_pnl_usd": round(toplam_dolar, 2),
        "islem_basi_ort_usd": round(toplam_dolar / len(dolar_islemler), 2) if dolar_islemler else 0.0,
        "islemler": dolar_islemler,
    }


def tek_bacak_backtest(sinyal_df, izlenen_df, esik: int = 4, sl_atr_carpani: float = 1.5,
                        risk_odul_orani: float = 1.5, sinyal_tersine_cikis: bool = True) -> dict:
    """Yonu RASYODAN uretir ama sadece TEK bacagin fiyat hareketini takip
    ederek P&L olcer - 'iki bacak yerine tek bacak tutsaydik ne olurdu'
    karsilastirmasi icin."""
    ortak_zaman = sinyal_df.index.intersection(izlenen_df.index)
    sinyal_df = sinyal_df.loc[ortak_zaman]
    izlenen_df = izlenen_df.loc[ortak_zaman]

    yon_serisi = _yon_serisi_confluence(sinyal_df, esik)
    islemler = _pozisyon_simulasyonu(izlenen_df, yon_serisi, sl_atr_carpani, risk_odul_orani, sinyal_tersine_cikis)
    return _ozet_hesapla(islemler)
