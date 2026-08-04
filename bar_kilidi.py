"""Bar basina TEK giris kilidi.

NEDEN GEREKLI - canli olarak olculdu (2-3 Agustos 2026, AUDNZD):

Backtest bar bar ilerler; bir barda en fazla BIR giris yapar. Canli bot ise
15 dakikada bir calisiyor, yani ayni saatlik barin icinde 4 kez giris
firsati buluyor. Stop yedikten sonra sinyal hala ayni yonde oldugu icin
dakikalar sonra yeniden giriyor:

    21:17 giris -> 21:24 stop -> 21:32 YENIDEN GIRIS   (ikisi de 21:00 bari)
    22:02 giris -> 22:20 stop -> 22:32 YENIDEN GIRIS   (ikisi de 22:00 bari)

Alti saatte dort islem, ucu stop, net -85.38 USD. Dordunun de sinyali 6/6
oyla saglamdi - sorun sinyalde degil, ayni bardan defalarca girilmesindeydi.

NASIL CALISIR - kasitli olarak DURUM DOSYASI KULLANMAZ:
Brokerin kendi islem gecmisine bakar: "bu barin baslangicindan beri bu
sembolde giris deal'i var mi?" GitHub Actions'ta her calistirma temiz bir
makinede basladigi icin yerel durum dosyasi tasinmaz; brokerin gecmisi ise
her zaman dogru kaynaktir.

SADECE demo hesap icindir.
"""
from __future__ import annotations

import datetime as dt
import json
import os

_HESAP_ETIKETI = os.getenv("HESAP_ETIKETI", "")


def _dosya_yolu(sembol: str) -> str:
    return os.path.join(os.path.dirname(__file__),
                        f"son_giris_bari_{sembol}{_HESAP_ETIKETI}.json")


def _kayitli_bar(sembol: str) -> str | None:
    yol = _dosya_yolu(sembol)
    if not os.path.exists(yol):
        return None
    try:
        with open(yol) as f:
            return json.load(f).get("bar")
    except (json.JSONDecodeError, OSError):
        return None


def girisi_kaydet(sembol: str, bar_baslangici) -> None:
    """Basarili bir giristen SONRA cagrilir - hangi barda girildigini yazar."""
    try:
        with open(_dosya_yolu(sembol), "w") as f:
            json.dump({"bar": bar_baslangici.isoformat()}, f)
    except OSError as exc:
        print(f"  (Giris bari yazilamadi: {exc} - kilit sadece broker gecmisine dayanacak)")


async def bu_barda_giris_var_mi(baglanti, sembol: str, bar_baslangici) -> bool:
    """`bar_baslangici` barinda `sembol` icin zaten giris yapilmis mi?

    IKI KATMANLI - biri digerinin yedegi:

    1) YEREL KAYIT (kesin, API'ye bagli degil): bir onceki calistirma bu
       barda giris yaptiysa dosyada yazar. Deterministik ve hizli.
    2) BROKER GECMISI: yerel kayit yoksa (cache kaybi, ilk calistirma)
       islem gecmisine bakilir.

    NEDEN IKI KATMAN - olculdu (03.08.2026, XAGUSD): tek basina broker
    gecmisi kontrolu bir kez devreye girmedi ve ayni 13:00 barinda iki
    giris yapildi (13:01:57 ve 13:37:13). Fonksiyon geriye donuk test
    edildiginde o pencereyi DOGRU okuyordu, yani mantik hatasi degil -
    muhtemelen o an API cagrisi hata verip asagidaki fail-open dalina
    dustu. Yerel kayit bu duruma bagisik.

    HATA DURUMU: broker gecmisi okunamazsa False doner (kilit uygulanmaz).
    Bildirim/kontrol yapamamak yuzunden botun tamamen durmasi daha kotu
    olurdu - ama artik yerel kayit birinci savunma hatti oldugu icin bu
    dalin tetiklenmesi sonucu degistirmiyor."""
    hedef = bar_baslangici.isoformat()

    # 1) yerel kayit
    if _kayitli_bar(sembol) == hedef:
        print(f"  (bar kilidi: {sembol} icin {bar_baslangici.strftime('%H:%M')} barinda "
              f"giris yapildigi YEREL KAYITTA var)")
        return True

    # 2) broker gecmisi
    try:
        simdi = dt.datetime.now(dt.timezone.utc)
        ham = await baglanti.get_deals_by_time_range(bar_baslangici, simdi + dt.timedelta(minutes=1))
        dealler = ham["deals"] if isinstance(ham, dict) else ham
    except Exception as exc:  # noqa: BLE001
        print(f"  UYARI: bar kilidi broker gecmisini okuyamadi ({type(exc).__name__}: {exc}) - "
              f"yerel kayitta da bulunmadigi icin girise izin veriliyor.")
        return False

    for d in dealler:
        if d.get("symbol") == sembol and d.get("entryType") == "DEAL_ENTRY_IN":
            print(f"  (bar kilidi: {sembol} icin {bar_baslangici.strftime('%H:%M')} barinda "
                  f"giris BROKER GECMISINDE bulundu)")
            return True
    return False


def acik_bar_baslangici(ham_df) -> dt.datetime:
    """Su an icinde bulunulan barin baslangic zamani.

    MetaApi ham veride son bar olarak ICINDE BULUNULAN mumu dondurur, yani
    onun indeksi dogrudan acik barin baslangicidir. Piyasa kapaliysa son
    kapanmis bar doner - o durumda da dogru davranis, cunku o bardan sonra
    yeni giris zaten olmamali."""
    return ham_df.index[-1].to_pydatetime()
