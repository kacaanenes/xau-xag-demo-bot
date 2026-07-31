"""AUDNZD icin emir yonetimi - tek enstruman oldugu icin XAU/XAG'daki gibi
bacak ayirmaya gerek yok, dogrudan MT5'in kendi stop-loss/take-profit'i
kullanilir. SADECE demo hesap icindir."""
from __future__ import annotations

import mt5_veri
import risk

SEMBOL = "AUDNZD"
KONTRAT_BUYUKLUGU = 100000


async def mevcut_pozisyon_yonu() -> str | None:
    baglanti = await mt5_veri.baglanti_al()
    pozisyonlar = await baglanti.get_positions()
    pozisyon = next((p for p in pozisyonlar if p["symbol"] == SEMBOL), None)
    if pozisyon is None:
        return None
    return "AL" if pozisyon["type"] == "POSITION_TYPE_BUY" else "SAT"


async def kar_zarar() -> float:
    baglanti = await mt5_veri.baglanti_al()
    pozisyonlar = await baglanti.get_positions()
    return sum(p["profit"] for p in pozisyonlar if p["symbol"] == SEMBOL)


async def pozisyonu_kapat() -> dict:
    baglanti = await mt5_veri.baglanti_al()
    return await baglanti.close_positions_by_symbol(SEMBOL)


async def pozisyon_ac(yon: str, df) -> dict:
    if yon not in ("AL", "SAT"):
        return {"durum": "sinyal_yok"}

    if await mevcut_pozisyon_yonu() is not None:
        return {"durum": "zaten_acik_pozisyon_var"}

    baglanti = await mt5_veri.baglanti_al()
    hesap_bilgisi = await baglanti.get_account_information()
    bakiye = hesap_bilgisi["balance"]

    fiyat = await baglanti.get_symbol_price(SEMBOL)
    alis_mi = yon == "AL"
    giris = fiyat["ask"] if alis_mi else fiyat["bid"]

    stop_hedef = risk.stop_ve_hedef_hesapla(df, giris, alis_mi, atr_carpani=1.5)
    stop_mesafesi = abs(giris - stop_hedef["stop_loss"])
    lot = risk.lot_hesapla(stop_mesafesi, KONTRAT_BUYUKLUGU, bakiye)

    if alis_mi:
        sonuc = await baglanti.create_market_buy_order(SEMBOL, lot, stop_hedef["stop_loss"], stop_hedef["take_profit"])
    else:
        sonuc = await baglanti.create_market_sell_order(SEMBOL, lot, stop_hedef["stop_loss"], stop_hedef["take_profit"])

    return {"durum": "islem_acildi", "yon": yon, "giris": giris, "lot": lot, **stop_hedef, "sonuc": sonuc}
