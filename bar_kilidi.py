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


async def bu_barda_giris_var_mi(baglanti, sembol: str, bar_baslangici) -> bool:
    """`bar_baslangici`'ndan bu yana `sembol` icin acilis (giris) islemi
    yapilmis mi?

    Hata durumunda False doner - yani kilit uygulanmaz. Kilit, isleyisi
    IYILESTIRMEK icin var; broker gecmisi okunamadi diye botun tamamen
    durmasi daha kotu olurdu.
    """
    try:
        simdi = dt.datetime.now(dt.timezone.utc)
        ham = await baglanti.get_deals_by_time_range(bar_baslangici, simdi + dt.timedelta(minutes=1))
        dealler = ham["deals"] if isinstance(ham, dict) else ham
    except Exception as exc:  # noqa: BLE001
        print(f"  (Bar kilidi kontrol edilemedi: {exc} - kilit uygulanmiyor)")
        return False

    for d in dealler:
        if d.get("symbol") == sembol and d.get("entryType") == "DEAL_ENTRY_IN":
            return True
    return False


def acik_bar_baslangici(ham_df) -> dt.datetime:
    """Su an icinde bulunulan barin baslangic zamani.

    MetaApi ham veride son bar olarak ICINDE BULUNULAN mumu dondurur, yani
    onun indeksi dogrudan acik barin baslangicidir. Piyasa kapaliysa son
    kapanmis bar doner - o durumda da dogru davranis, cunku o bardan sonra
    yeni giris zaten olmamali."""
    return ham_df.index[-1].to_pydatetime()
