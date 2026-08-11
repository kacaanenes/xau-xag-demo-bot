"""AUDNZD ORTALAMAYA DONUS BOTU - sifirdan olculerek kuruldu.

Bu bot, emekliye ayrilan eski AUDNZD botunun (confluence trend takip,
15.2 yilda -%91.9) yerine gecmiyor - o zaten kaldirilmisti. Bu, AUDNZD icin
BASTAN kurulan ayri bir sistem.

--------------------------------------------------------------------------
KURAL
--------------------------------------------------------------------------
1 SAATLIK barlarda:
  - fiyatin EMA50'den yuzdesel sapmasi hesaplanir
  - bu sapmanin son 500 barlik standart sapmasi esik olarak alinir
  - sapma  -2 esigin ALTINDA  -> AL   (asiri dusuk, ortalamaya doner)
  - sapma  +2 esigin USTUNDE  -> SAT  (asiri yuksek, ortalamaya doner)
  - stop  : 1.5 x ATR(14)
  - hedef : 1R (stop mesafesi kadar) - yani 1:1
  - CUMA 12:00 UTC'den sonra YENI pozisyon acilmaz
  - hafta sonu pozisyon TASINIR (olculdu, kapatmak zarar veriyor)

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

HAFTA SONU: 17.3 yilda sadece 6 islem (%0.9) boslukta doldu, fazladan
  maliyet -2.5R = toplamin %3.6'si. Hafta sonunu TASIYAN islemler daha IYI
  (58 islem, isabet %66, ortalama +0.2658R) cunku cuma gunu fiyatin
  ortalamadan en cok uzaklastigi anlar onlar. Cuma aksami zorla kapatmak
  +%93'u +%74-86'ya dusuruyor - YAPILMIYOR.
  Cuma 12:00 sonrasi GIRMEMEK ise dususu %9.4 -> %8.0 yapiyor - EKLENDI.

--------------------------------------------------------------------------
BILINEN ZAYIFLIKLAR
--------------------------------------------------------------------------
1. GECIKMEYE COK HASSAS. Bar kapanisindan 1 saat gec girilirse sistem
   +%94.2'den -%12.1'e duser. Bayat sinyal korumasi (0.2R) bunu +%40.2'ye
   toparlar. Bot 15 dakikada bir calisiyor, yani normalde gecikme <= 15 dk;
   ama GitHub Actions calistirma ATLAYABILIYOR (olculdu: 35 dakikada 3
   tetikleme kacti). Koruma o yuzden sart.
2. Secilen parametre hucresi bir tepe (yukariya bak).
3. Ayda ~3 islem. Sonuclarin anlamli olmasi aylar surer.

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


class OrtalamaDonusBot:
    def __init__(self, sembol: str = "AUDNZD", kontrat_buyuklugu: float = 100000,
                 ema_periyot: int = 50, sapma_carpani: float = 2.0,
                 sapma_penceresi: int = 500, stop_atr_carpani: float = 1.5,
                 hedef_r: float = 1.0, risk_yuzdesi: float = 0.005,
                 azami_bayatlik_r: float = 0.2, cuma_giris_son_saat: int = 12):
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
        # Cuma bu saatten (UTC) sonra yeni pozisyon yok. Dususu %9.4 -> %8.0.
        # Acik pozisyonlar hafta sonunu TASIR - kapatmak olculdu ve zarar
        # veriyor (+%93 -> +%74-86).
        self.cuma_giris_son_saat = cuma_giris_son_saat

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

        yon, sapma, esik, ma = sapma_sinyali(df, self.ema_periyot, self.sapma_carpani,
                                             self.sapma_penceresi)
        print(f"{self.sembol} {ham['close'].iloc[-1]:.5f} | son kapanmis bar "
              f"{df.index[-1].strftime('%d.%m %H:%M')} @ {df['close'].iloc[-1]:.5f} | "
              f"EMA{self.ema_periyot} {ma:.5f} | sapma {sapma*100:+.3f}% "
              f"(esik +-{esik*100:.3f}%) | sinyal: {yon or 'YOK'}")

        pozisyon = await self._pozisyon_getir()
        if pozisyon is not None:
            mevcut = "AL" if pozisyon["type"] == "POSITION_TYPE_BUY" else "SAT"
            print(f"  Acik pozisyon: {mevcut} @ {pozisyon['openPrice']:.5f} | "
                  f"kar/zarar: {pozisyon['profit']:+.2f} USD | "
                  f"stop {pozisyon.get('stopLoss')} | hedef {pozisyon.get('takeProfit')}")
            # Pozisyon acikken hicbir sey yapilmaz - stop ve hedef brokerde
            # duruyor, backtest de tam boyle olculdu. Basabas yok, iz suren
            # stop yok (ikisi de olculdu ve ZARAR verdi).
            print("  MT5'in kendi stop/hedefiyle acik kaliyor.")
            return

        if yon is None:
            print("  Pozisyon yok, sinyal de yok - beklemede.")
            return

        # CUMA FILTRESI: cuma 12:00 UTC'den sonra yeni pozisyon acilmaz.
        # Acik pozisyonlar hafta sonunu tasir - bu KASITLI (bkz. modul basligi).
        simdi = dt.datetime.now(dt.timezone.utc)
        if simdi.weekday() == 4 and simdi.hour >= self.cuma_giris_son_saat:
            print(f"  Sinyal var ({yon}) ama cuma {simdi.hour:02d}:xx UTC - "
                  f"{self.cuma_giris_son_saat}:00 sonrasi yeni pozisyon acilmiyor "
                  f"(hafta sonu boslugu riski). Pazartesi tekrar bakilacak.")
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
