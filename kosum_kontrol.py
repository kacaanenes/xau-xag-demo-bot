"""CALISTIRMA SAGLIK KONTROLU - workflow'un sonunda calisir.

--------------------------------------------------------------------------
NEDEN GEREKLI - 19.08.2026'da olculen iki kor nokta
--------------------------------------------------------------------------
1) YESIL TIK HICBIR SEY KANITLAMIYOR
   Workflow'daki bot adimlarinin hepsinde `continue-on-error: true` var -
   ki bu dogru bir tercih: bir bot cokerse digerleri calismaya devam
   etmeli. Ama yan etkisi sinsi: adim COKSE BILE is yesil gorunur.
   Son 100 calistirmanin 99'u "success"ti ve bu, botlarin calistigi
   anlamina GELMIYORDU.

   Somut vaka: Hesap 3 (AUDNZD) 11.08'de canliya alindi ve 60 gunde HIC
   islem yapmadi. Oysa 12-13.08'de uc gecerli sinyal olustu ve en az biri
   (13.08 03:00) botun hicbir korumasina takilmiyordu. Kodun kendisi
   yerelde sorunsuz calisiyor - yani sorun ortamda (muhtemelen bir
   secret), ama adim "success" gorundugu icin 8 gun fark edilmedi.

2) CRON NEREDEYSE HIC CALISMIYOR
   Olculdu (18-19.08, 100 calistirma): cron (7,22,37,52) o pencerede 88
   kez tetiklenmeliyken 14 kez tetiklendi. Iki tetikleme arasi ortalama
   93 dakika, en uzunu 202 dakika. Botlari asil ayakta tutan sey harici
   workflow_dispatch cagrilari. O kaynak durursa botlar gunde 96 yerine
   ~14 kez calisir ve HABER VEREN OLMAZ.

--------------------------------------------------------------------------
NE YAPAR
--------------------------------------------------------------------------
- Her bot adiminin `outcome` degerini okur (workflow env olarak gecer).
- Basarisiz adim varsa Telegram'a bildirir ve KODU 1 ILE CIKAR -> is
  KIRMIZI gorunur. Botlar bu noktada zaten calismis olur; yani "digerleri
  calismaya devam etsin" ozelligi korunur, sadece sessizlik kalkar.
- Bir onceki calistirmadan bu yana gecen sureyi olcer; esigi asmissa
  "botlar N dakika calismadi" uyarisi gonderir.

Durum dosyasi (son_kosum.json) workflow cache'i ile calistirmalar
arasinda tasinir - bildirilen_kapanislar*.json ile ayni mekanizma.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

import telegram_bildirim

# Bir onceki calistirmadan bu yana gecen sure bunu asarsa uyari gider.
# Hedef aralik 15 dk; 45 dk = ust uste iki tetikleme kacirilmis demektir.
AZAMI_ARA_DAKIKA = 45

_DURUM_DOSYASI = os.path.join(os.path.dirname(__file__), "son_kosum.json")


def _adim_sonuclari() -> dict[str, str]:
    """ADIM_* env degiskenlerini {ad: sonuc} sozlugune cevirir.

    Workflow her bot adimi icin ADIM_<AD>=${{ steps.<id>.outcome }} gecer.
    `outcome`, continue-on-error UYGULANMADAN ONCEKI sonuctur - yani
    gercekte ne oldugunu soyleyen tek deger budur (`conclusion` degil)."""
    return {ad[5:].replace("_", " "): deger.strip().lower()
            for ad, deger in os.environ.items()
            if ad.startswith("ADIM_") and deger.strip()}


def _onceki_kosum() -> dt.datetime | None:
    try:
        with open(_DURUM_DOSYASI) as f:
            return dt.datetime.fromisoformat(json.load(f)["zaman"])
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return None


def _kosumu_kaydet(simdi: dt.datetime) -> None:
    try:
        with open(_DURUM_DOSYASI, "w") as f:
            json.dump({"zaman": simdi.isoformat()}, f)
    except OSError as exc:
        print(f"  (Kosum zamani yazilamadi: {exc} - bosluk tespiti bir tur atlanacak)")


def main() -> int:
    simdi = dt.datetime.now(dt.timezone.utc)
    sonuclar = _adim_sonuclari()
    basarisiz = sorted(ad for ad, s in sonuclar.items() if s not in ("success", "skipped"))

    print(f"Adim sonuclari ({len(sonuclar)} adim):")
    for ad, s in sorted(sonuclar.items()):
        print(f"  {'OK  ' if s in ('success', 'skipped') else 'HATA'}  {ad}: {s}")

    # --- calistirmalar arasi bosluk (harici tetikleyici durdu mu?) ---
    onceki = _onceki_kosum()
    if onceki is not None:
        ara = (simdi - onceki).total_seconds() / 60
        print(f"\nOnceki calistirma: {onceki:%d.%m %H:%M} UTC ({ara:.0f} dakika once)")
        if ara > AZAMI_ARA_DAKIKA:
            print(f"  UYARI: ara {AZAMI_ARA_DAKIKA} dakikayi asti.")
            telegram_bildirim.sistem_uyarisi(
                f"Botlar {ara:.0f} dakika calismadi", [
                    f"Onceki calistirma: {onceki:%d.%m %H:%M} UTC",
                    f"Bu calistirma: {simdi:%d.%m %H:%M} UTC",
                    "Beklenen ara: 15 dakika",
                    "",
                    "GitHub cron'u guvenilir tetiklemiyor; harici "
                    "tetikleyici durmus olabilir.",
                ])
    else:
        print("\nOnceki calistirma kaydi yok (ilk calistirma ya da cache kaybi).")
    _kosumu_kaydet(simdi)

    if not basarisiz:
        print("\nTum adimlar basarili.")
        return 0

    print(f"\nBASARISIZ ADIM: {', '.join(basarisiz)}")
    telegram_bildirim.sistem_uyarisi("Bot adimi HATA verdi", [
        *(f"• {ad}" for ad in basarisiz),
        "",
        f"Zaman: {simdi:%d.%m %H:%M} UTC",
        f"Log: {os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/"
        f"{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/"
        f"{os.getenv('GITHUB_RUN_ID', '')}",
    ])
    return 1


if __name__ == "__main__":
    sys.exit(main())
