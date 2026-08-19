"""Her bacak icin ATR bazli stop-loss / kar-al hesaplar. Minimum risk
felsefesi: sabit kucuk lot + dar stop."""
from __future__ import annotations

import teknik

SL_ATR_CARPANI = 1.5
RISK_ODUL_ORANI = 1.5

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

# UST SINIR - felaket freni.
# Lot formulunun paydasinda stop mesafesi var; stop sifira yaklasirsa lot
# sinirsiz buyur. OLCULDU (1000 bar): normal sartlarda nominal buyukluk
# ozsermayenin XAGUSD'de en fazla 2.71 kati, XAUUSD'de 5.05 kati, AUDNZD'de
# ~7.0 kati oluyor. 10x tavani gercek veride HIC devreye girmiyor - sadece
# bozuk ATR / anormal dusuk volatilite durumunda emri makul seviyede tutar.
# Bu tavan olmadan stop %0.001'e duserse 100k hesapta 200 lot (57 milyon
# dolar nominal) emri denenirdi.
AZAMI_KALDIRAC = 10.0


def lot_hesapla(stop_mesafesi_fiyat: float, kontrat_buyuklugu: float, bakiye: float,
                 risk_yuzdesi: float = RISK_YUZDESI, kur_carpani: float = 1.0,
                 fiyat: float | None = None, azami_lot_broker: float | None = None) -> float:
    """kur_carpani: sembolun KAR para birimini hesap para birimine ceviren
    carpan (mt5_veri.kar_kuru_carpani'ndan gelir).

    fiyat / azami_lot_broker: ust sinir kontrolleri icin. Ikisi de None ise
    sinir uygulanmaz (eski davranis) - bu yuzden CANLI kodda ikisinin de
    gecilmesi gerekir, backtest'te gerekmez.

    stop_mesafesi x kontrat_buyuklugu carpimi, sembolun kar para biriminde
    cikar - hesap para biriminde DEGIL. XAUUSD/XAGUSD'de ikisi de USD oldugu
    icin carpan 1.0 ve hicbir sey degismez. AUDNZD'de carpim NZD cinsinden
    olusur ve carpan olmadan gercek risk hedeflenenin ~%59'u kadar kalir -
    bkz. mt5_veri.kar_kuru_carpani'ndaki olcum."""
    if stop_mesafesi_fiyat <= 0:
        return MIN_LOT
    hedef_risk = bakiye * risk_yuzdesi
    lot_basi_zarar = stop_mesafesi_fiyat * kontrat_buyuklugu * kur_carpani
    if lot_basi_zarar <= 0:
        return MIN_LOT
    lot_ham = hedef_risk / lot_basi_zarar

    # UST SINIR 1 - kaldirac tavani. Nominal buyukluk = lot x kontrat x fiyat,
    # kur_carpani ile hesap para birimine cevrilir (AUDNZD'de nominal NZD
    # cinsinden cikar, dolara cevrilmesi gerekir).
    if fiyat is not None and fiyat > 0:
        azami_nominal = bakiye * AZAMI_KALDIRAC
        lot_tavani = azami_nominal / (kontrat_buyuklugu * fiyat * kur_carpani)
        if lot_ham > lot_tavani:
            print(f"  UYARI: lot {lot_ham:.2f} -> {lot_tavani:.2f} (kaldirac tavani {AZAMI_KALDIRAC:.0f}x). "
                  f"Stop mesafesi anormal dar olabilir ({stop_mesafesi_fiyat:.5f}).")
            lot_ham = lot_tavani

    # UST SINIR 2 - brokerin kendi azami hacmi (teknik sinir).
    if azami_lot_broker is not None and lot_ham > azami_lot_broker:
        print(f"  UYARI: lot {lot_ham:.2f} -> {azami_lot_broker:.2f} (broker azami hacmi).")
        lot_ham = azami_lot_broker

    lot = round(lot_ham / LOT_ADIMI) * LOT_ADIMI
    return max(round(lot, 2), MIN_LOT)


def broker_sinirina_uydur(giris: float, stop: float, hedef: float, alis_mi: bool,
                           asgari_stop: float, basamak: int = 5) -> dict:
    """Stop/hedef, brokerin asgari mesafesinden yakinsa ikisini de genisletir.

    NEDEN: MT5 brokerleri stop/hedefin guncel fiyata cok yakin olmasina izin
    vermez (stopsLevel). Ihlal edilirse emrin TAMAMI reddedilir - yani sinyal
    kacar. Duz reddedilmektense mesafeyi asgariye cekip islem acmak daha iyi.

    RISK/ODUL ORANI KORUNUR: stop genisletilirken hedef de ayni oranda
    genisletilir, boylece olculen 1:2 (metaller) / 1:1.5 (AUDNZD) geometrisi
    bozulmaz.

    DIKKAT: stop genisledigi icin LOT YENIDEN HESAPLANMALI - yoksa risk %1'i
    asar. Cagiran kod donen 'stop_mesafesi' degerini kullanmali.

    MetaQuotes-Demo'da asgari_stop = 0, yani bu fonksiyon hicbir sey yapmaz."""
    stop_mesafesi = abs(giris - stop)
    hedef_mesafesi = abs(hedef - giris)

    if asgari_stop <= 0 or stop_mesafesi >= asgari_stop:
        return {"stop_loss": round(stop, basamak), "take_profit": round(hedef, basamak),
                "stop_mesafesi": stop_mesafesi, "genisletildi": False}

    oran = hedef_mesafesi / stop_mesafesi if stop_mesafesi > 0 else RISK_ODUL_ORANI
    yeni_stop_mesafesi = asgari_stop
    yeni_hedef_mesafesi = oran * yeni_stop_mesafesi

    if alis_mi:
        yeni_stop, yeni_hedef = giris - yeni_stop_mesafesi, giris + yeni_hedef_mesafesi
    else:
        yeni_stop, yeni_hedef = giris + yeni_stop_mesafesi, giris - yeni_hedef_mesafesi

    print(f"  Stop mesafesi {stop_mesafesi:.5f} -> {yeni_stop_mesafesi:.5f} "
          f"(brokerin asgari stop mesafesi). Risk/odul 1:{oran:.1f} korundu, "
          f"lot yeni mesafeye gore hesaplanacak.")
    return {"stop_loss": round(yeni_stop, basamak), "take_profit": round(yeni_hedef, basamak),
            "stop_mesafesi": yeni_stop_mesafesi, "genisletildi": True}


def stop_ve_hedef_hesapla(df, giris_fiyati: float, alis_mi: bool, atr_carpani: float = SL_ATR_CARPANI,
                           risk_odul_orani: float = RISK_ODUL_ORANI, kapanis_bazli_atr: bool = True) -> dict:
    """kapanis_bazli_atr - DIKKAT, varsayilan (True) ARTIK GECERLI DEGIL.

    Bu varsayilan, emekli parite (XAU/XAG rasyosu) botu icin dogruydu:
    orada high/low iki ayri enstrumanin teorik birlesimiydi, gercek bar-ici
    aralik degildi. CANLI tek-enstruman botlari bunu ACIKCA False geciyor
    (bkz. tek_enstruman.py'deki kapanis_bazli_atr aciklamasi): XAGUSD ve
    XAUUSD'nin gercek yuksek/dusuk verisi var ve kapanis-bazli ATR gercek
    dalgalanmayi yarisi kadar olcup stoplari asiri daraltiyordu.

    Varsayilan degistirilmedi cunku onu kullanan emekli kod (emir.py) hala
    duruyor - ama YENI cagirilarda deger ACIKCA gecilmeli.

    risk_odul_orani da artik parametre: modul sabitine (1.5) sabitlenmisti,
    botun kendi ayari (metallerde 2.0) hic kullanilmiyordu."""
    atr = (teknik.atr_kapanis_bazli(df["close"], 14) if kapanis_bazli_atr
           else teknik.atr_serisi(df, 14)).iloc[-1]
    stop_mesafesi = atr_carpani * atr
    hedef_mesafesi = risk_odul_orani * stop_mesafesi

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
