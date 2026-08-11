"""AUDNZD ORTALAMAYA DONUS BOTU - sifirdan olculerek kuruldu.

Bu bot, emekliye ayrilan eski AUDNZD botunun (confluence trend takip,
15.2 yilda -%91.9) yerine gecmiyor - o zaten kaldirilmisti. Bu, AUDNZD icin
BASTAN kurulan ayri bir sistem.

--------------------------------------------------------------------------
KURAL
--------------------------------------------------------------------------
1 SAATLIK barlarda, UC KOSUL DA AYNI YONU gostermeli:
  1. fiyatin EMA50'den yuzdesel sapmasi, o sapmanin son 500 barlik
     standart sapmasinin 2 katini asmis olmali
  2. Stochastic %K(14)  < 20 (AL)  /  > 80 (SAT)
  3. RSI(14)            < 30 (AL)  /  > 70 (SAT)

  - stop  : 1.5 x ATR(14)
  - hedef : 1R (stop mesafesi kadar) - yani 1:1
  - HAFTA ACILISINDAN sonraki ilk 2 barda GIRIS YOK
  - CUMA 20:00 UTC'de acik pozisyon KAPATILIR (hafta sonu boslugu riski)

OLCULEN SONUC (17.3 yil, 59.941 bar, spread + gercekci bosluk dolumu):
  526 islem, isabet %58, +%108.4, azami dusus %6.9
  ileriye yuruyen (sabit parametre) +%85.0
  18 yilin 16'si pozitif

KATMANLARIN KATKISI:
  MA sapmasi tek basina, korumasiz          +%93.1  dusus %9.4
  + Stochastic + RSI teyidi                 +%92.6  dusus %8.1
  + cuma 20:00 kapatma                      +%80.1  dusus %7.6
  + hafta acilisi ilk 2 bar yasak          +%108.4  dusus %6.9
Cuma korumasi getiriden 12.5 puan goturuyor ama pazartesi filtresi bunu
fazlasiyla geri odiyor: sonucta hem hafta sonu riski YOK, hem getiri
korumasiz halden YUKSEK, hem dusus daha dusuk.

--------------------------------------------------------------------------
NASIL SECILDI - once "bilgi var mi", sonra "kar eder mi"
--------------------------------------------------------------------------
FAZ 0: yedi indikatorun her biri, HICBIR cikis kurali olmadan, sadece
"sinyalden sonra fiyat sinyalin dedigi yone gidiyor mu" diye olculdu.
Getiri ATR cinsinden, 59.941 bar (17.3 yil). t-istatistigi >= 3 arandi:

  BILGI TASIYANLAR              4 bar    12 bar   24 bar   48 bar   96 bar
    MA sapmasi (EMA50)        +0.087   +0.255   +0.365   +0.623   +0.814
                              (t=4.8)  (t=8.3)  (t=8.1)  (t=9.3)  (t=9.6)
    RSI 20/80                 +0.140   +0.318   +0.596   +0.801        -
    RSI 30/70                 +0.073   +0.139   +0.170   +0.284        -
    Bollinger 20/2            +0.073   +0.126        -        -        -
    Stochastic 20/80          +0.086   +0.128        -        -        -

  BILGI TASIMAYANLAR
    MACD              hicbir ufukta anlamli degil (en yuksek |t| = 1.6)
    RVI               hicbir ufukta anlamli degil (en yuksek |t| = 1.9)
    ADX (+DI/-DI)     SISTEMATIK OLARAK YANLIS (t = -3.7 ... -4.7)

ADX rejim filtresi olarak da denendi (ortalamaya donusu hangi ADX bandinda
uygulamali): en iyi band 25-30'da t=2.6 - esigin altinda, kullanilmadi.

Kontrol olarak Donchian kirilimi da olculdu: AUDNZD'de t=-5.5, yani
anlamli derecede NEGATIF. Kirilimlar bu paritede sistematik olarak
basarisiz - varyans oraninin (0.885-0.934) soyledigini bagimsiz olarak
dogruluyor.

--------------------------------------------------------------------------
NEDEN 1 SAATLIK (4 saatlik ELENDI)
--------------------------------------------------------------------------
                             1 saatlik   4 saatlik
  en iyi kurulum               +%93.1      +%18.4
  1. yari / 2. yari         +32.0/+46.2  +27.1/-6.8   <- celiskili
  ileriye yuruyen              +%75.6      +%12.8
4 saatlikte Bollinger ve Stochastic 48 barda TERS isaret veriyor
(t=-3.2 ve -5.1). AUDNZD'nin ortalamaya donus yapisi saatlik olcekte.

--------------------------------------------------------------------------
NEDEN 1R HEDEF, IZ SUREN STOP DEGIL
--------------------------------------------------------------------------
Metal botunun (Donchian) tam TERSI cikti - ve mantikli. Trend takibinde
hareket sinirsizdir, iz suren stop kazanir. Ortalamaya donuste hareket
SINIRLIDIR: fiyat ortalamaya doner ve durur.

  stop 1.5R + hedef 1R          +%93.1   dusus %9.4    <- SECILEN
  stop 2.5R + ortalamaya donunce +%45.8   dusus %13.7
  stop 1.5R + hedef 2R           +%27.0   dusus %22.2
  stop 1.5R + hedef 3R           -%29.0   dusus %46.5
  stop 1.5R + iz suren 1.5xATR   -%22.5   dusus %32.7

--------------------------------------------------------------------------
DAYANIKLILIK
--------------------------------------------------------------------------
PLATO: 180 parametre kombinasyonunun 162'si (%90) pozitif. Medyan +%24.2.
  DIKKAT: secilen hucre 96. yuzdelik dilimde, yani bir TEPE. Gercekci
  beklenti +%93 degil, medyan ile tepe arasi - kabaca +%40-60.
  Saglam olan taraf: "sapma 2.0" sutununun BESI de yuksek (+%36...+%93),
  yani 2 standart sapma secimi EMA periyodundan bagimsiz calisiyor.
  EMA periyodu gurultu (20/30/50/120 benzer sonuc veriyor).

YIL YIL: 18 yilin 16'si pozitif. Negatifler 2013 (-%6.7) ve 2021 (-%0.7).
  En iyi yil toplamin sadece %14'u - kazanc tek bir yildan gelmiyor.

ILERIYE YURUYEN (12 ceyrek isinma): SABIT parametreyle +%75.6, dusus %9.4.
  Adaptif secim (her ceyrek gecmisin en iyisi) +%25.7 - yani parametre
  SABIT kalmali, uyarlanmamali.

MALIYET: spread'in 5 katinda hala pozitif (+%27), 8 katinda kiriliyor.

HAFTA SONU: olculen hasar KUCUK - 17.3 yilda 6 islem (%1.1) boslukta
  doldu, ortalama -1.38R (planlanan -1.00R yerine). Buna ragmen cuma
  kapatmasi EKLENDI: bu bir getiri optimizasyonu degil, OLCULMEMIS bir
  kuyruk riskine karsi kasitli tercih (RBA/RBNZ surprizi ya da sistemik
  sok hafta sonu cok daha sert bir bosluk acabilir).
  Piyasa saatleri (17 yillik veriden): kapanis cuma 20:00-21:00 UTC
  (%46 20:00, %22 21:00), acilis pazar 21:00-22:00 UTC.
  Cuma 20:00 kapatma, hafta sonu maruziyetini 46 islemden 16'ya indiriyor.

--------------------------------------------------------------------------
BILINEN ZAYIFLIKLAR
--------------------------------------------------------------------------
1. GECIKMEYE HASSAS. Bar kapanisindan 1 saat gec girilirse ucluda sistem
   +%83.7'den -%3.8'e duser (MA tek basinayken -%12.1 idi, uclu daha
   dayanikli). Bayat sinyal korumasi (0.2R) bunu +%20.3'e toparlar. Bot 15
   dakikada bir calisiyor, yani normalde gecikme <= 15 dk; ama GitHub
   Actions calistirma ATLAYABILIYOR (olculdu: 35 dakikada 3 tetikleme
   kacti). Koruma o yuzden sart.
2. STANDART SAPMA PENCERESI (500) hala bir TEPE: 250 -> +%44.4,
   500 -> +%92.6, 1000 -> +%45.3, 2000 -> +%39.8. Uclu kombinasyon EMA
   periyodu hassasiyetini cozdu ama bunu cozmedi. Tek bilinen kirilganlik.
3. Ayda ~3 islem. Sonuclarin anlamli olmasi aylar surer.
4. Bu turda cok sayida varyant denendi. Uclunun secilme gerekcesi getiri
   DEGIL (getiri neredeyse ayni), parametre dayanikliligi: EMA/sapma
   izgarasinda MA tek basina medyan +%38.5 / en kotu +%4.5 verirken uclu
   medyan +%82.4 / en kotu +%22.7 veriyor ve secilen hucre TEPE degil ORTA.

SADECE demo hesap icindir - gercek/canli hesaba asla baglanmamali."""
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

# EMA50 + 500 barlik standart sapma penceresi + ATR14 icin isinma payi.
HAM_BAR_ADEDI = 1500


def _tamamlanmis_barlar(df: pd.DataFrame) -> pd.DataFrame:
    """MetaApi son bar olarak ICINDE BULUNULAN mumu doner - onun 'close'
    degeri o anki fiyattir, bar kapanisi degil. Sinyal her zaman son
    KAPANMIS bardan hesaplanmali (backtest de oyle olculdu)."""
    if len(df) < 2:
        return df
    periyot = df.index[-1] - df.index[-2]
    if df.index[-1] + periyot > dt.datetime.now(dt.timezone.utc):
        return df.iloc[:-1]
    return df


def sapma_sinyali(df: pd.DataFrame, ema_periyot: int = 50, carpan: float = 2.0,
                  pencere: int = 500):
    """Son KAPANMIS bar icin sinyal, esik ve sapma degerini doner.

    Esik, sapmanin kendi son 500 barlik standart sapmasidir - yani
    "normal" sapma buyuklugu piyasanin o donemki halinden ogrenilir,
    sabit bir yuzde degildir. Volatilite artinca esik de genisler.
    """
    ma = df["close"].ewm(span=ema_periyot, adjust=False).mean()
    sapma = (df["close"] - ma) / ma
    esik = sapma.rolling(pencere).std() * carpan
    s, e = float(sapma.iloc[-1]), float(esik.iloc[-1])
    if e != e or e <= 0:
        return None, s, e, float(ma.iloc[-1])
    if s < -e:
        return "AL", s, e, float(ma.iloc[-1])
    if s > e:
        return "SAT", s, e, float(ma.iloc[-1])
    return None, s, e, float(ma.iloc[-1])


def acilistan_bar_sayisi(df: pd.DataFrame, bosluk_saat: int = 24) -> int:
    """Son hafta sonu boslugundan bu yana kac bar gecti? (0 = acilis bari)

    Bosluk, ardisik iki bar arasinda `bosluk_saat` saatten fazla fark
    olmasiyla tespit edilir - tatiller de dahil, sadece hafta sonu degil.
    Hic bosluk bulunmazsa buyuk bir sayi doner (yani filtre uygulanmaz).
    """
    if len(df) < 2:
        return 999
    farklar = df.index.to_series().diff().dt.total_seconds() / 3600
    for i in range(len(df) - 1, 0, -1):
        if farklar.iloc[i] >= bosluk_saat:
            return len(df) - 1 - i
    return 999


def stokastik_k(df: pd.DataFrame, periyot: int = 14) -> float:
    """Stochastic %K - fiyatin son N barin araligindaki konumu (0-100)."""
    en_dusuk = df["low"].rolling(periyot).min().iloc[-1]
    en_yuksek = df["high"].rolling(periyot).max().iloc[-1]
    aralik = en_yuksek - en_dusuk
    if aralik <= 0 or aralik != aralik:
        return float("nan")
    return float(100 * (df["close"].iloc[-1] - en_dusuk) / aralik)


def teyitli_sinyal(df: pd.DataFrame, ema_periyot: int = 50, carpan: float = 2.0,
                   pencere: int = 500):
    """UC KOSULUN DA AYNI YONU gostermesi gerekir:
        1. fiyat EMA'dan +-carpan x std kadar sapmis
        2. Stochastic %K  < 20 (AL) ya da > 80 (SAT)
        3. RSI(14)        < 30 (AL) ya da > 70 (SAT)

    NEDEN UCU BIRDEN - ve neden bu 'daha cok onay' DEGIL:
    Sinyaller bagimsiz teyit vermiyor; olculdu, MA sinyal verdiginde RSI
    %77 ayni yonu gosteriyor ve %0 ters. Ucu de ayni bilgiye bakiyor.
    Faydasi baska yerden geliyor: ek kosullar, esigin tam nerede
    cizildigine en duyarli olan SINIRDAKI sinyalleri eliyor. Sonuc,
    parametre secimine cok daha az bagimli bir sistem:

      EMA/sapma izgarasi (15 hucre)   MA tek      MA+Stoch+RSI
        medyan                        +%38.5        +%82.4
        en kotu hucre                  +%4.5        +%22.7
        secilen hucre (EMA50/2.0)     +%93.1 (TEPE) +%92.6 (ORTA)

    MA tek basina icin secilen hucre izgaranin MAKSIMUMUYDU - yani tepe.
    Ucluda ayni hucre dagilimin ortasinda. Getiri neredeyse ayni
    (+%93.1 vs +%92.6) ama ucluyu secmemizin sebebi getiri degil, bu.

    Diger olculen farklar (17.3 yil, spread + gercekci bosluk dolumu):
      azami dusus            %9.4  -> %8.1
      en kotu yil           -%6.7  -> -%4.7
      yillik std              3.9  ->   3.2
      spread 8 kat             -%7 ->    +%7
      1 saat gecikme (korumasiz) -%12.1 -> -%3.8
    """
    yon, sapma, esik, ma = sapma_sinyali(df, ema_periyot, carpan, pencere)
    # Stochastic ve RSI, sinyal olmasa bile hesaplanir - loga yazilinca
    # "neden girilmedi" sorusu tek bakista cevaplanabilsin diye.
    k = stokastik_k(df, 14)
    r = float(teknik.rsi_serisi(df["close"], 14).iloc[-1])
    if yon is None or k != k or r != r:
        return None, sapma, esik, ma, k, r

    if yon == "AL" and k < 20 and r < 30:
        return "AL", sapma, esik, ma, k, r
    if yon == "SAT" and k > 80 and r > 70:
        return "SAT", sapma, esik, ma, k, r
    return None, sapma, esik, ma, k, r


class OrtalamaDonusBot:
    def __init__(self, sembol: str = "AUDNZD", kontrat_buyuklugu: float = 100000,
                 ema_periyot: int = 50, sapma_carpani: float = 2.0,
                 sapma_penceresi: int = 500, stop_atr_carpani: float = 1.5,
                 hedef_r: float = 1.0, risk_yuzdesi: float = 0.005,
                 azami_bayatlik_r: float = 0.2, cuma_kapat_saat: int | None = 20,
                 acilis_yasak_bar: int = 2):
        self.sembol = sembol
        self.kontrat_buyuklugu = kontrat_buyuklugu
        self.ema_periyot = ema_periyot
        self.sapma_carpani = sapma_carpani
        self.sapma_penceresi = sapma_penceresi
        self.stop_atr_carpani = stop_atr_carpani
        # 1R hedef - ortalamaya donuste hareket SINIRLI oldugu icin.
        # 2R -> +%27, 3R -> -%29 (bkz. modul basligi).
        self.hedef_r = hedef_r
        self.risk_yuzdesi = risk_yuzdesi
        # Bar kapanisindan sonra fiyat bu kadar R uzaklastiysa girilmez.
        # 0.2 OLCULDU: 1 saat gecikmede koruma yok -%12.1, 0.2R ile +%40.2,
        # 0.3R ile +%27.2, 0.5R ile +%24.9. Gecikme yokken HIC tetiklenmiyor
        # (635 islemin 635'i geciyor), yani bedava sigorta.
        self.azami_bayatlik_r = azami_bayatlik_r
        # HAFTA SONU KORUMASI: cuma bu saatte (UTC) acik pozisyon KAPATILIR.
        #
        # Olculdu (uclu kurulum, 17.3 yil):
        #   kurulum                       hesap%  dusus%  hafta sonu maruziyeti
        #   tasinir (korumasiz)            +92.6     8.1        46 islem
        #   cuma 21:00 kapat               +88.7     8.1        40 islem
        #   cuma 20:00 kapat               +80.1     7.6        16 islem   <- SECILEN
        #   cuma 20:00 + 12:00 girme yok   +76.7     7.6        10 islem
        #
        # 20:00 en verimli nokta: maruziyeti %65 azaltiyor, bedeli 12.5 puan.
        # 21:00 anlamsiz (piyasa zaten kapaniyor). Giris yasagi eklemek
        # maruziyeti 16'dan 10'a indirirken 3.4 puan daha goturuyor.
        #
        # NOT: bu bir GETIRI optimizasyonu DEGIL, kasitli bir risk tercihi.
        # Tarihte AUDNZD hafta sonu boslugu 6 islemde ortalama -1.38R yapmis
        # (planlanan -1.00R yerine) - yani olculen hasar kucuk. Koruma,
        # OLCULMEMIS bir kuyruk riski icin: RBA/RBNZ surprizi ya da sistemik
        # bir sok hafta sonu cok daha sert bir bosluk acabilir. Getiriden
        # feragat ederek bu belirsizlik satin aliniyor.
        # None yapilirsa koruma kapanir ve pozisyon hafta sonunu tasir.
        self.cuma_kapat_saat = cuma_kapat_saat
        # HAFTA ACILISI FILTRESI: bosluktan sonraki ilk N barda GIRIS YOK.
        #
        # Olculdu - acilistan sonraki N. barda girilen islemlerin performansi:
        #   acilis bari (0)      112 islem  isabet %54  +0.0533R
        #   1-2. bar              16 islem  isabet %25  -0.4889R   <- felaket
        #   3-5. bar              20 islem  isabet %70  +0.3004R
        #   12-23. bar            44 islem  isabet %59  +0.1450R
        #   24+ bar (hafta ici)  327 islem  isabet %58  +0.1564R
        #
        # Filtre sonuclari (cuma 20:00 kapatma acikken):
        #   yasak yok      +%80.1  dusus %7.6  ileriye +%59.8
        #   ilk 1 bar      +%94.2  dusus %7.1  ileriye +%69.8
        #   ilk 2 bar     +%108.4  dusus %6.9  ileriye +%85.0   <- SECILEN
        #   ilk 3 bar     +%101.5  dusus %6.9  ileriye +%73.3
        #   ilk 4 bar      +%98.1  dusus %6.8  ileriye +%70.5
        #   ilk 6 bar      +%84.4  dusus %7.1  ileriye +%55.1
        # 1-4 bar araliginin hepsi temeli belirgin geciyor: tepe degil PLATO.
        #
        # Sinyal genelde birkac bar surdugu icin bu filtre islemi IPTAL
        # etmiyor, GECIKTIRIYOR - islem sayisi 550'den 526'ya iniyor ama
        # giris fiyati daha iyi oluyor.
        self.acilis_yasak_bar = acilis_yasak_bar

    async def _pozisyon_getir(self) -> dict | None:
        baglanti = await mt5_veri.baglanti_al()
        pozisyonlar = await baglanti.get_positions()
        return next((p for p in pozisyonlar if p["symbol"] == self.sembol), None)

    async def pozisyon_ac(self, yon: str, df: pd.DataFrame, bar_bas) -> dict:
        baglanti = await mt5_veri.baglanti_al()
        hesap = await baglanti.get_account_information()
        # BAKIYE degil OZSERMAYE - acik pozisyonlarin anlik zarari da sayilsin.
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
        if sinir["asgari_stop"] > stop_mesafesi:
            print(f"  Stop mesafesi {stop_mesafesi:.5f}, brokerin asgarisi "
                  f"{sinir['asgari_stop']:.5f} - genisletildi.")
            stop_mesafesi = sinir["asgari_stop"]
        stop = round(giris - isaret * stop_mesafesi, sinir["basamak"])
        hedef = round(giris + isaret * self.hedef_r * stop_mesafesi, sinir["basamak"])

        # AUDNZD'nin kar para birimi NZD - hesap USD. Carpan olmadan gercek
        # risk hedeflenenin ~%59'u kalirdi (bkz. mt5_veri.kar_kuru_carpani).
        kur = await mt5_veri.kar_kuru_carpani(self.sembol)
        lot = risk.lot_hesapla(stop_mesafesi, self.kontrat_buyuklugu, bakiye,
                               risk_yuzdesi=self.risk_yuzdesi, kur_carpani=kur,
                               fiyat=giris,
                               azami_lot_broker=await mt5_veri.azami_lot(self.sembol))

        emir_fn = (baglanti.create_market_buy_order if alis_mi
                   else baglanti.create_market_sell_order)
        sonuc = await emir_fn(self.sembol, lot, stop, hedef)

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

        bar_kilidi.girisi_kaydet(self.sembol, bar_bas)
        telegram_bildirim.pozisyon_acildi(self.sembol, yon, lot, giris, stop, hedef, bakiye)
        return {"durum": "islem_acildi", "yon": yon, "giris": giris, "lot": lot,
                "stop_loss": stop, "take_profit": hedef, "stop_mesafesi": stop_mesafesi,
                "sonuc": sonuc}

    async def calistir(self) -> None:
        baglanti = await mt5_veri.baglanti_al()
        # Stop/hedef kapanislarini bot canli goremez (15 dakikada bir calisiyor),
        # brokerin gecmisinden geriye donuk taranip Telegram'a bildirilir.
        # SADECE OKUR, hicbir pozisyona dokunmaz.
        await kapanis_bildirimi.kapanislari_bildir(baglanti, self.sembol)

        ham = await mt5_veri.cok_barli_getir(self.sembol, "1h", HAM_BAR_ADEDI)
        df = _tamamlanmis_barlar(ham)
        gerekli = self.sapma_penceresi + self.ema_periyot
        if len(df) < gerekli:
            print(f"{self.sembol}: yeterli bar yok ({len(df)} < {gerekli}) - atlaniyor.")
            return

        yon, sapma, esik, ma, k, rsi = teyitli_sinyal(
            df, self.ema_periyot, self.sapma_carpani, self.sapma_penceresi)
        ham_yon = sapma_sinyali(df, self.ema_periyot, self.sapma_carpani,
                                self.sapma_penceresi)[0]
        print(f"{self.sembol} {ham['close'].iloc[-1]:.5f} | son kapanmis bar "
              f"{df.index[-1].strftime('%d.%m %H:%M')} @ {df['close'].iloc[-1]:.5f} | "
              f"EMA{self.ema_periyot} {ma:.5f}")
        k_yazi = f"{k:.1f}" if k == k else "?"
        rsi_yazi = f"{rsi:.1f}" if rsi == rsi else "?"
        print(f"  1) sapma {sapma*100:+.3f}% (esik +-{esik*100:.3f}%) -> {ham_yon or 'YOK'}")
        print(f"  2) Stochastic %K {k_yazi} (AL<20 / SAT>80)")
        print(f"  3) RSI {rsi_yazi} (AL<30 / SAT>70)")
        if yon:
            print(f"  UC KOSUL DA {yon} diyor.")
        elif ham_yon:
            print(f"  MA sapmasi {ham_yon} diyor ama Stochastic/RSI teyit etmedi - giris yok.")
        else:
            print("  Sinyal yok.")

        pozisyon = await self._pozisyon_getir()
        if pozisyon is not None:
            mevcut = "AL" if pozisyon["type"] == "POSITION_TYPE_BUY" else "SAT"
            print(f"  Acik pozisyon: {mevcut} @ {pozisyon['openPrice']:.5f} | "
                  f"kar/zarar: {pozisyon['profit']:+.2f} USD | "
                  f"stop {pozisyon.get('stopLoss')} | hedef {pozisyon.get('takeProfit')}")
            # HAFTA SONU KORUMASI - cuma aksami pozisyonu kapat.
            simdi = dt.datetime.now(dt.timezone.utc)
            if (self.cuma_kapat_saat is not None and simdi.weekday() == 4
                    and simdi.hour >= self.cuma_kapat_saat):
                kz = pozisyon["profit"]
                print(f"  CUMA {simdi.hour:02d}:xx UTC - hafta sonu boslugu riskine karsi "
                      f"pozisyon kapatiliyor ({kz:+.2f} USD)...")
                try:
                    sonuc = await baglanti.close_position(pozisyon["id"])
                    print(f"  Kapandi: {sonuc.get('stringCode')}")
                    telegram_bildirim.pozisyon_kapandi(
                        self.sembol, mevcut, kz,
                        "cuma kapanisi - hafta sonu boslugu riski")
                except Exception as exc:  # noqa: BLE001 - kapatma basarisiz olsa da bot durmamali
                    print(f"  KAPATMA BASARISIZ ({exc}) - pozisyon stop/hedefiyle devam "
                          f"ediyor, sonraki turda tekrar denenecek.")
                return

            # Diger her durumda pozisyona dokunulmaz - stop ve hedef brokerde
            # duruyor, backtest de tam boyle olculdu. Basabas yok, iz suren
            # stop yok (ikisi de olculdu ve ZARAR verdi).
            print("  MT5'in kendi stop/hedefiyle acik kaliyor.")
            return

        if yon is None:
            print("  Pozisyon yok, sinyal de yok - beklemede.")
            return

        # CUMA FILTRESI YOK - uclu kurulumda OLCULDU ve ZARAR veriyor:
        #   filtresiz              +%92.6   dusus %8.1
        #   cuma 12:00 sonrasi yok +%83.7   dusus %8.6
        #   cuma 20:00'de kapat    +%80.1   dusus %7.6
        # MA tek basinayken filtre kucuk fayda veriyordu (+%94.2 vs +%93.1),
        # ucluda hem getiriyi hem dususu kotulestiriyor. Zaten sinirda bir
        # kazancti. Hafta sonu pozisyon TASINIR: tasiyan 46 islemin ortalamasi
        # +0.2998R (genel ortalama +0.1258R), boslukta dolan sadece 6 islem
        # (%1.1, ortalama -1.38R).

        # HAFTA ACILISI FILTRESI (bkz. __init__ icindeki olcum tablosu).
        acilis_bar = acilistan_bar_sayisi(df)
        if acilis_bar < self.acilis_yasak_bar:
            print(f"  Sinyal var ({yon}) ama hafta acilisindan sadece {acilis_bar} bar "
                  f"gecmis (ilk {self.acilis_yasak_bar} bar yasak) - acilis "
                  f"dalgalanmasi geciyor, sonraki barda tekrar bakilacak.")
            return

        # BAR BASINA TEK GIRIS: bot 15 dakikada bir calisiyor, ayni saatlik
        # barda 4 kez giris firsati buluyor. Bkz. bar_kilidi.
        bar_bas = df.index[-1] + pd.Timedelta(hours=1)
        if await bar_kilidi.bu_barda_giris_var_mi(baglanti, self.sembol, bar_bas):
            print(f"  Sinyal var ({yon}) ama {bar_bas.strftime('%H:%M')} barinda zaten "
                  f"giris yapilmis - yeni bar acilana kadar beklenir.")
            return

        # BAYAT SINYAL KORUMASI - bu sistemde KRITIK.
        # Ortalamaya donus, sicramayi yakalamak demek; bir saat gec kalinirsa
        # sicrama olmus biter. Olculdu: 1 saat gecikmede koruma yok -%12.1,
        # 0.2R korumasiyla +%40.2. Gecikme yokken hic tetiklenmez.
        atr = teknik.atr_serisi(df, 14).iloc[-1]
        if atr == atr and atr > 0:
            sinyal_fiyati = float(df["close"].iloc[-1])
            simdi_fiyat = float(ham["close"].iloc[-1])
            sapma_r = ((simdi_fiyat - sinyal_fiyati) * (1 if yon == "AL" else -1)
                       / (self.stop_atr_carpani * float(atr)))
            if sapma_r > self.azami_bayatlik_r:
                print(f"  Sinyal var ({yon}) ama fiyat sinyal kapanisindan "
                      f"({sinyal_fiyati:.5f}) {simdi_fiyat-sinyal_fiyati:+.5f} = "
                      f"{sapma_r:+.2f}R uzaklasmis (tavan {self.azami_bayatlik_r}R) - "
                      f"donus hareketi baslamis, artik backtestin olctugu giris degil. "
                      f"Atlaniyor.")
                return

        sonuc = await self.pozisyon_ac(yon, df, bar_bas)
        if sonuc["durum"] == "islem_acildi":
            print(f"  ACILDI: {yon} {sonuc['lot']} lot @ {sonuc['giris']:.5f} | "
                  f"stop {sonuc['stop_loss']:.5f} | hedef {sonuc['take_profit']:.5f} (1R)")
        else:
            print(f"  {sonuc['durum']}")
