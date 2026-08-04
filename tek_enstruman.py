"""Tek enstrumanli (cift bacakli olmayan) botlar icin ortak emir/orkestrasyon
mantigi. AUDNZD ve XAGUSD ayni kodu paylassin diye genellestirildi - onceki
halinde audnzd_emir.py sadece AUDNZD'ye gomuluydu, ikinci bir enstruman
eklemek kod kopyalamayi gerektiriyordu.

Strateji tipi enstrumanin OLCULEN karakterine gore secilir (varyans orani
< 1 ise ortalamaya donus, > 1 ise trend) - bkz. README.
SADECE demo hesap icindir."""
from __future__ import annotations

import datetime as dt

import backtest
import bar_kilidi
import gosterim
import kapanis_bildirimi
import mt5_veri
import risk
import telegram_bildirim


def _tamamlanmis_barlar(df):
    """MetaApi son bar olarak ICINDE BULUNULAN (tamamlanmamis) mumu doner -
    onun 'close' degeri o anki fiyattir, bar kapanisi degil. Sinyali bunun
    uzerinden hesaplamak, backtest'in olctugu davranistan sapar.

    OLCULDU: saat ici anlik fiyata gore girmek, saatlik kapanisa gore
    girmeye kiyasla belirgin daha kotu:
      XAGUSD  +%39.92 -> +%25.34   (islem 31 -> 55, isabet %67.7 -> %52.7)
      XAUUSD  +%13.49 ->  +%8.79   (islem 35 -> 58, isabet %57.1 -> %46.6)
    Sebep: fiyat bandin disina saat icinde kisa sure cikip geri donuyor;
    bunlar saatlik kapanista sinyal SAYILMAZDI - yani sahte sinyaller.

    Bu fonksiyon tamamlanmamis son bari atarak sinyali her zaman son
    KAPANMIS bardan hesaplatir."""
    if len(df) < 2:
        return df
    son = df.index[-1]
    simdi = dt.datetime.now(dt.timezone.utc)
    # Son barin kapsadigi periyot henuz bitmemisse (bar baslangici, simdiki
    # zamandan bir periyot geride degilse) o bar tamamlanmamistir.
    if len(df) >= 2:
        periyot = df.index[-1] - df.index[-2]
        if son + periyot > simdi:
            return df.iloc[:-1]
    return df


class TekEnstrumanBot:
    def __init__(self, sembol: str, kontrat_buyuklugu: float, strateji: str,
                 esik: int = 5, risk_odul_orani: float = 1.5, zaman_dilimi: str = "1h",
                 basabas_r: float | None = 1.0, izinli_saatler: tuple | None = None,
                 sinyal_tersine_cikis: bool = False):
        if strateji not in ("meanrev", "trend"):
            raise ValueError(f"bilinmeyen strateji: {strateji}")
        # Sinyal ters dondugunde pozisyonu kapatmak, backtest'te AYRI bir
        # varyant olarak olculur - canli kod ile backtest'in ayni sonucu
        # vermesi icin bu ayarin ikisinde de AYNI olmasi sart. Metaller
        # (meanrev) False ile olculdu: sinyal-tersine-cikis acikken sonuc
        # daha kotuydu, cunku ortalamaya donus sinyali pozisyon acikken
        # dogal olarak zayifliyor ve erken cikis yaratiyor.
        self.sinyal_tersine_cikis = sinyal_tersine_cikis
        self.sembol = sembol
        self.kontrat_buyuklugu = kontrat_buyuklugu
        self.strateji = strateji
        self.esik = esik
        self.risk_odul_orani = risk_odul_orani
        self.zaman_dilimi = zaman_dilimi
        # Hangi UTC saatlerinde YENI pozisyon acilabilecegi. Acik pozisyon
        # bu saatlerin disina cikilsa bile kendi stop/hedefine kadar
        # yonetilmeye devam eder - filtre sadece girisi kisitlar.
        self.izinli_saatler = izinli_saatler
        # Kar, baslangic riskinin bu katina ulasinca stop girise cekilir.
        # XAGUSD'de olculdu: +%32.27 -> +%37.61 (iki yarida da pozitif).
        # Iz suren stop ayrica denendi ve DAHA KOTU cikti (+%29.69), bu
        # yuzden sadece basabas korumasi var, surekli izleyen stop yok.
        self.basabas_r = basabas_r

    async def _basabasa_cek(self, pozisyon: dict) -> bool:
        """Kar 1R'ye ulastiysa stop'u girise ceker. Zaten girise (veya
        otesine) cekilmisse bir sey yapmaz."""
        if self.basabas_r is None:
            return False

        giris = pozisyon["openPrice"]
        stop = pozisyon.get("stopLoss")
        if stop is None:
            return False

        alis_mi = pozisyon["type"] == "POSITION_TYPE_BUY"
        r = abs(giris - stop)
        if r <= 0:
            return False

        baglanti = await mt5_veri.baglanti_al()
        fiyat = await baglanti.get_symbol_price(self.sembol)
        simdi = fiyat["bid"] if alis_mi else fiyat["ask"]

        if alis_mi:
            if stop >= giris or simdi < giris + self.basabas_r * r:
                return False
        else:
            if stop <= giris or simdi > giris - self.basabas_r * r:
                return False

        # --- BROKER KISITLARI -------------------------------------------
        # MetaQuotes-Demo'da ikisi de 0, yani burada hicbir sey degismez.
        # Gercek brokerde sifir degil ve bu kontroller olmazsa basabasa
        # cekme TAM KRITIK ANDA hata verir.
        sinir = await mt5_veri.sembol_sinirlari(self.sembol)
        hedef = pozisyon.get("takeProfit")

        # 1) DONDURMA BOLGESI: fiyat mevcut stop veya hedefe cok yakinsa
        #    broker degisiklige hic izin vermez. Hata almak yerine bu turu
        #    atla - 15 dakika sonra tekrar denenecek.
        if sinir["dondurma"] > 0:
            for ad, seviye in (("stop", stop), ("hedef", hedef)):
                if seviye and abs(simdi - seviye) < sinir["dondurma"]:
                    print(f"  BASABAS ERTELENDI: fiyat {ad} seviyesine {abs(simdi-seviye):.5f} "
                          f"uzaklikta, brokerin dondurma mesafesi {sinir['dondurma']:.5f} - "
                          f"emir su an degistirilemez, sonraki turda tekrar denenecek.")
                    return False

        # 2) ASGARI STOP MESAFESI: yeni stop (= giris fiyati) guncel fiyata
        #    brokerin izin verdiginden yakinsa emir reddedilir. Bu, 1R'lik
        #    kar brokerin asgari mesafesinden kucukse olur.
        if abs(simdi - giris) < sinir["asgari_stop"]:
            print(f"  BASABAS ERTELENDI: giris fiyati guncel fiyata {abs(simdi-giris):.5f} "
                  f"uzaklikta, brokerin asgari stop mesafesi {sinir['asgari_stop']:.5f} - "
                  f"fiyat biraz daha uzaklasinca cekilecek.")
            return False

        try:
            await baglanti.modify_position(pozisyon["id"], stop_loss=giris, take_profit=hedef)
        except Exception as exc:  # noqa: BLE001 - basabas basarisiz olsa da bot devam etmeli
            print(f"  BASABAS BASARISIZ ({exc}) - pozisyon orijinal stopuyla devam ediyor, "
                  f"sonraki turda tekrar denenecek.")
            return False

        print(f"  BASABAS: kar 1R'ye ulasti, stop girise cekildi ({giris:.5f}) - bu islem artik zarar edemez.")
        telegram_bildirim.basabasa_cekildi(self.sembol, giris)
        return True

    def _yon_hesapla(self, df) -> str | None:
        if self.strateji == "meanrev":
            return backtest._yon_serisi_mean_reversion(df)[-1]
        return backtest._yon_serisi_confluence(df, self.esik)[-1]

    async def _pozisyon_getir(self) -> dict | None:
        baglanti = await mt5_veri.baglanti_al()
        pozisyonlar = await baglanti.get_positions()
        return next((p for p in pozisyonlar if p["symbol"] == self.sembol), None)

    async def mevcut_pozisyon_yonu(self) -> str | None:
        pozisyon = await self._pozisyon_getir()
        if pozisyon is None:
            return None
        return "AL" if pozisyon["type"] == "POSITION_TYPE_BUY" else "SAT"

    async def kar_zarar(self) -> float:
        baglanti = await mt5_veri.baglanti_al()
        pozisyonlar = await baglanti.get_positions()
        return sum(p["profit"] for p in pozisyonlar if p["symbol"] == self.sembol)

    async def pozisyonu_kapat(self) -> dict:
        baglanti = await mt5_veri.baglanti_al()
        return await baglanti.close_positions_by_symbol(self.sembol)

    async def pozisyon_ac(self, yon: str, df) -> dict:
        if yon not in ("AL", "SAT"):
            return {"durum": "sinyal_yok"}
        if await self.mevcut_pozisyon_yonu() is not None:
            return {"durum": "zaten_acik_pozisyon_var"}

        baglanti = await mt5_veri.baglanti_al()
        hesap = await baglanti.get_account_information()
        # BAKIYE degil OZSERMAYE: bakiye sadece kapanmis islemleri sayar,
        # ozsermaye acik pozisyonlarin anlik zararini da icerir. Bakiye
        # kullanilsaydi hesap 90.000'e dusse bile bakiye 99.958 kaldigi
        # surece ayni buyuklukte risk alinirdi. Ozsermaye ile kayip
        # arttikca pozisyonlar otomatik kuculur (ve toparlayinca buyur).
        bakiye = hesap["equity"]
        fiyat = await baglanti.get_symbol_price(self.sembol)

        alis_mi = yon == "AL"
        giris = fiyat["ask"] if alis_mi else fiyat["bid"]
        ham = risk.stop_ve_hedef_hesapla(df, giris, alis_mi, atr_carpani=1.5,
                                          risk_odul_orani=self.risk_odul_orani)
        # Brokerin asgari stop mesafesine uydur - ihlal edilirse emrin TAMAMI
        # reddedilir, yani sinyal kacar. Gerekirse stop/hedef birlikte genisler.
        sinir = await mt5_veri.sembol_sinirlari(self.sembol)
        stop_hedef = risk.broker_sinirina_uydur(giris, ham["stop_loss"], ham["take_profit"],
                                                 alis_mi, sinir["asgari_stop"], sinir["basamak"])
        # XAUUSD/XAGUSD'de kar para birimi zaten USD oldugu icin carpan 1.0
        # doner ve hesap degismez; yine de genel dogru olsun diye burada da
        # sorulmasi lazim (bkz. mt5_veri.kar_kuru_carpani).
        kur = await mt5_veri.kar_kuru_carpani(self.sembol)
        # Lot MUTLAKA nihai stop mesafesinden hesaplanmali - stop genisletildiyse
        # eski mesafeyle hesaplamak riski %1'in uzerine cikarirdi.
        lot = risk.lot_hesapla(stop_hedef["stop_mesafesi"], self.kontrat_buyuklugu,
                                bakiye, kur_carpani=kur, fiyat=giris,
                                azami_lot_broker=await mt5_veri.azami_lot(self.sembol))

        emir_fn = baglanti.create_market_buy_order if alis_mi else baglanti.create_market_sell_order
        sonuc = await emir_fn(self.sembol, lot, stop_hedef["stop_loss"], stop_hedef["take_profit"])
        telegram_bildirim.pozisyon_acildi(self.sembol, yon, lot, giris,
                                           stop_hedef["stop_loss"], stop_hedef["take_profit"], bakiye)
        return {"durum": "islem_acildi", "yon": yon, "giris": giris, "lot": lot, **stop_hedef, "sonuc": sonuc}

    async def calistir(self) -> None:
        # Once broker tarafinda kapanmis pozisyon var mi diye bak. Stop/hedef
        # kapanislarini bot hicbir zaman canli gormuyor (15 dakikada bir
        # calisiyor), bu yuzden gecmisten geriye donuk taraniyor.
        # SADECE OKUR VE BILDIRIR - hicbir pozisyona dokunmaz.
        await kapanis_bildirimi.kapanislari_bildir(await mt5_veri.baglanti_al(), self.sembol)

        ham = await mt5_veri.mum_verisi_getir(self.sembol, self.zaman_dilimi, 200)
        df = _tamamlanmis_barlar(ham)
        yon = self._yon_hesapla(df)
        print(f"{self.sembol} {ham['close'].iloc[-1]:.5f} "
              f"(sinyal {df.index[-1].strftime('%H:%M')} kapanisindan: {df['close'].iloc[-1]:.5f}) "
              f"| {self.strateji} sinyali: {yon or 'YOK'}")

        acik = await self._pozisyon_getir()
        mevcut = None if acik is None else ("AL" if acik["type"] == "POSITION_TYPE_BUY" else "SAT")
        if mevcut is not None:
            gosterim_mi = gosterim.gosterim_mi(self.sembol)
            etiket = " [gosterim]" if gosterim_mi else ""
            print(f"  Acik pozisyon: {mevcut}{etiket} | kar/zarar: {await self.kar_zarar():+.2f} USD")
            await self._basabasa_cek(acik)

            # Gosterim pozisyonu, GERCEK sinyal geldigi anda yerini stratejinin
            # kendi pozisyonuna birakir - yonu ayni olsa bile, cunku stop/hedef
            # seviyeleri sinyal fiyatina gore yeniden kurulmali.
            if gosterim_mi and yon is not None:
                print(f"  GERCEK SINYAL GELDI ({yon}) - gosterim pozisyonu kapatilip sinyale gore aciliyor...")
                kz = await self.kar_zarar()
                print(f"  Kapama: {(await self.pozisyonu_kapat())['stringCode']}")
                telegram_bildirim.pozisyon_kapandi(self.sembol, mevcut, kz, "gercek sinyal geldi, yerini strateji pozisyonu aldi")
                gosterim.isareti_kaldir(self.sembol)
                await self._ac_ve_yazdir(yon, df)
                return

            if self.sinyal_tersine_cikis and yon is not None and yon != mevcut:
                print("  Sinyal ters dondu, kapatiliyor...")
                kz = await self.kar_zarar()
                print(f"  Kapama: {(await self.pozisyonu_kapat())['stringCode']}")
                telegram_bildirim.pozisyon_kapandi(self.sembol, mevcut, kz, "sinyal ters dondu")
                gosterim.isareti_kaldir(self.sembol)
            else:
                print("  MT5'in kendi stop/hedefiyle acik kaliyor.")
            return

        gosterim.isareti_kaldir(self.sembol)  # pozisyon kapanmis, isaret bayat
        if yon is None:
            print("  Pozisyon yok, sinyal de yok - beklemede.")
            return

        if self.izinli_saatler is not None:
            saat = dt.datetime.now(dt.timezone.utc).hour
            if saat not in self.izinli_saatler:
                print(f"  Sinyal var ({yon}) ama saat {saat:02d}:xx UTC islem penceresi disinda - atlaniyor.")
                return

        # BAR BASINA TEK GIRIS: backtest bir barda en fazla bir kez girer,
        # canli bot ise 15 dakikada bir calistigi icin ayni bara 4 kez
        # girebilir. Olculdu (AUDNZD, 2-3 Agustos): stop yedikten dakikalar
        # sonra ayni bardan yeniden girip tekrar stop olmus. Bkz. bar_kilidi.
        bar_bas = bar_kilidi.acik_bar_baslangici(ham)
        if await bar_kilidi.bu_barda_giris_var_mi(await mt5_veri.baglanti_al(), self.sembol, bar_bas):
            print(f"  Sinyal var ({yon}) ama {bar_bas.strftime('%H:%M')} barinda zaten giris "
                  f"yapilmis - yeni bar acilana kadar tekrar girilmiyor.")
            return

        await self._ac_ve_yazdir(yon, df, bar_bas)

    async def _ac_ve_yazdir(self, yon: str, df, bar_bas=None) -> None:
        sonuc = await self.pozisyon_ac(yon, df)
        if sonuc["durum"] == "islem_acildi":
            # Bar kilidinin yerel kaydi - bir sonraki calistirma bu barda
            # tekrar girmesin (bkz. bar_kilidi).
            if bar_bas is not None:
                bar_kilidi.girisi_kaydet(self.sembol, bar_bas)
            print(f"  ACILDI: {yon} {sonuc['lot']} lot @ {sonuc['giris']:.5f} | "
                  f"stop {sonuc['stop_loss']:.5f} | hedef {sonuc['take_profit']:.5f}")
        else:
            print(f"  {sonuc['durum']}")
