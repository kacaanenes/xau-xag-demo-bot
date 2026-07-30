"""MetaApi.cloud uzerinden demo MT5 hesabini ekler/bulur, deploy eder ve
baglantiyi dogrulamak icin hesap bilgisini yazdirir. Sadece kurulum/dogrulama
amacli, tek seferlik calistirilir.
"""
import asyncio

from metaapi_cloud_sdk import MetaApi

import config

_HESAP_ADI = "XAU_XAG Demo"


async def main() -> None:
    api = MetaApi(config.METAAPI_TOKEN)

    hesaplar = await api.metatrader_account_api.get_accounts_with_infinite_scroll_pagination()
    hesap = next((h for h in hesaplar if h.login == config.MT5_LOGIN), None)

    if hesap is None:
        print("Hesap MetaApi'de bulunamadi, olusturuluyor...")
        hesap = await api.metatrader_account_api.create_account(
            account={
                "name": _HESAP_ADI,
                "type": "cloud-g2",
                "login": config.MT5_LOGIN,
                "password": config.MT5_PASSWORD,
                "server": config.MT5_SERVER,
                "platform": "mt5",
                "magic": 123456,
            }
        )
    else:
        print(f"Hesap zaten var: {hesap.id}")

    if hesap.state != "DEPLOYED":
        print("Hesap deploy ediliyor...")
        await hesap.deploy()

    print("Baglanti bekleniyor...")
    await hesap.wait_connected()

    baglanti = hesap.get_rpc_connection()
    await baglanti.connect()
    await baglanti.wait_synchronized()

    bilgi = await baglanti.get_account_information()
    print("\nHesap bilgisi:")
    print(f"  Bakiye: {bilgi['balance']} {bilgi['currency']}")
    print(f"  Ozsermaye: {bilgi['equity']} {bilgi['currency']}")
    print(f"  Sunucu: {bilgi['server']}")
    print(f"  Broker: {bilgi.get('broker', '-')}")


if __name__ == "__main__":
    asyncio.run(main())
