"""DONCHIAN KIRILIMI + IZ SUREN STOP - trend takip botu.

Mevcut meanrev botlarindan TEMELDEN farkli bir aile: onlar yukselise KARSI
bahis oynar (ust banda vurunca SAT), bu ise yukselisI SATIN ALIR.

--------------------------------------------------------------------------
KURAL
--------------------------------------------------------------------------
4 SAATLIK barlarda:
  - kapanis, onceki 55 barin EN YUKSEGINI asarsa  -> AL
  - kapanis, onceki 55 barin EN DUSUGUNUN altina inerse -> SAT
  - stop: giristen 1.5 x ATR(14) uzakta
  - HEDEF YOK - stop, her 4 saatlik bar kapanisinda fiyatin 4.0 x ATR
    gerisine cekilir (sadece lehte yonde, asla geri gitmez)
  - pozisyon acikken yeni sinyal DIKKATE ALINMAZ (backtest de boyle olculdu)

--------------------------------------------------------------------------
NEDEN 4 SAAT - SPREAD MALIYETI
--------------------------------------------------------------------------
Spread SABIT bir para tutari; stop ne kadar buyukse riske orani o kadar
kucuktur. Gumuste olculdu:

    zaman dilimi   ortalama stop   spread maliyeti (islem basi)
    1 saat              0.15            0.1255 R
    4 saat              0.469           0.0405 R
    8 saat              0.674           0.0282 R
    gunluk              1.125           0.0169 R

Saatlik meanrev botu her islemde ham beklentisinin (+0.038R) UC KATI kadar
maliyet oduyordu. Sistemin 15 yillik veride kaybetmesinin tek basina
yeterli sebebi buydu.

--------------------------------------------------------------------------
OLCUM (18.1 / 17.8 yil, DELIKSIZ veri, GERCEK spread, bosluk dolumu
       gercekci, ayni barda yeniden giris yok)
--------------------------------------------------------------------------
                islem  isabet   net R   hesap%  dusus%  ileriye%  son5yil
  XAUUSD          465    %27   +0.1220   +54.5    30.2     +71.5    +36.8
  XAGUSD          453    %30   +0.2423  +155.7    29.7     +92.0    +17.8
  ikisi birlikte  918                   +113.3    26.1   (islem basi %0.5 risk)

Isabet %27-30 - islemlerin cogu zarar eder, para birkac buyuk hareketten
gelir. Ust uste 5-6 zarar NORMALDIR.

--------------------------------------------------------------------------
UC OLCUM DUZELTMESI - onceki rakamlar (+%217.1 / +%147.8) YANLISTI
--------------------------------------------------------------------------
1) BOSLUK DOLUMU: ilk olcum +%430 / +%400 demisti. Hafta sonu ve haber
   bosluklarinda emir stop fiyatindan DEGIL acilis fiyatindan dolar.

2) AYNI BARDA YENIDEN GIRIS: motor stop yedikten sonra ayni barda tekrar
   girebiliyordu; canli bot bunu bar_kilidi ile engelliyor. Hizalandi.

3) EKSIK VERI (11.08.2026 - EN BUYUGU):
   cok_barli_getir() BAR SAYISINA gore geriye gidiyordu; MetaApi arali bir
   parca dondurunce imlec siciriyor ve atlanan pencere BIR DAHA
   istenmiyordu. Sonuc: 18 yillik seride 210 tane 60+ saatlik delik, en
   buyugu 554 saat (23 gun).
   OLCULDU: deliklerin ortasi ACIKCA istendiginde MetaApi veriyi
   DONDURUYOR (3 delikte de 100/100 bar geldi) - yani kayip kaynakta
   degil, yontemdeydi.
   ZAMAN PENCERESIYLE yeniden cekilince:
     XAUUSD  59.941 -> 106.077 bar,  delik 210 -> 42,  en buyuk 554s -> 86s
     XAGUSD  59.941 -> 104.147 bar,  delik 192 -> 41,  en buyuk 483s -> 98s
   Ayni kurulum, ayni yillar, sadece veri farki: XAUUSD +%217.1 -> +%40.2.

4) GERCEK SPREAD: model altinda 0.26 kullaniyordu. 6 ayri olcum (Londra
   seansi): medyan 0.50, aralik 0.43-0.57. Gumus 0.018 (model 0.019) ve
   AUDNZD 0.00003 (model 0.00004) modelden IYI, degistirilmedi.

--------------------------------------------------------------------------
NEDEN D55 / iz 4.0  (onceki D20 / iz 1.5 DEGIL)
--------------------------------------------------------------------------
D20/iz1.5 secimi EKSIK VERIYLE yapilmisti. Deliksiz veriyle gumuste bu,
izgaranin EN KOTU kosesi:

                        XAUUSD              XAGUSD
                   hesap%  ileriye%    hesap%  ileriye%   son5yil(XAG)
  D20 / iz 1.5      +60.1    +66.8       +3.6     -25.7      -%15.1
  D55 / iz 3.0      +42.9    +68.0     +113.3     +62.8      +%17.5
  D55 / iz 4.0      +54.5    +71.5     +155.7     +92.0      +%17.8

Altin siki iz suren stopu, gumus gevsegi seviyor. D55/iz4.0 IKISINI
BIRDEN cozuyor - enstruman basina ayri ayar gerekmiyor.

iz 3.0 da denendi: birlesik dususu daha iyi (%17.9 vs %26.1) ama bunu
getiriden (+%84.4 vs +%113.3), maliyet dayanikliligindan (altin spread
x3'te -%11 vs +%2) ve tutarliliktan (altinda 9/19 vs 12/19 pozitif yil)
feragat ederek aliyor. 4.0 secildi.

--------------------------------------------------------------------------
DAYANIKLILIK
--------------------------------------------------------------------------
PLATO: 5 periyot (20-80) x 5 iz carpani (2.0-5.0) = 25 hucrenin 23'u
IKI METALDE BIRDEN geciyor (hem toplam getiri hem ileriye yuruyen
pozitif). Bu proje boyunca gorulen en genis plato.

MALIYET (gercek spread uzerinden): altin x2 +%26, x3 +%2, x5 -%32.
Gumus x2 +%91, x3 +%43, x5 -%20. Altin daha kirilgan - olculen spread
Londra seansindan, Asya seansinda genisler.

GECIKME: 1 barlik (4 saat) gecikmede altin +%55 -> +%7, gumus +%156 ->
+%1. Bayat sinyal korumasi (0.5R) ile altin +%45, gumus +%74. Bot 15
dakikada bir calistigi icin gercek gecikme bunun ~onalti'da biri.

YIL YIL: ikisi de 12/19 pozitif. En kotu yil altin -%13, gumus -%19.

--------------------------------------------------------------------------
BILINEN ZAYIFLIKLAR
--------------------------------------------------------------------------
1. Altinin maliyet payi dar: olculen spread'in 3 katinda +%2'ye iniyor.
2. Isabet %27-30. Ust uste 5-6 zarar normaldir.
3. Iz suren stop cikislarinda KAYMA olculmedi. Demo sifir kayma veriyor;
   kayma_kaydi.py bunu biriktiriyor.
4. Bu izgaraya cok kez bakildi. Secilen hucre platonun icinde ama en iyi
   hucre degil (D80/iz2.0 altinda +%118.8 veriyor, gumuste +%52.2).
   Gercekci beklenti tablodaki rakamlardan DUSUK olmali.
5. cok_barli_getir() hala eski (atlayan) yontemi kullaniyor. Sinyal icin
   1500 bar yeterli oldugundan canlida sorun cikarmiyor, ama duzeltilmeli.

SADECE demo hesap icindir - gercek/canli hesaba asla baglanmamali.
"""
from __future__ import annotations

import asyncio
import datetime as dt

import pandas as pd

import bar_kilidi
import kapanis_bildirimi
import kayma_kaydi
import mt5_veri
import risk
import teknik
import telegram_bildirim

# Kac saatlik bar cekilecegi. Donchian20 + ATR14 icin en az ~35 dort-saatlik
# bar sart; ATR ozyinelemeli (ewm alpha=1/14) oldugu icin isinma payi genis
# tutuluyor. 1500 saatlik bar = ~375 dort-saatlik bar.
HAM_BAR_ADEDI = 1500


def dort_saatlik(ham: pd.DataFrame, saat: int = 4) -> pd.DataFrame:
    """Saatlik barlari N saatlik barlara cevirir.

    label='left', closed='left': 00:00 etiketli bar 00:00-03:59 araligini
    kapsar. Boylece bir barin degeri kendi araliginin SONUNDA olusur ve
    bar kapandiktan sonra kullanilir - gelecege bakis yok.

    (Bu proje daha once tam bu noktada hata yapti: resample("24h").last()
    varsayilan olarak kovanin etiketini basa, degerini sona koyuyor; ffill
    ile saatlik seriye yayilinca sabahki islem aksamin kapanisini goruyordu.
    Bkz. tek_enstruman.ust_trend_yukselis_mi.)

    Tamamlanmamis son bar ATILIR - sinyal her zaman KAPANMIS bardan gelir.
    """
    df = ham.resample(f"{saat}h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    if len(df) == 0:
        return df
    simdi = dt.datetime.now(dt.timezone.utc)
    if df.index[-1] + pd.Timedelta(hours=saat) > simdi:
        df = df.iloc[:-1]
    return df


def yon_serisi_donchian(df: pd.DataFrame, periyot: int = 55) -> list:
    """Kapanis, ONCEKI `periyot` barin en yuksegini asarsa AL; en dusugunun
    altina inerse SAT.

    shift(1) sart: kiyaslama kendi barini ICERMEZ, yoksa kapanis her zaman
    kendi barinin yuksegine esit ya da altinda kalir ve sinyal hic olusmaz.
    """
    yuksek = df["high"].rolling(periyot).max().shift(1)
    dusuk = df["low"].rolling(periyot).min().shift(1)
    kapanis = df["close"]
    return [None if yuksek.iloc[i] != yuksek.iloc[i] else
            ("AL" if kapanis.iloc[i] > yuksek.iloc[i] else
             "SAT" if kapanis.iloc[i] < dusuk.iloc[i] else None)
            for i in range(len(df))]


class DonchianBot:
    def __init__(self, sembol: str, kontrat_buyuklugu: float, periyot: int = 55,
                 stop_atr_carpani: float = 1.5, iz_atr_carpani: float = 4.0,
                 risk_yuzdesi: float = 0.005, bar_saati: int = 4,
                 azami_bayatlik_r: float = 0.5):
        self.sembol = sembol
        self.kontrat_buyuklugu = kontrat_buyuklugu
        # Donchian periyodu 20 -> 55 (ayni veri duzeltmesiyle). 55, iki
        # metalde de 20'den istikrarli: XAU +%42.9->+%54.5 aralikta,
        # XAG +%108.6 (D20/iz4) -> +%155.7 (D55/iz4).
        self.periyot = periyot
        self.stop_atr_carpani = stop_atr_carpani
        # Iz suren stopun fiyati kac ATR geriden takip ettigi.
        #
        # 11.08.2026 - VERI DUZELTMESINDEN SONRA 1.5 -> 4.0.
        # Onceki 1.5 secimi EKSIK VERIYLE yapilmisti (bkz. modul basligi).
        # Deliksiz veriyle gumuste 1.5 izgaranin EN KOTU kosesi:
        #   XAGUSD D20/iz1.5   hesap +%3.6   ileriye -%25.7   son 5 yil -%15.1
        #   XAGUSD D55/iz4.0   hesap +%155.7 ileriye +%92.0   son 5 yil +%17.8
        # Altin sikiyi, gumus gevsegi seviyor; D55/iz4.0 IKISINI BIRDEN
        # cozuyor, yani enstruman basina ayri ayar gerekmiyor.
        self.iz_atr_carpani = iz_atr_carpani
        # Iki enstruman ayni hesapta calistigi icin islem basi %0.5. Tekil
        # %1 ile birlesik dusus %46.6'ya cikiyordu, %0.5 ile %26.4.
        self.risk_yuzdesi = risk_yuzdesi
        self.bar_saati = bar_saati
        # Fiyat, sinyal barinin kapanisindan bu kadar R uzaklastiysa artik
        # girilmez (bkz. calistir icindeki BAYAT SINYAL KORUMASI).
        self.azami_bayatlik_r = azami_bayatlik_r

    # ---------------------------------------------------------------- veri
    async def _veri(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        ham = await mt5_veri.cok_barli_getir(self.sembol, "1h", HAM_BAR_ADEDI)
        return ham, dort_saatlik(ham, self.bar_saati)

    async def _pozisyon_getir(self) -> dict | None:
        baglanti = await mt5_veri.baglanti_al()
        pozisyonlar = await baglanti.get_positions()
        return next((p for p in pozisyonlar if p["symbol"] == self.sembol), None)

    # --------------------------------------------------------- iz suren stop
    async def _izi_guncelle(self, pozisyon: dict, df: pd.DataFrame) -> bool:
        """Stopu son KAPANMIS barin kapanisindan iz_atr_carpani x ATR geriye
        ceker. Sadece lehte yonde hareket eder - stop asla geri gitmez.

        Bot 15 dakikada bir calisir ama hesap son kapanmis bardan yapildigi
        icin ayni bar icindeki tekrar calistirmalar AYNI degeri uretir; yani
        islem tekrarsizdir, ayrica durum dosyasi gerekmez.
        """
        atr = teknik.atr_serisi(df, 14).iloc[-1]
        if atr != atr or atr <= 0:
            return False

        alis_mi = pozisyon["type"] == "POSITION_TYPE_BUY"
        isaret = 1 if alis_mi else -1
        kapanis = float(df["close"].iloc[-1])
        yeni_stop = kapanis - isaret * self.iz_atr_carpani * atr

        mevcut = pozisyon.get("stopLoss")
        if mevcut is None:
            return False
        # Sadece lehte yon: alista yukari, satista asagi.
        if (alis_mi and yeni_stop <= mevcut) or ((not alis_mi) and yeni_stop >= mevcut):
            return False

        baglanti = await mt5_veri.baglanti_al()
        fiyat = await baglanti.get_symbol_price(self.sembol)
        simdi = fiyat["bid"] if alis_mi else fiyat["ask"]
        sinir = await mt5_veri.sembol_sinirlari(self.sembol)

        # DONDURMA BOLGESI: fiyat mevcut stopa cok yakinsa broker degisiklige
        # hic izin vermez. MetaQuotes-Demo'da 0, gercek brokerde degil.
        if sinir["dondurma"] > 0 and abs(simdi - mevcut) < sinir["dondurma"]:
            print(f"  IZ ERTELENDI: fiyat stopa {abs(simdi-mevcut):.5f} uzaklikta, "
                  f"brokerin dondurma mesafesi {sinir['dondurma']:.5f}.")
            return False
        # ASGARI STOP MESAFESI: yeni stop guncel fiyata izin verilenden
        # yakinsa emir reddedilir - o zaman bu turu atla.
        if abs(simdi - yeni_stop) < sinir["asgari_stop"]:
            print(f"  IZ ERTELENDI: yeni stop guncel fiyata {abs(simdi-yeni_stop):.5f} "
                  f"uzaklikta, asgari mesafe {sinir['asgari_stop']:.5f}.")
            return False

        yeni_stop = round(yeni_stop, sinir["basamak"])
        try:
            await baglanti.modify_position(pozisyon["id"], stop_loss=yeni_stop,
                                           take_profit=None)
        except Exception as exc:  # noqa: BLE001 - iz basarisiz olsa da bot devam etmeli
            print(f"  IZ SUREN STOP BASARISIZ ({exc}) - pozisyon mevcut stopuyla devam "
                  f"ediyor, sonraki turda tekrar denenecek.")
            return False

        giris = pozisyon["openPrice"]
        korunan = (yeni_stop - giris) * isaret
        print(f"  IZ SUREN STOP: {mevcut:.5f} -> {yeni_stop:.5f} "
              f"({'kar kilitlendi' if korunan > 0 else 'zarar daraltildi'}: "
              f"{korunan:+.5f} puan)")

        # TELEGRAM SADECE ESIK GECISINDE: stop her 4 saatlik barda
        # guncelleniyor (41 saatlik ortalama pozisyonda ~10 kez). Anlamli
        # an, stopun zarar tarafindan KAR tarafina gectigi tek andir.
        # Durum dosyasi gerekmiyor - eski ve yeni stopun girise gore
        # tarafina bakmak yeterli.
        onceki_korunan = (mevcut - giris) * isaret
        if onceki_korunan <= 0 < korunan:
            telegram_bildirim.stop_kara_gecti(
                self.sembol, "AL" if alis_mi else "SAT", giris, yeni_stop, korunan)
        return True

    # ------------------------------------------------------------- giris
    async def pozisyon_ac(self, yon: str, df: pd.DataFrame, bar_bas=None) -> dict:
        baglanti = await mt5_veri.baglanti_al()
        hesap = await baglanti.get_account_information()
        # BAKIYE degil OZSERMAYE - acik pozisyonlarin anlik zarari da sayilsin
        # ki kayip buyudukce pozisyonlar otomatik kuculsun.
        bakiye = hesap["equity"]
        fiyat = await baglanti.get_symbol_price(self.sembol)

        alis_mi = yon == "AL"
        giris = fiyat["ask"] if alis_mi else fiyat["bid"]
        atr = teknik.atr_serisi(df, 14).iloc[-1]
        if atr != atr or atr <= 0:
            return {"durum": "atr_hesaplanamadi"}

        isaret = 1 if alis_mi else -1
        sinir = await mt5_veri.sembol_sinirlari(self.sembol)
        stop_mesafesi = self.stop_atr_carpani * float(atr)
        # Broker asgari mesafesi stoptan buyukse stopu genislet - ihlal
        # edilirse emrin TAMAMI reddedilir, yani sinyal kacar.
        if sinir["asgari_stop"] > stop_mesafesi:
            print(f"  Stop mesafesi {stop_mesafesi:.5f}, brokerin asgarisi "
                  f"{sinir['asgari_stop']:.5f} - genisletildi.")
            stop_mesafesi = sinir["asgari_stop"]
        stop = round(giris - isaret * stop_mesafesi, sinir["basamak"])

        kur = await mt5_veri.kar_kuru_carpani(self.sembol)
        lot = risk.lot_hesapla(stop_mesafesi, self.kontrat_buyuklugu, bakiye,
                               risk_yuzdesi=self.risk_yuzdesi, kur_carpani=kur,
                               fiyat=giris,
                               azami_lot_broker=await mt5_veri.azami_lot(self.sembol))

        # HEDEF YOK: cikis sadece iz suren stopla olur. 136 puanlik bir
        # hareketten 24 puan alip cikmamak icin - olculdu, hedef koymak
        # sistemin butun kazancini siliyor.
        emir_fn = baglanti.create_market_buy_order if alis_mi else baglanti.create_market_sell_order
        sonuc = await emir_fn(self.sembol, lot, stop, None)

        try:
            acilan = None
            for _ in range(3):
                acilan = await self._pozisyon_getir()
                if acilan is not None:
                    break
                await asyncio.sleep(1)
            if acilan is not None:
                kayma_kaydi.kaydet(self.sembol, yon, giris, acilan["openPrice"],
                                   lot, stop_mesafesi)
            else:
                print("  (Kayma olculemedi: pozisyon terminal durumunda gorunmedi)")
        except Exception as exc:  # noqa: BLE001 - olcum hatasi islemi bozmamali
            print(f"  (Kayma olculemedi: {exc})")

        if bar_bas is not None:
            bar_kilidi.girisi_kaydet(self.sembol, bar_bas)
        # hedef=None -> mesajda "Hedef: yok, iz suren stopla yonetilir" yazar.
        telegram_bildirim.pozisyon_acildi(self.sembol, yon, lot, giris, stop, None, bakiye)
        return {"durum": "islem_acildi", "yon": yon, "giris": giris, "lot": lot,
                "stop_loss": stop, "stop_mesafesi": stop_mesafesi, "sonuc": sonuc}

    # ------------------------------------------------------------ ana akis
    async def calistir(self) -> None:
        baglanti = await mt5_veri.baglanti_al()
        # Stop kapanislari 15 dakikalik turlar arasinda gerceklestigi icin
        # bot onlari canli goremez - brokerin gecmisinden geriye donuk
        # taranip Telegram'a bildirilir. SADECE OKUR, hicbir pozisyona
        # dokunmaz.
        await kapanis_bildirimi.kapanislari_bildir(baglanti, self.sembol)

        ham, df = await self._veri()
        if len(df) < self.periyot + 20:
            print(f"{self.sembol}: yeterli {self.bar_saati} saatlik bar yok "
                  f"({len(df)}) - atlaniyor.")
            return

        yon = yon_serisi_donchian(df, self.periyot)[-1]
        yuksek = df["high"].rolling(self.periyot).max().shift(1).iloc[-1]
        dusuk = df["low"].rolling(self.periyot).min().shift(1).iloc[-1]
        print(f"{self.sembol} {ham['close'].iloc[-1]:.5f} | son kapanmis "
              f"{self.bar_saati}s bar {df.index[-1].strftime('%d.%m %H:%M')} "
              f"@ {df['close'].iloc[-1]:.5f} | {self.periyot} bar araligi "
              f"{dusuk:.5f} - {yuksek:.5f} | Donchian sinyali: {yon or 'YOK'}")

        pozisyon = await self._pozisyon_getir()
        if pozisyon is not None:
            mevcut = "AL" if pozisyon["type"] == "POSITION_TYPE_BUY" else "SAT"
            kar = pozisyon["profit"]
            giris = pozisyon["openPrice"]
            stop = pozisyon.get("stopLoss")
            print(f"  Acik pozisyon: {mevcut} @ {giris:.5f} | kar/zarar: {kar:+.2f} USD"
                  + (f" | stop {stop:.5f}" if stop else ""))
            # POZISYON ACIKKEN YENI SINYAL DIKKATE ALINMAZ - backtest de
            # boyle olculdu. Tek is: izi guncelle.
            await self._izi_guncelle(pozisyon, df)
            return

        if yon is None:
            print("  Pozisyon yok, kirilim da yok - beklemede.")
            return

        # BAR BASINA TEK GIRIS: bot 15 dakikada bir calisiyor, yani ayni
        # 4 saatlik barin icinde 16 kez giris firsati buluyor. Stop yedikten
        # sonra sinyal hala ayni yonde oldugu icin tekrar girerdi.
        bar_bas = df.index[-1] + pd.Timedelta(hours=self.bar_saati)
        if await bar_kilidi.bu_barda_giris_var_mi(baglanti, self.sembol, bar_bas):
            print(f"  Kirilim var ({yon}) ama {bar_bas.strftime('%d.%m %H:%M')} "
                  f"barinda zaten giris yapilmis - yeni bar acilana kadar beklenir.")
            return

        # BAYAT SINYAL KORUMASI - backteste SADIK KALMAK icin.
        #
        # Backtest girisi sinyal barinin KAPANISINDAN yapar. Canli bot 15
        # dakikada bir calistigi icin normalde bu farki 15 dakikaya indirir.
        # Ama GitHub Actions calistirma atlayabiliyor (olculdu: 35 dakikada
        # 3 tetikleme kacti) ve bot yeniden baslatildiginda barin ortasinda
        # olabiliyor. O durumda fiyat coktan uzaklasmis olur; ayni sinyalden
        # ama tamamen baska bir fiyattan girmek olculen sistem DEGILDIR.
        #
        # Ornek (05.08.2026 kurulum ani): XAUUSD sinyali 00:00 barinin
        # 4128.24 kapanisindan geldi, bot ilk kez 06:00'da calisti ve fiyat
        # 4178.83'tu - 50 puan, yani 1.0R uzakta. O giris backtestin olctugu
        # islem olmazdi.
        #
        # Bu esik backtesti DEGISTIRMEZ: orada giris fiyati = sinyal kapanisi
        # oldugu icin sapma her zaman 0'dir ve kural hic tetiklenmez.
        atr = teknik.atr_serisi(df, 14).iloc[-1]
        if atr == atr and atr > 0:
            sinyal_fiyati = float(df["close"].iloc[-1])
            simdi_fiyat = float(ham["close"].iloc[-1])
            sapma = (simdi_fiyat - sinyal_fiyati) * (1 if yon == "AL" else -1)
            sapma_r = sapma / (self.stop_atr_carpani * float(atr))
            if sapma_r > self.azami_bayatlik_r:
                print(f"  Kirilim var ({yon}) ama fiyat sinyal kapanisindan "
                      f"({sinyal_fiyati:.5f}) {sapma:+.5f} = {sapma_r:+.2f}R uzaklasmis "
                      f"(tavan {self.azami_bayatlik_r}R) - bu artik backtestin olctugu "
                      f"giris degil, atlaniyor. Yeni kirilim beklenecek.")
                return

        sonuc = await self.pozisyon_ac(yon, df, bar_bas)
        if sonuc["durum"] == "islem_acildi":
            print(f"  ACILDI: {yon} {sonuc['lot']} lot @ {sonuc['giris']:.5f} | "
                  f"stop {sonuc['stop_loss']:.5f} | HEDEF YOK (iz suren stop)")
        else:
            print(f"  {sonuc['durum']}")
