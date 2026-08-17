"""BACKTEST VERISI CEKME - delik doldurmali, kalici klasore.

Scratchpad temizlenince veriler siliniyordu; artik repo icindeki veri/
klasorune yaziliyor (.gitignore'da).

Kullanim:  python veri_cek.py XAUUSD XAGUSD AUDNZD
"""
import asyncio, sys, pathlib
import mt5_veri

KLASOR = pathlib.Path(__file__).parent / "veri"


async def cek(sembol: str, adet: int = 60000):
    KLASOR.mkdir(exist_ok=True)
    d = await mt5_veri.cok_barli_getir(sembol, "1h", adet, delik_doldur=True)
    yol = KLASOR / f"{sembol}_tam.pkl"
    d.to_pickle(yol)
    f = d.index.to_series().diff().dt.total_seconds() / 3600
    print(f"{sembol}: {len(d)} bar  {d.index[0].date()} - {d.index[-1].date()}  "
          f"({(d.index[-1]-d.index[0]).days/365.25:.1f} yil)", flush=True)
    print(f"   1 saatlik adim %{(f==1).mean()*100:.1f} | 60s+ delik {int((f>=60).sum())} | "
          f"en buyuk {f.max():.0f}s -> {yol.name}", flush=True)


async def main():
    for s in (sys.argv[1:] or ["XAUUSD", "XAGUSD", "AUDNZD"]):
        await cek(s)

if __name__ == "__main__":
    asyncio.run(main())
