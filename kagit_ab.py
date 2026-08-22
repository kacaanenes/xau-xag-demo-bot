"""KAGIT TAKIP - A+B birlesik sistemi (XAUUSD, 8 saatlik).

Gercek emir GONDERMEZ. Sadece sinyalleri ve varsayimsal islemleri kaydeder.
Amac: hesap acmadan once sistemi canli veriyle takip etmek.

--------------------------------------------------------------------------
SISTEM
--------------------------------------------------------------------------
A  Donchian55 kirilimi -> SADECE AL
   (kapanis, onceki 55 barin en yuksegini asarsa)
B  Volatilite soku + trend uyumu -> IKI YON
   (barin gercek araligi son 100 barin medyaninin 2 katini asarsa VE
    mum yonu 24 saatlik EMA50 trendiyle uyumluysa)

Ikisi de: stop 1.5 x ATR(14), hedef YOK, iz suren stop 4.0 x ATR.
Ikisi AYNI ANDA acik olabilir - ayri ayri takip edilir.

--------------------------------------------------------------------------
NEDEN HER TURDA YENIDEN HESAPLIYOR (durum biriktirmiyor)
--------------------------------------------------------------------------
Bot 15 dakikada bir calisiyor ama GitHub Actions calistirma ATLIYOR -
olculdu (19.08.2026): beklenen ~88 tetiklemeden 14'u gerceklesti, iki
tetikleme arasi ortalama 93 dakika, en uzunu 202 dakika.

Durum biriktiren bir tasarimda (her turda "yeni bar var mi" diye bakip
uzerine eklemek) atlanan tur, kacan sinyal demek olurdu. Bu modul bunun
yerine HER TURDA son 125 gunu bastan simule ediyor: sonuc yalnizca
VERIYE bagli, kac tur atlandigina bagli degil. Ayni girdi her zaman ayni
ciktiyi verir.

Kapanmis islemler ayrica JSONL'e yaziliyor - bu sadece bildirim tekrarini
onlemek ve gecmisi biriktirmek icin; hesabin dogrulugu ona bagli degil.

--------------------------------------------------------------------------
OLCULEN BEKLENTI (14.7 yil, XAUUSD, spread 0.30, %0.5 risk/islem)
--------------------------------------------------------------------------
  362 islem  hesap +%201  azami dusus %8  ileriye yuruyen +%176
  15 yilin 12'si pozitif, en kotu yil -%3
  plato: 20 parametre hucresinin 20'si pozitif (medyan +%165)
  maliyet: spread x5'te bile +%163
  bootstrap: %5 dilimi +%82, negatif tur %0.0

UYARI - kazanc REJIME bagli:
  1. yari (2012-2019) +%18   |  2. yari (2019-2026) +%155
  Islem sayisi ayni (179 vs 183), degisen sey islem basi kazanc:
  AL islemlerinde +0.312R -> +1.713R.
  Sistem uzun ve kesintisiz trendlerden yasiyor. Altin sikisirsa yilda
  %1-5, trend yaparsa %10-40 beklenmeli. Kotu rejimde de KAYBETMIYOR:
  2013'te altin -%28 iken sistem +%3.4, 2015'te altin -%11 iken -%3.1.

--------------------------------------------------------------------------
GERCEKCILIK - NE MODELLENIYOR, NE MODELLENMIYOR
--------------------------------------------------------------------------
MODELLENEN (gercek islemle ayni):
  - brokerin GERCEK canli fiyat verisi
  - bar-ici stop tespiti (bar kapanisi degil, gercek yuksek/dusuk)
  - BOSLUK GERCEKCI dolum: stopun otesinde acilan bar, stop fiyatindan
    DEGIL acilis fiyatindan doldurur (hafta sonu/haber bosluklari)
  - islem maliyeti: her isleme SPREAD (0.30) dusulur
  - iz suren stop yalnizca bar KAPANISINDA guncellenir
  - pozisyon acikken yeni sinyal alinmaz

MODELLENMEYEN (kagit sonuc bu kadar IYIMSER):
  1. GIRIS GECIKMESI. Giris, barin KAPANIS fiyatindan varsayiliyor. Gercek
     bot bar kapanisindan 15 dakikaya kadar sonra calisiyor ve o anki
     fiyattan giriyor. Olculdu: 1 barlik (8 saat) gecikme +%201'i +%110'a
     dusuruyor; 15 dakika bunun ~otuz ikide biri, yani etki kucuk ama SIFIR
     DEGIL.
  2. KAYMA (slippage). Stop emirleri tam stop fiyatindan dolduruluyor
     varsayiliyor. Demo hesapta olculdu: 24 cikisin 24'unde kayma sifir -
     ama gercek brokerde stop emirleri seviyeyi asarak dolar.
  3. LOT YUVARLAMA. Risk saf R olarak hesaplaniyor; gercekte lot 0.01
     adimlarla yuvarlanir ve asgari lot sinirl vardir. Kucuk hesaplarda
     bu, hedeflenen riskten sapma yaratir.
  4. KOMISYON. MetaQuotes-Demo'da yok; gercek brokerde olabilir.
  5. MARJ / KALDIRAC SINIRI. Kagit takipte pozisyon her zaman acilabilir.

Yani kagit sonuc, gercek sonucun UST SINIRI olarak okunmali. Farkin
buyuk kismi giris gecikmesinden gelir.

SADECE demo/kagit takip icindir - gercek emir gondermez.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib

import pandas as pd

import mt5_veri
import teknik
import telegram_bildirim

SEMBOL = "XAUUSD"
BAR_SAATI = 8
HAM_BAR = 4000          # ~500 adet 8 saatlik bar = ~166 gun

# KAGIT TAKIBIN BASLANGICI - SABIT. Simulasyon bu tarihten oncesini sadece
# ISINMA icin kullanir, islem saymaz.
#
# NEDEN SABIT (kayan pencere DEGIL) - olculdu:
# Ilk tasarim her turda "son N bar"i simule ediyordu. Pencere kaydikca
# isinma siniri da kayiyor; sinirin uzerinde ACIK bir pozisyon varsa kisa
# pencere bosta baslayip gercek sistemin ALMAYACAGI bir sinyali aliyor.
# Test: 600 barlik pencere 2 islem uretti, tam veri ayni donemde 1 - yani
# fazladan bir islem uydurdu.
# Sabit capa ile isinma bolgesi hic hareket etmiyor, sonuc her turda ayni.
BASLANGIC = "2026-08-22"
DONCHIAN = 55
SOK_CARPANI = 2.0
SOK_PENCERE = 100
STOP_ATR = 1.5
IZ_ATR = 4.0

# ISLEM MALIYETI - her kagit isleme uygulanir.
# XAUUSD spread'i 71 olcumle saat saat cikarildi: tum gun medyani 0.30,
# aralik 0.09-0.51 (en ucuz 05-07 ve 18 UTC'de 0.12-0.14, en pahali
# 20-21 UTC rollover'inda 0.44). Backtest de 0.30 kullandi; kagit takip
# ayni sayiyi kullanmali yoksa sonuclar olculen beklentiden IYI gorunur.
SPREAD = 0.30
RISK_YUZDESI = 0.005
BASLANGIC_BAKIYE = 100_000.0

_ETIKET = os.getenv("HESAP_ETIKETI", "")
KAYIT = pathlib.Path(__file__).parent / f"kagit_ab{_ETIKET}.jsonl"


def _sekiz_saatlik(ham: pd.DataFrame) -> pd.DataFrame:
    """Tamamlanmamis son bar ATILIR - sinyal her zaman kapanmis bardan."""
    df = ham.resample(f"{BAR_SAATI}h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    if len(df) and df.index[-1] + pd.Timedelta(hours=BAR_SAATI) > dt.datetime.now(dt.timezone.utc):
        df = df.iloc[:-1]
    return df


def sinyaller(df: pd.DataFrame) -> tuple[list, list]:
    """(A sinyalleri, B sinyalleri) - her bar icin 'AL'/'SAT'/None."""
    kap = df["close"].values
    acilis = df["open"].values
    don_yuksek = df["high"].rolling(DONCHIAN).max().shift(1).values

    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - df["close"].shift(1)).abs(),
                    (df["low"] - df["close"].shift(1)).abs()], axis=1).max(axis=1)
    sok = (tr > SOK_CARPANI * tr.rolling(SOK_PENCERE).median()).values

    gunluk = df["close"].resample("24h").last().dropna()
    ema24 = (gunluk.ewm(span=50, adjust=False).mean().shift(1)
             .reindex(df.index, method="ffill").values)

    a, b = [], []
    for i in range(len(df)):
        a.append("AL" if (don_yuksek[i] == don_yuksek[i] and kap[i] > don_yuksek[i]) else None)
        if not sok[i] or ema24[i] != ema24[i]:
            b.append(None)
        elif kap[i] > acilis[i] and kap[i] > ema24[i]:
            b.append("AL")
        elif kap[i] < acilis[i] and kap[i] < ema24[i]:
            b.append("SAT")
        else:
            b.append(None)
    return a, b


def simule(df: pd.DataFrame, yon: list, kaynak: str) -> tuple[list, dict | None]:
    """Deterministik simulasyon. (kapanmis islemler, acik pozisyon) doner.

    Motor, backteste BIREBIR ayni: bar-ici stop, bosluk gercekci dolum
    (stopun otesinde acilan bar ACILISTAN doldurur), pozisyon acikken yeni
    sinyal dikkate alinmaz, iz suren stop bar kapanisinda guncellenir."""
    kap, ac = df["close"].values, df["open"].values
    yuk, dus = df["high"].values, df["low"].values
    atr = teknik.atr_serisi(df, 14).values
    idx = df.index
    kapanan, poz = [], None

    for i in range(DONCHIAN + 60, len(df)):
        if poz is not None:
            s = poz["isaret"]
            vurdu = (dus[i] <= poz["stop"]) if s > 0 else (yuk[i] >= poz["stop"])
            if vurdu:
                cikis = poz["stop"]
                if (s > 0 and ac[i] < cikis) or (s < 0 and ac[i] > cikis):
                    cikis = ac[i]
                kapanan.append({
                    "kaynak": kaynak, "yon": poz["yon"],
                    "giris_zaman": poz["zaman"].isoformat(), "giris": round(poz["giris"], 3),
                    "cikis_zaman": idx[i].isoformat(), "cikis": round(float(cikis), 3),
                    # Spread DUSULUR - backtest de boyle olculdu (+%201
                    # rakami spread 0.30 dahildi). Dusulmezse kagit sonuc
                    # olculen beklentiden iyi gorunur.
                    "R": round((cikis - poz["giris"]) * s / poz["risk"] - SPREAD / poz["risk"], 4),
                    "R_ham": round((cikis - poz["giris"]) * s / poz["risk"], 4),
                    "bar": i - poz["i"],
                })
                poz = None
            else:
                yeni = kap[i] - s * IZ_ATR * atr[i]
                poz["stop"] = max(poz["stop"], yeni) if s > 0 else min(poz["stop"], yeni)
            continue
        if yon[i] is None:
            continue
        a = atr[i]
        if a != a or a <= 0:
            continue
        s = 1 if yon[i] == "AL" else -1
        risk = STOP_ATR * a
        poz = {"isaret": s, "yon": yon[i], "risk": risk, "giris": float(kap[i]),
               "i": i, "zaman": idx[i], "stop": float(kap[i]) - s * risk}

    acik = None
    if poz is not None:
        acik = {"kaynak": kaynak, "yon": poz["yon"],
                "giris_zaman": poz["zaman"].isoformat(), "giris": round(poz["giris"], 3),
                "stop": round(poz["stop"], 3), "risk": round(poz["risk"], 3),
                "bar": len(df) - 1 - poz["i"]}
    return kapanan, acik


def _bilinen_kapanislar() -> set:
    if not KAYIT.exists():
        return set()
    bilinen = set()
    for satir in KAYIT.read_text().splitlines():
        if not satir.strip():
            continue
        try:
            k = json.loads(satir)
            bilinen.add((k["kaynak"], k["giris_zaman"], k["cikis_zaman"]))
        except (json.JSONDecodeError, KeyError):
            continue
    return bilinen


def ozet() -> dict | None:
    """Kaydedilmis kagit islemlerin ozeti."""
    if not KAYIT.exists():
        return None
    islemler = []
    for satir in KAYIT.read_text().splitlines():
        if satir.strip():
            try:
                islemler.append(json.loads(satir))
            except json.JSONDecodeError:
                continue
    if not islemler:
        return None
    bakiye = BASLANGIC_BAKIYE
    tepe = bakiye
    dusus = 0.0
    for x in sorted(islemler, key=lambda z: z["cikis_zaman"]):
        bakiye *= (1 + x["R"] * RISK_YUZDESI)
        tepe = max(tepe, bakiye)
        dusus = max(dusus, (tepe - bakiye) / tepe * 100)
    kazanan = sum(1 for x in islemler if x["R"] > 0)
    return {"islem": len(islemler), "isabet": kazanan / len(islemler) * 100,
            "toplam_R": sum(x["R"] for x in islemler), "bakiye": bakiye,
            "getiri": (bakiye / BASLANGIC_BAKIYE - 1) * 100, "dusus": dusus}


async def calistir() -> None:
    ham = await mt5_veri.cok_barli_getir(SEMBOL, "1h", HAM_BAR)
    df = _sekiz_saatlik(ham)
    gerekli = DONCHIAN + 80
    if len(df) < gerekli:
        print(f"KAGIT A+B: yeterli {BAR_SAATI} saatlik bar yok ({len(df)} < {gerekli}) - atlaniyor.")
        return

    a_yon, b_yon = sinyaller(df)
    a_kapanan, a_acik = simule(df, a_yon, "A")
    b_kapanan, b_acik = simule(df, b_yon, "B")

    # SABIT CAPA: baslangictan onceki islemler sadece isinmaydi, sayilmaz.
    capa = pd.Timestamp(BASLANGIC, tz="UTC")
    a_kapanan = [x for x in a_kapanan if pd.Timestamp(x["giris_zaman"]) >= capa]
    b_kapanan = [x for x in b_kapanan if pd.Timestamp(x["giris_zaman"]) >= capa]
    # Capadan ONCE acilmis pozisyonlar kagit islem SAYILMAZ ama yeni girisi
    # ENGELLER (pozisyon acikken yeni sinyal alinmaz kurali). Gorunur
    # birakiliyor ki "sinyal var ama giris yok" durumu aciklanabilsin.
    a_isinma = bool(a_acik) and pd.Timestamp(a_acik["giris_zaman"]) < capa
    b_isinma = bool(b_acik) and pd.Timestamp(b_acik["giris_zaman"]) < capa

    son = df.index[-1]
    print(f"KAGIT A+B ({SEMBOL} {BAR_SAATI}h) | guncel {ham['close'].iloc[-1]:.2f} | "
          f"son kapanmis bar {son.strftime('%d.%m %H:%M')} @ {df['close'].iloc[-1]:.2f} | "
          f"{len(df)} bar penceresi")
    print(f"  bu barin sinyalleri: A={a_yon[-1] or 'yok'}  B={b_yon[-1] or 'yok'}"
          f"  | kagit takip baslangici {BASLANGIC}")

    # YENI KAPANISLARI BILDIR (kayittaki ile karsilastirarak)
    bilinen = _bilinen_kapanislar()
    yeni = [x for x in (a_kapanan + b_kapanan)
            if (x["kaynak"], x["giris_zaman"], x["cikis_zaman"]) not in bilinen]
    ilk_calistirma = not KAYIT.exists()

    with open(KAYIT, "a") as f:
        for x in sorted(yeni, key=lambda z: z["cikis_zaman"]):
            f.write(json.dumps(x) + "\n")

    if ilk_calistirma:
        # Ilk calistirmada pencerede ne varsa hepsi "yeni" gorunur; bunlari
        # bildirmek Telegram'i doldurur. Sessizce kaydedilir.
        print(f"  ILK CALISTIRMA - {len(yeni)} gecmis islem sessizce kaydedildi.")
    else:
        for x in sorted(yeni, key=lambda z: z["cikis_zaman"]):
            kz = x["R"] * RISK_YUZDESI * BASLANGIC_BAKIYE
            print(f"  KAGIT KAPANIS: {x['kaynak']} {x['yon']} {x['giris']} -> {x['cikis']} "
                  f"= {x['R']:+.2f}R")
            telegram_bildirim.pozisyon_kapandi(
                f"[KAGIT] {SEMBOL} ({x['kaynak']})", x["yon"], kz,
                f"iz suren stop | {x['R']:+.2f}R | {x['bar']} bar")

    for etiket, acik, isinma in (("A", a_acik, a_isinma), ("B", b_acik, b_isinma)):
        if acik is None:
            print(f"  {etiket}: pozisyon yok")
            continue
        anlik = float(ham["close"].iloc[-1])
        isaret = 1 if acik["yon"] == "AL" else -1
        kar_r = (anlik - acik["giris"]) * isaret / acik["risk"]
        if isinma:
            print(f"  {etiket}: ISINMA pozisyonu {acik['yon']} @ {acik['giris']} "
                  f"({acik['giris_zaman'][:16]}, capadan ONCE) | stop {acik['stop']} | "
                  f"{kar_r:+.2f}R -> KAGIT ISLEM SAYILMAZ, ama kapanana kadar "
                  f"yeni giris de olmaz")
        else:
            print(f"  {etiket}: KAGIT POZISYON {acik['yon']} @ {acik['giris']} | "
                  f"stop {acik['stop']} | {kar_r:+.2f}R | {acik['bar']} bar")

    o = ozet()
    if o:
        print(f"  TOPLAM KAGIT: {o['islem']} islem, isabet %{o['isabet']:.0f}, "
              f"{o['toplam_R']:+.1f}R, getiri %{o['getiri']:+.2f}, azami dusus %{o['dusus']:.1f}")
