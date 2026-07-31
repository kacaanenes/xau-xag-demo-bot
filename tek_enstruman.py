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
import gosterim
import mt5_veri
import risk


class TekEnstrumanBot:
    def __init__(self, sembol: str, kontrat_buyuklugu: float, strateji: str,
                 esik: int = 5, risk_odul_orani: float = 1.5, zaman_dilimi: str = "1h",
                 basabas_r: float | None = 1.0, izinli_saatler: tuple | None = None):
        if strateji not in ("meanrev", "trend"):
            raise ValueError(f"bilinmeyen strateji: {strateji}")
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

        await baglanti.modify_position(pozisyon["id"], stop_loss=giris,
                                        take_profit=pozisyon.get("takeProfit"))
        print(f"  BASABAS: kar 1R'ye ulasti, stop girise cekildi ({giris:.5f}) - bu islem artik zarar edemez.")
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
        bakiye = (await baglanti.get_account_information())["balance"]
        fiyat = await baglanti.get_symbol_price(self.sembol)

        alis_mi = yon == "AL"
        giris = fiyat["ask"] if alis_mi else fiyat["bid"]
        stop_hedef = risk.stop_ve_hedef_hesapla(df, giris, alis_mi, atr_carpani=1.5)
        lot = risk.lot_hesapla(abs(giris - stop_hedef["stop_loss"]), self.kontrat_buyuklugu, bakiye)

        emir_fn = baglanti.create_market_buy_order if alis_mi else baglanti.create_market_sell_order
        sonuc = await emir_fn(self.sembol, lot, stop_hedef["stop_loss"], stop_hedef["take_profit"])
        return {"durum": "islem_acildi", "yon": yon, "giris": giris, "lot": lot, **stop_hedef, "sonuc": sonuc}

    async def calistir(self) -> None:
        df = await mt5_veri.mum_verisi_getir(self.sembol, self.zaman_dilimi, 200)
        yon = self._yon_hesapla(df)
        print(f"{self.sembol} {df['close'].iloc[-1]:.5f} | {self.strateji} sinyali: {yon or 'YOK'}")

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
                print(f"  Kapama: {(await self.pozisyonu_kapat())['stringCode']}")
                gosterim.isareti_kaldir(self.sembol)
                await self._ac_ve_yazdir(yon, df)
                return

            if yon is not None and yon != mevcut:
                print("  Sinyal ters dondu, kapatiliyor...")
                print(f"  Kapama: {(await self.pozisyonu_kapat())['stringCode']}")
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

        await self._ac_ve_yazdir(yon, df)

    async def _ac_ve_yazdir(self, yon: str, df) -> None:
        sonuc = await self.pozisyon_ac(yon, df)
        if sonuc["durum"] == "islem_acildi":
            print(f"  ACILDI: {yon} {sonuc['lot']} lot @ {sonuc['giris']:.5f} | "
                  f"stop {sonuc['stop_loss']:.5f} | hedef {sonuc['take_profit']:.5f}")
        else:
            print(f"  {sonuc['durum']}")
