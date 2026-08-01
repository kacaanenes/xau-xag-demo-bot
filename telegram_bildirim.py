"""Telegram bildirimi - SADECE anlamli olaylarda.

Bot 15 dakikada bir calisiyor; her turda "sinyal yok" mesaji atmak gunde
~96 bildirim demek olurdu. Bu yuzden sadece su uc olayda mesaj gider:
pozisyon acildi, pozisyon kapandi, stop basabasa cekildi.

Telegram yapilandirilmamissa (token/chat_id yoksa) sessizce atlanir -
bildirim gonderememek botun islem yapmasini ENGELLEMEMELI.
"""
from __future__ import annotations

import os

import requests

_TIMEOUT = 15
_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_HEDEFLER = [c.strip() for c in os.getenv("TELEGRAM_CHAT_ID", "").split(",") if c.strip()]


def _gonder(metin: str) -> None:
    if not _TOKEN or not _HEDEFLER:
        return
    for hedef in _HEDEFLER:
        try:
            requests.post(
                f"https://api.telegram.org/bot{_TOKEN}/sendMessage",
                json={"chat_id": hedef, "text": metin, "parse_mode": "HTML"},
                timeout=_TIMEOUT,
            ).raise_for_status()
        except requests.RequestException as exc:
            # Bildirim gonderilemedi diye islem akisi bozulmamali
            print(f"  (Telegram bildirimi gonderilemedi: {exc})")


def pozisyon_acildi(sembol: str, yon: str, lot: float, giris: float,
                    stop: float, hedef: float, bakiye: float) -> None:
    risk = abs(giris - stop)
    odul = abs(hedef - giris)
    ok = "🟢" if yon == "AL" else "🔴"
    _gonder(
        f"{ok} <b>{sembol} — {yon}</b>\n\n"
        f"Giriş: <b>{giris:.5f}</b>  ({lot} lot)\n"
        f"Stop: {stop:.5f}  ({risk:.5f} uzakta)\n"
        f"Hedef: {hedef:.5f}  ({odul:.5f} uzakta)\n"
        f"Risk/Ödül: 1:{odul/risk:.1f}\n\n"
        f"<i>Bakiye: {bakiye:,.2f} USD</i>"
    )


def pozisyon_kapandi(sembol: str, yon: str, kar_zarar: float, sebep: str) -> None:
    ok = "✅" if kar_zarar >= 0 else "❌"
    _gonder(
        f"{ok} <b>{sembol} — {yon} kapandı</b>\n\n"
        f"Sonuç: <b>{kar_zarar:+.2f} USD</b>\n"
        f"Sebep: {sebep}"
    )


def pozisyon_kapandi_detayli(sembol: str, yon: str, kar_zarar: float, sebep: str,
                              cikis_fiyati=None, lot=None, kapanis_zamani=None,
                              bakiye=None) -> None:
    """Broker tarafinda (stop/hedef) kapanan pozisyonlar icin durum bildirimi.

    pozisyon_kapandi()'dan farki: bu mesaj gecmisten geriye donuk taramayla
    uretiliyor, bu yuzden kapanis fiyati/zamani/hacmi gibi ek bilgiler var."""
    ok = "✅" if kar_zarar >= 0 else "❌"
    baslik = "KÂR" if kar_zarar >= 0 else "ZARAR"

    satirlar = [f"{ok} <b>{sembol} — {yon} kapandı ({baslik})</b>", ""]
    satirlar.append(f"Sonuç: <b>{kar_zarar:+.2f} USD</b>")
    satirlar.append(f"Sebep: {sebep}")
    if cikis_fiyati is not None:
        hacim = f"  ({lot} lot)" if lot is not None else ""
        satirlar.append(f"Çıkış: {cikis_fiyati}{hacim}")
    if kapanis_zamani is not None:
        satirlar.append(f"Zaman: {str(kapanis_zamani)[:19]} UTC")
    if bakiye is not None:
        yuzde = kar_zarar / bakiye * 100 if bakiye else 0.0
        satirlar.append("")
        satirlar.append(f"<i>Bakiye: {bakiye:,.2f} USD  ({yuzde:+.2f}%)</i>")

    _gonder("\n".join(satirlar))


def basabasa_cekildi(sembol: str, giris: float) -> None:
    _gonder(
        f"🛡 <b>{sembol} — başabaş korumasi</b>\n\n"
        f"Kâr 1R'ye ulaştı, stop girişe çekildi ({giris:.5f}).\n"
        f"<i>Bu işlem artık zarar edemez.</i>"
    )
