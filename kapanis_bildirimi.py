"""Broker tarafinda kapanan pozisyonlari bulup Telegram'a bildirir.

NEDEN AYRI BIR MODUL GEREKTI:
Pozisyonlarimizin cogu BROKER tarafinda kapaniyor - fiyat stop veya hedefe
degince MT5 sunucusu kendisi kapatiyor. Bot 15 dakikada bir calistigi icin o
ani hicbir zaman gormuyor; sadece "pozisyon yok" durumunu goruyor. Bu yuzden
kapanislari islem GECMISINDEN geriye donuk tariyoruz.

(telegram_bildirim.pozisyon_kapandi zaten vardi ama yalnizca BOTUN KENDI
kapattigi durumda cagriliyordu - sinyal ters dondugunde. Stop/hedef
kapanislarinda hicbir mesaj gitmiyordu.)

TEKRAR BILDIRIM SORUNU - DIKKAT:
Her calistirmada ayni kapanis tekrar bulunur. Bunu onlemek icin bildirilen
deal id'leri bir dosyada tutuluyor. GitHub Actions'ta her calistirma TEMIZ bir
makinede basladigi icin bu dosyanin actions/cache ile tasinmasi ZORUNLUDUR -
yoksa ayni kapanis mesaji her 15 dakikada bir tekrar gider. Workflow'daki
cache adimini kaldirmayin.

SADECE demo hesap icindir. Canli/gercek hesaba asla baglanmamali.
"""
from __future__ import annotations

import datetime as dt
import json
import os

import telegram_bildirim

_HESAP_ETIKETI = os.getenv("HESAP_ETIKETI", "")


def _dosya_yolu(sembol: str) -> str:
    """Durum dosyasi SEMBOL BASINA ayri tutulur.

    NEDEN - olculdu: XAUUSD ve XAGUSD ayni hesapta, workflow'da ARDI ARDINA
    calisiyor ve tek bir dosyayi paylasiyorlardi. Cache bos oldugunda:
      1) xau_main calisir, dosya YOK  -> koruma aktif, sadece son 20 dk
      2) xau_main dosyayi olusturur
      3) xag_main calisir, dosya VAR  -> koruma DEVRE DISI kalir ve
         XAGUSD'nin 12 saatlik penceredeki TUM kapanislari bildirilir
    Sonuc: cache her kayboldugunda XAGUSD icin mesaj yagmuru. Ayri dosya
    ile her sembol kendi ilk-calistirma korumasini kullanir."""
    return os.path.join(os.path.dirname(__file__),
                        f"bildirilen_kapanislar_{sembol}{_HESAP_ETIKETI}.json")

# Geriye donuk tarama penceresi. Cron 15 dakikada bir calisiyor; pencere bundan
# genis tutuldu ki gecikmis/atlanmis bir calistirmada kapanis kacmasin. Tekrar
# bildirimi zaten deal id kaydi engelliyor, o yuzden genis olmasinin zarari yok.
_TARAMA_SAATI = int(os.getenv("KAPANIS_TARAMA_SAATI", "12"))

# Dosya sinirsiz buyumesin - 12 saatlik pencereden cok daha fazlasi zaten
# gereksiz, ama guvenli tarafta kalmak icin son 300 kayit tutuluyor.
_AZAMI_KAYIT = 300

# DURUM DOSYASI YOKKEN (ilk calistirma, ya da bulutta cache kurulmamissa)
# 12 saatlik pencerenin tamamini bildirmek mesaj yagmuru olurdu. Bu durumda
# sadece son bu kadar dakikada kapananlar bildirilir, geri kalani sessizce
# "bildirilmis" sayilir. Boylece cache olmasa bile sistem calisir; sadece
# ayni kapanis 1-2 kez tekrarlanabilir (cron 15 dakikada bir calisiyor).
_DURUMSUZ_PENCERE_DAKIKA = int(os.getenv("KAPANIS_DURUMSUZ_DAKIKA", "20"))

_SEBEPLER = {
    "DEAL_REASON_TP": "🎯 hedefe ulaştı",
    "DEAL_REASON_SL": "🛑 stop oldu",
    "DEAL_REASON_SO": "⚠️ margin call (stop out)",
    "DEAL_REASON_EXPERT": "bot kapattı",
    "DEAL_REASON_CLIENT": "elle kapatıldı",
    "DEAL_REASON_MOBILE": "elle kapatıldı (mobil)",
    "DEAL_REASON_WEB": "elle kapatıldı (web)",
}


def _bildirilenler(dosya: str) -> set[str]:
    if not os.path.exists(dosya):
        return set()
    try:
        with open(dosya) as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        # Bozuk/okunamayan durum dosyasi yuzunden bot durmamali. En kotu
        # ihtimalle bir kapanis ikinci kez bildirilir.
        return set()


def _kaydet(dosya: str, idler: set[str]) -> None:
    try:
        with open(dosya, "w") as f:
            json.dump(sorted(idler)[-_AZAMI_KAYIT:], f)
    except OSError as exc:
        print(f"  (Kapanis durumu yazilamadi: {exc})")


async def kapanislari_bildir(baglanti, sembol: str) -> int:
    """`sembol` icin son _TARAMA_SAATI saatte kapanan ve daha once
    bildirilmemis pozisyonlari Telegram'a gonderir. Gonderilen mesaj
    sayisini doner.

    Hata durumunda sessizce 0 doner - bildirim gonderememek botun islem
    yapmasini ENGELLEMEMELI."""
    try:
        simdi = dt.datetime.now(dt.timezone.utc)
        ham = await baglanti.get_deals_by_time_range(
            simdi - dt.timedelta(hours=_TARAMA_SAATI), simdi + dt.timedelta(hours=1)
        )
        dealler = ham["deals"] if isinstance(ham, dict) else ham
    except Exception as exc:  # noqa: BLE001 - bildirim akisi botu bozmamali
        print(f"  (Kapanis gecmisi okunamadi: {exc})")
        return 0

    dosya = _dosya_yolu(sembol)
    durum_var = os.path.exists(dosya)
    onceki = _bildirilenler(dosya)
    yeni = set()
    gonderilen = 0
    esik = simdi - dt.timedelta(minutes=_DURUMSUZ_PENCERE_DAKIKA)

    for d in dealler:
        if d.get("entryType") != "DEAL_ENTRY_OUT" or d.get("symbol") != sembol:
            continue
        deal_id = str(d.get("id"))
        if deal_id in onceki:
            continue
        yeni.add(deal_id)

        # Durum dosyasi yoksa eski kapanislari bildirme - sadece kaydet.
        if not durum_var:
            zaman = d.get("time")
            if not isinstance(zaman, dt.datetime) or zaman < esik:
                continue

        # Kapanis deal'i pozisyonun TERSI yondedir: SAT pozisyonu AL ile kapanir.
        yon = "SAT" if d.get("type") == "DEAL_TYPE_BUY" else "AL"
        kar_zarar = d.get("profit", 0.0) + d.get("commission", 0.0) + d.get("swap", 0.0)
        sebep = _SEBEPLER.get(d.get("reason"), d.get("reason", "bilinmiyor"))

        try:
            hesap = await baglanti.get_account_information()
            bakiye = hesap["balance"]
        except Exception:  # noqa: BLE001
            bakiye = None

        telegram_bildirim.pozisyon_kapandi_detayli(
            sembol=sembol, yon=yon, kar_zarar=kar_zarar, sebep=sebep,
            cikis_fiyati=d.get("price"), lot=d.get("volume"),
            kapanis_zamani=d.get("time"), bakiye=bakiye,
        )
        gonderilen += 1
        print(f"  KAPANIS BILDIRILDI: {sembol} {yon} {kar_zarar:+.2f} USD ({sebep})")

    # Yeni kapanis olmasa bile dosyayi olustur - yoksa her calistirma
    # "durumsuz" sayilir ve yukaridaki koruma surekli devrede kalir.
    _kaydet(dosya, onceki | yeni)
    return gonderilen
