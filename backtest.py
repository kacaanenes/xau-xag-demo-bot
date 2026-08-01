"""XAU/XAG parite stratejilerini gecmis veride GERCEK DOLAR P&L'i uzerinden
olcer - varsayim degil, olcum. Birden fazla strateji varyanti (confluence
esikleri, farkli risk/odul, mean-reversion) ayni harness ile test edilip
karsilastirilabilir."""
from __future__ import annotations

import teknik

ISINMA_BARI = 50  # ilk N bar, gostergelerin (EMA50 vb.) kararlilik kazanmasi icin atlanir
XAU_KONTRAT_BUYUKLUGU = 100  # oz/lot
XAG_KONTRAT_BUYUKLUGU = 5000  # oz/lot


_TUM_GOSTERGELER = ("EMA", "MACD", "RSI", "SuperTrend", "MOST", "Bollinger")


def _yon_serisi_confluence(df, esik: int = 4, gostergeler: tuple = _TUM_GOSTERGELER):
    """gostergeler: hangi oylarin dahil edilecegini secmek icin - bazi
    gostergeler birbiriyle yuksek korelasyonlu (ornegin RSI-Bollinger 0.79),
    yani '6 bagimsiz oy' degil, kismen ayni sinyalin tekrari. Bunu test
    etmek icin alt kumeler denenebilir."""
    kapanis = df["close"]
    ema20 = teknik.ema_serisi(kapanis, 20)
    ema50 = teknik.ema_serisi(kapanis, 50)
    rsi = teknik.rsi_serisi(kapanis, 14)
    macd_cizgisi, macd_sinyal = teknik.macd_hesapla(kapanis)
    orta_bant, _, _ = teknik.bollinger_hesapla(kapanis, 20, 2.0)
    st_df = teknik.supertrend_hesapla(df, 10, 3.0)
    most_df = teknik.most_hesapla(kapanis, 9, 2.0)

    tum_oylar = {
        "EMA": ema20 > ema50,
        "MACD": macd_cizgisi > macd_sinyal,
        "RSI": rsi > 50,
        "SuperTrend": st_df["yukselis_mi"],
        "MOST": most_df["yukselis_mi"],
        "Bollinger": kapanis > orta_bant,
    }
    secili_oylar = [tum_oylar[g] for g in gostergeler]
    n = len(secili_oylar)

    yonler = []
    for i in range(len(df)):
        yukselis_oyu = sum(bool(oy.iloc[i]) for oy in secili_oylar)
        dusus_oyu = n - yukselis_oyu
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
                           kapanis_bazli_atr: bool = False,
                           basabas_r: float | None = None, iz_atr_carpani: float | None = None,
                           izinli_saatler: range | tuple | None = None,
                           kotu_saatte_kari_al: bool = False):
    """basabas_r: kar, baslangic riskinin bu katina ulasinca stop girise
    cekilir (o andan sonra islem en kotu basabas kapanir).
    iz_atr_carpani: stop, fiyatin bu kadar ATR gerisini izler (iz suren
    stop). Ikisi de None ise klasik sabit stop/hedef davranisi korunur.

    UYARI: iz suren stop sezgisel olarak "kari korur" gibi gorunse de
    kazanan islemleri erken kesip toplam getiriyi DUSUREBILIR - bu yuzden
    varsayilan olarak KAPALI, acmadan once backtest ile karsilastirilmali."""
    kapanis = df["close"]
    atr = teknik.atr_kapanis_bazli(kapanis, 14) if kapanis_bazli_atr else teknik.atr_serisi(df, 14)

    islemler = []
    pozisyon = None

    for i in range(ISINMA_BARI, len(df)):
        fiyat = kapanis.iloc[i]

        if pozisyon is not None:
            # Stop'u yukari/asagi cek (asla ters yone gevsetme)
            if basabas_r is not None or iz_atr_carpani is not None:
                r = pozisyon["baslangic_riski"]
                if pozisyon["yon"] == "AL":
                    if basabas_r is not None and fiyat >= pozisyon["giris_fiyat"] + basabas_r * r:
                        pozisyon["stop"] = max(pozisyon["stop"], pozisyon["giris_fiyat"])
                    if iz_atr_carpani is not None:
                        pozisyon["stop"] = max(pozisyon["stop"], fiyat - iz_atr_carpani * atr.iloc[i])
                else:
                    if basabas_r is not None and fiyat <= pozisyon["giris_fiyat"] - basabas_r * r:
                        pozisyon["stop"] = min(pozisyon["stop"], pozisyon["giris_fiyat"])
                    if iz_atr_carpani is not None:
                        pozisyon["stop"] = min(pozisyon["stop"], fiyat + iz_atr_carpani * atr.iloc[i])

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

            # Kotu seansa girerken kari al: islem penceresi disina cikildiysa
            # VE pozisyon kardaysa kapat. Zarardaysa DOKUNMA - zarari
            # gerceklestirmek yerine stop/hedefe sansi kalsin.
            if not tetiklendi and kotu_saatte_kari_al and izinli_saatler is not None \
                    and df.index[i].hour not in izinli_saatler:
                kardaysa = (fiyat > pozisyon["giris_fiyat"]) if pozisyon["yon"] == "AL" else (fiyat < pozisyon["giris_fiyat"])
                if kardaysa:
                    tetiklendi, sebep = True, "kotu_saatte_kar_alindi"

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
                    # R-katsayisi (kar/zararin baslangic riskine orani) ve
                    # hesap dususu hesaplari icin gerekli - sadece kayit.
                    "stop_mesafesi": pozisyon["baslangic_riski"],
                    "getiri_yuzde": (fiyat / pozisyon["giris_fiyat"] - 1) * 100 * yon_isareti,
                })
                pozisyon = None

        # Saat filtresi SADECE yeni giriste uygulanir - acik pozisyon,
        # izinli saat disina cikilsa bile kendi stop/hedefine kadar yonetilir.
        if izinli_saatler is not None and df.index[i].hour not in izinli_saatler:
            continue

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
            pozisyon = {"yon": yon_serisi[i], "giris_fiyat": fiyat, "stop": stop, "hedef": hedef,
                        "giris_i": i, "baslangic_riski": stop_mesafesi}

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
                         sinyal_tersine_cikis: bool = True, kapanis_bazli_atr: bool = False,
                         gostergeler: tuple = _TUM_GOSTERGELER, basabas_r: float | None = None,
                         iz_atr_carpani: float | None = None, izinli_saatler=None,
                             kotu_saatte_kari_al: bool = False) -> dict:
    yon_serisi = _yon_serisi_confluence(df, esik, gostergeler)
    islemler = _pozisyon_simulasyonu(df, yon_serisi, sl_atr_carpani, risk_odul_orani, sinyal_tersine_cikis,
                                      kapanis_bazli_atr, basabas_r, iz_atr_carpani, izinli_saatler, kotu_saatte_kari_al)
    return _ozet_hesapla(islemler)


def mean_reversion_backtest(df, periyot: int = 20, sapma: float = 2.0, sl_atr_carpani: float = 1.5,
                             risk_odul_orani: float = 1.5, sinyal_tersine_cikis: bool = False,
                             kapanis_bazli_atr: bool = False, basabas_r: float | None = None,
                             iz_atr_carpani: float | None = None, izinli_saatler=None,
                             kotu_saatte_kari_al: bool = False) -> dict:
    yon_serisi = _yon_serisi_mean_reversion(df, periyot, sapma)
    islemler = _pozisyon_simulasyonu(df, yon_serisi, sl_atr_carpani, risk_odul_orani, sinyal_tersine_cikis, kapanis_bazli_atr, basabas_r, iz_atr_carpani, izinli_saatler, kotu_saatte_kari_al)
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
