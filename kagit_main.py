"""Mean-reversion stratejisini GERCEK EMIR ACMADAN, kagit uzerinde
calistirir (kapanis-bazli ATR + 1:2 risk/odul - olculerek en iyi cikan
kombinasyon). Kisa bir dogrulama sonrasi gercek demo hesaba alinacak.
SADECE olcum/dogrulama amaclidir - MT5 hesabinda hicbir emir vermez."""
from __future__ import annotations

import asyncio
import datetime

import backtest
import kagit_defter
import mt5_veri
import teknik

LOT = 0.01
STRATEJI_ADI = "meanrev"
AYARLAR = {"sl_atr_carpani": 1.5, "risk_odul_orani": 2.0, "sinyal_tersine_cikis": False}


def _simdi() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


async def strateji_adimi(yon_su_an, rasyo_son, rasyo_df, xau_fiyat, xag_fiyat) -> str:
    durum = kagit_defter.durum_oku(STRATEJI_ADI)

    if durum is not None:
        tetiklendi, sebep = False, None
        if durum["yon"] == "AL":
            if rasyo_son <= durum["stop_orani"]:
                tetiklendi, sebep = True, "stop"
            elif rasyo_son >= durum["hedef_orani"]:
                tetiklendi, sebep = True, "hedef"
        else:
            if rasyo_son >= durum["stop_orani"]:
                tetiklendi, sebep = True, "stop"
            elif rasyo_son <= durum["hedef_orani"]:
                tetiklendi, sebep = True, "hedef"

        if not tetiklendi and AYARLAR["sinyal_tersine_cikis"] and yon_su_an is not None and yon_su_an != durum["yon"]:
            tetiklendi, sebep = True, "sinyal_tersine_dondu"

        if not tetiklendi:
            return f"ACIK KALIYOR ({durum['yon']}, giris {durum['giris_orani']:.4f}, stop {durum['stop_orani']:.4f}, hedef {durum['hedef_orani']:.4f})"

        xau_isareti = 1 if durum["yon"] == "AL" else -1
        xag_isareti = -1 if durum["yon"] == "AL" else 1
        xau_cikis_fiyat = xau_fiyat["bid"] if durum["yon"] == "AL" else xau_fiyat["ask"]
        xag_cikis_fiyat = xag_fiyat["ask"] if durum["yon"] == "AL" else xag_fiyat["bid"]

        xau_pnl = (xau_cikis_fiyat - durum["xau_giris"]) * xau_isareti * LOT * backtest.XAU_KONTRAT_BUYUKLUGU
        xag_pnl = (xag_cikis_fiyat - durum["xag_giris"]) * xag_isareti * LOT * backtest.XAG_KONTRAT_BUYUKLUGU
        toplam_pnl = xau_pnl + xag_pnl

        kagit_defter.gecmise_ekle({
            "strateji": STRATEJI_ADI,
            "yon": durum["yon"],
            "giris_orani": durum["giris_orani"],
            "cikis_orani": rasyo_son,
            "sebep": sebep,
            "xau_pnl_usd": round(xau_pnl, 2),
            "xag_pnl_usd": round(xag_pnl, 2),
            "toplam_pnl_usd": round(toplam_pnl, 2),
            "acilis_zamani": durum["acilis_zamani"],
            "kapanis_zamani": _simdi(),
        })
        kagit_defter.durum_temizle(STRATEJI_ADI)
        return f"KAPANDI ({sebep}): {toplam_pnl:.2f} USD"

    if yon_su_an is None:
        return "pozisyon yok, sinyal yok"

    atr = teknik.atr_kapanis_bazli(rasyo_df["close"], 14).iloc[-1]
    stop_mesafesi = AYARLAR["sl_atr_carpani"] * atr
    hedef_mesafesi = AYARLAR["risk_odul_orani"] * stop_mesafesi
    if yon_su_an == "AL":
        stop_orani = rasyo_son - stop_mesafesi
        hedef_orani = rasyo_son + hedef_mesafesi
    else:
        stop_orani = rasyo_son + stop_mesafesi
        hedef_orani = rasyo_son - hedef_mesafesi

    xau_giris_fiyat = xau_fiyat["ask"] if yon_su_an == "AL" else xau_fiyat["bid"]
    xag_giris_fiyat = xag_fiyat["bid"] if yon_su_an == "AL" else xag_fiyat["ask"]

    kagit_defter.durum_kaydet(STRATEJI_ADI, {
        "yon": yon_su_an,
        "giris_orani": rasyo_son,
        "stop_orani": round(float(stop_orani), 5),
        "hedef_orani": round(float(hedef_orani), 5),
        "xau_giris": xau_giris_fiyat,
        "xag_giris": xag_giris_fiyat,
        "acilis_zamani": _simdi(),
    })
    return f"YENI KAGIT POZISYON: {yon_su_an}"


async def calistir() -> None:
    rasyo_df = await mt5_veri.parite_serisi_getir("1h", 200)
    baglanti = await mt5_veri.baglanti_al()
    xau_fiyat = await baglanti.get_symbol_price(mt5_veri.XAU_SEMBOL)
    xag_fiyat = await baglanti.get_symbol_price(mt5_veri.XAG_SEMBOL)

    rasyo_son = float(rasyo_df["close"].iloc[-1])
    yon_su_an = backtest._yon_serisi_mean_reversion(rasyo_df)[-1]

    print(f"Rasyo: {rasyo_son:.4f} | Mean-reversion sinyali: {yon_su_an}")

    sonuc = await strateji_adimi(yon_su_an, rasyo_son, rasyo_df, xau_fiyat, xag_fiyat)
    print(f"[meanrev] {sonuc}")

    gecmis = kagit_defter.gecmisi_oku(STRATEJI_ADI)
    toplam = sum(k["toplam_pnl_usd"] for k in gecmis)
    kazanan = sum(1 for k in gecmis if k["toplam_pnl_usd"] > 0)
    print(f"  >> {len(gecmis)} kapanan kagit islem, kazanan {kazanan}, kumulatif $PnL={toplam:.2f}")


if __name__ == "__main__":
    asyncio.run(calistir())
