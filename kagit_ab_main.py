"""Kagit takip calistirma girisi - A+B sistemi (XAUUSD 8 saatlik).

GERCEK EMIR GONDERMEZ. Hesap 1'in kimlik bilgileriyle baglanir ama sadece
FIYAT VERISI okur; pozisyon acmaz, kapatmaz, degistirmez.

Neden hesap 1: yeni bir MetaApi hesabi acmak maliyeti %33 artirirdi.
Veri okumak icin hangi hesaba baglandigin fark etmiyor - fiyat ayni.

Kagit islemler kagit_ab*.jsonl dosyasinda birikir; workflow cache'i onu
calistirmalar arasinda tasir.

Bkz. kagit_ab.py modul basligi - sistem tanimi, olculen beklenti ve
rejim uyarisi orada."""
from __future__ import annotations

import asyncio

import kagit_ab


async def calistir() -> None:
    try:
        await kagit_ab.calistir()
    except Exception as e:  # noqa: BLE001 - kagit takip hatasi diger botlari etkilemesin
        print(f"KAGIT A+B hatasi ({type(e).__name__}: {e}) - "
              f"sonraki calistirmada tekrar denenecek.")


if __name__ == "__main__":
    asyncio.run(calistir())
