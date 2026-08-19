"""[EMEKLI - sadece parite botu kullanir, workflow calistirmiyor]
Parite sinyaline gore XAUUSD + XAGUSD bacaklarini AYNI ANDA acar.
SADECE demo hesap icindir - gercek/canli hesaba asla baglanmamali."""
from __future__ import annotations

import mt5_veri
import pozisyon_durumu
import risk

_SEMBOLLER = (mt5_veri.XAU_SEMBOL, mt5_veri.XAG_SEMBOL)


async def acik_pozisyon_var_mi() -> bool:
    baglanti = await mt5_veri.baglanti_al()
    pozisyonlar = await baglanti.get_positions()
    return any(p["symbol"] in _SEMBOLLER for p in pozisyonlar)


async def mevcut_pozisyon_yonu() -> str | None:
    """Acik parite pozisyonunun yonunu XAU bacagindan okur: XAU AL -> 'AL',
    XAU SAT -> 'SAT'. Pozisyon yoksa None doner."""
    baglanti = await mt5_veri.baglanti_al()
    pozisyonlar = await baglanti.get_positions()
    xau_pozisyon = next((p for p in pozisyonlar if p["symbol"] == mt5_veri.XAU_SEMBOL), None)
    if xau_pozisyon is None:
        return None
    return "AL" if xau_pozisyon["type"] == "POSITION_TYPE_BUY" else "SAT"


async def acik_pozisyonlarin_kar_zarari() -> dict:
    baglanti = await mt5_veri.baglanti_al()
    pozisyonlar = await baglanti.get_positions()
    ilgili = [p for p in pozisyonlar if p["symbol"] in _SEMBOLLER]
    detay = {p["symbol"]: p["profit"] for p in ilgili}
    return {"toplam": sum(detay.values()), "detay": detay}


async def parite_pozisyonunu_kapat() -> dict:
    baglanti = await mt5_veri.baglanti_al()
    xau_sonuc = await baglanti.close_positions_by_symbol(mt5_veri.XAU_SEMBOL)
    xag_sonuc = await baglanti.close_positions_by_symbol(mt5_veri.XAG_SEMBOL)
    pozisyon_durumu.temizle()
    return {"xau": xau_sonuc, "xag": xag_sonuc}


async def parite_islemi_ac(yon: str, rasyo_df, giris_orani: float, zaman_dilimi: str = "15m") -> dict:
    if yon not in ("AL", "SAT"):
        return {"durum": "sinyal_yok"}

    if await acik_pozisyon_var_mi():
        return {"durum": "zaten_acik_pozisyon_var"}

    baglanti = await mt5_veri.baglanti_al()

    hesap_bilgisi = await baglanti.get_account_information()
    # BAKIYE degil OZSERMAYE - bkz. tek_enstruman.py'deki aciklama.
    bakiye = hesap_bilgisi["equity"]

    xau_fiyat = await baglanti.get_symbol_price(mt5_veri.XAU_SEMBOL)
    xag_fiyat = await baglanti.get_symbol_price(mt5_veri.XAG_SEMBOL)
    xau_df = await mt5_veri.mum_verisi_getir(mt5_veri.XAU_SEMBOL, zaman_dilimi, 100)
    xag_df = await mt5_veri.mum_verisi_getir(mt5_veri.XAG_SEMBOL, zaman_dilimi, 100)

    # "AL" = rasyo yukselecek = XAU AL + XAG SAT. "SAT" = tam tersi.
    xau_alis_mi = yon == "AL"
    xag_alis_mi = yon == "SAT"

    xau_giris = xau_fiyat["ask"] if xau_alis_mi else xau_fiyat["bid"]
    xag_giris = xag_fiyat["ask"] if xag_alis_mi else xag_fiyat["bid"]

    # Bacak seviyesindeki stop/hedef artik sadece genis bir felaket guvenlik
    # agi - asil kapama karari rasyonun kendi stop/hedefine gore (asagida
    # kaydedilen pozisyon_durumu uzerinden) main.py'de veriliyor.
    xau_risk = risk.stop_ve_hedef_hesapla(xau_df, xau_giris, xau_alis_mi, risk.GUVENLIK_AGI_CARPANI)
    xag_risk = risk.stop_ve_hedef_hesapla(xag_df, xag_giris, xag_alis_mi, risk.GUVENLIK_AGI_CARPANI)

    # Sabit dolar yerine bakiyenin %1'i kadar risk hedeflenir: genis stop ->
    # kucuk lot, dar stop -> buyuk lot, ama risk her zaman bakiyeye oranli
    # sabit kalir (hesap buyudukce/kuculdukce otomatik olcekler).
    xau_stop_mesafesi = abs(xau_giris - xau_risk["stop_loss"])
    xag_stop_mesafesi = abs(xag_giris - xag_risk["stop_loss"])
    xau_lot = risk.lot_hesapla(xau_stop_mesafesi, risk.XAU_KONTRAT_BUYUKLUGU, bakiye)
    xag_lot = risk.lot_hesapla(xag_stop_mesafesi, risk.XAG_KONTRAT_BUYUKLUGU, bakiye)

    if xau_alis_mi:
        xau_sonuc = await baglanti.create_market_buy_order(
            mt5_veri.XAU_SEMBOL, xau_lot, xau_risk["stop_loss"], xau_risk["take_profit"]
        )
    else:
        xau_sonuc = await baglanti.create_market_sell_order(
            mt5_veri.XAU_SEMBOL, xau_lot, xau_risk["stop_loss"], xau_risk["take_profit"]
        )

    if xag_alis_mi:
        xag_sonuc = await baglanti.create_market_buy_order(
            mt5_veri.XAG_SEMBOL, xag_lot, xag_risk["stop_loss"], xag_risk["take_profit"]
        )
    else:
        xag_sonuc = await baglanti.create_market_sell_order(
            mt5_veri.XAG_SEMBOL, xag_lot, xag_risk["stop_loss"], xag_risk["take_profit"]
        )

    rasyo_risk = risk.rasyo_stop_hedef_hesapla(rasyo_df, giris_orani, alis_mi=(yon == "AL"))
    pozisyon_durumu.kaydet({
        "yon": yon,
        "giris_orani": giris_orani,
        "stop_orani": rasyo_risk["stop_orani"],
        "hedef_orani": rasyo_risk["hedef_orani"],
    })

    return {
        "durum": "islem_acildi",
        "yon": yon,
        "rasyo": {"giris": giris_orani, **rasyo_risk},
        "xau": {"alis_mi": xau_alis_mi, "giris": xau_giris, "lot": xau_lot, **xau_risk, "sonuc": xau_sonuc},
        "xag": {"alis_mi": xag_alis_mi, "giris": xag_giris, "lot": xag_lot, **xag_risk, "sonuc": xag_sonuc},
    }
