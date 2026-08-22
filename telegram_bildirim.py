"""Telegram bildirimi - SADECE anlamli olaylarda.

Bot 15 dakikada bir calisiyor; her turda "sinyal yok" mesaji atmak gunde
~96 bildirim demek olurdu. Bu yuzden sadece su olaylarda mesaj gider:
pozisyon acildi, pozisyon kapandi, stop basabasa cekildi - ve ayrica
SISTEM UYARISI (bir bot adimi coktu ya da botlar uzun sure hic calismadi;
bkz. kosum_kontrol.py). Sistem uyarisi da nadir bir olaydir: her sey
yolundayken hic gonderilmez.

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


def sistem_uyarisi(baslik: str, satirlar: list[str]) -> None:
    """Islem degil, SISTEM sorunu bildirir (bot adimi coktu, botlar
    calismadi vb.). Ayri bir fonksiyon olmasinin sebebi, islem
    bildirimleriyle karismamasi: bu mesajlar hesapla degil, ALTYAPIYLA
    ilgilidir ve gorulmezse sessiz bir durus fark edilmeden gecer."""
    _gonder(f"🚨 <b>{baslik}</b>\n\n" + "\n".join(satirlar))


def pozisyon_acildi(sembol: str, yon: str, lot: float, giris: float,
                    stop: float, hedef: float | None, bakiye: float) -> None:
    """hedef=None: hedefsiz (iz suren stopla yonetilen) pozisyon.

    Donchian botu hedef koymaz. Onceden buraya 0.0 geciliyordu ve mesaj
    "Hedef: 0.00000 (4128.24000 uzakta) / Risk/Odul: 1:80.1" gibi tamamen
    yaniltici cikiyordu."""
    risk = abs(giris - stop)
    ok = "🟢" if yon == "AL" else "🔴"
    satirlar = [f"{ok} <b>{sembol} — {yon}</b>", "",
                f"Giriş: <b>{giris:.5f}</b>  ({lot} lot)",
                f"Stop: {stop:.5f}  ({risk:.5f} uzakta)"]
    if hedef:
        odul = abs(hedef - giris)
        satirlar.append(f"Hedef: {hedef:.5f}  ({odul:.5f} uzakta)")
        satirlar.append(f"Risk/Ödül: 1:{odul/risk:.1f}")
    else:
        satirlar.append("Hedef: <b>yok</b> — iz süren stopla yönetilir")
    satirlar += ["", f"<i>Bakiye: {bakiye:,.2f} USD</i>"]
    _gonder("\n".join(satirlar))


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


def stop_kara_gecti(sembol: str, yon: str, giris: float, yeni_stop: float,
                    kilitlenen: float) -> None:
    """Iz suren stop ILK KEZ giris fiyatinin karli tarafina gecti.

    NEDEN SADECE BIR KEZ: iz suren stop her 4 saatlik barda guncelleniyor,
    yani ortalama 41 saatlik bir pozisyonda ~10 kez. Her guncellemeyi
    bildirmek Telegram'i doldururdu. Anlamli an, stopun zarar tarafindan
    kar tarafina GECTIGI andir - o andan sonra islem artik zarar edemez."""
    _gonder(
        f"🛡 <b>{sembol} — {yon} artık zarar edemez</b>\n\n"
        f"İz süren stop girişin üstüne geçti.\n"
        f"Giriş: {giris:.5f}  →  Stop: <b>{yeni_stop:.5f}</b>\n"
        f"Kilitlenen: <b>{kilitlenen:+.5f}</b> puan\n\n"
        f"<i>Stop bundan sonra sadece lehe hareket eder, geri gitmez.</i>"
    )


def kagit_acildi(sembol: str, kaynak: str, yon: str, giris: float, stop: float,
                 risk: float) -> None:
    """KAGIT pozisyon acildi - gercek emir GONDERILMEDI.

    Gercek islem bildirimlerinden ayirt edilebilmesi sart: bu mesajlar
    hesapta hicbir sey degistirmez, sadece takip icindir."""
    ok = "🟢" if yon == "AL" else "🔴"
    _gonder(
        f"📝 <b>[KAGIT] {sembol} ({kaynak}) — {yon}</b>\n\n"
        f"{ok} Giriş: <b>{giris:.2f}</b>\n"
        f"Stop: {stop:.2f}  ({risk:.2f} uzakta = 1R)\n"
        f"Hedef: yok — iz süren stop 4×ATR\n\n"
        f"<i>Gerçek emir gönderilmedi. Sadece takip.</i>"
    )


def kagit_ozet(baslik: str, satirlar: list[str]) -> None:
    """Kagit takibin gunluk ozeti."""
    _gonder(f"📝 <b>{baslik}</b>\n\n" + "\n".join(satirlar))


def basabasa_cekildi(sembol: str, giris: float) -> None:
    _gonder(
        f"🛡 <b>{sembol} — başabaş korumasi</b>\n\n"
        f"Kâr 1R'ye ulaştı, stop girişe çekildi ({giris:.5f}).\n"
        f"<i>Bu işlem artık zarar edemez.</i>"
    )
