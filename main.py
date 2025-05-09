import os
import pandas as pd
from binance.client import Client
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator
from ta.trend import PSARIndicator
import requests
import time

# Настройки
SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_4H
LIMIT = 150

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Ваш токен бота
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Ваш chat_id

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")

client = Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET)

def fetch_klines():
    klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=LIMIT)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['open'] = df['open'].astype(float)
    return df

def analyze(df):
    df = df.copy()

    # EMA
    ema9 = EMAIndicator(df['close'], window=9).ema_indicator()
    ema21 = EMAIndicator(df['close'], window=21).ema_indicator()

    # RSI
    rsi = RSIIndicator(df['close'], window=14).rsi()

    # Bollinger Bands
    bb = BollingerBands(df['close'], window=20, window_dev=2)
    lower_band = bb.bollinger_lband()

    # MACD
    macd = MACD(df['close'])
    macd_line = macd.macd()
    signal_line = macd.macd_signal()

    # Volume (просто проверка роста)
    volume = df['volume']

    # Parabolic SAR
    psar = PSARIndicator(df['high'], df['low'], df['close'])
    psar_values = psar.psar()

    last = -1

    conditions = [
        ema9[last - 1] > ema21[last - 1] and ema9[last] < ema21[last],  # пересечение
        30 < rsi[last] < 70,
        df['close'][last] <= lower_band[last] * 1.03,  # касается нижней границы
        macd_line[last - 1] < signal_line[last - 1] and macd_line[last] > signal_line[last],
        volume[last] > volume[last - 1],
        psar_values[last] < df['close'][last],
    ]

    return all(conditions)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    requests.post(url, data=payload)

def main():
    try:
        df = fetch_klines()
        if analyze(df):
            send_telegram_message(f"📈 BUY SIGNAL for {SYMBOL} (4H)")
        else:
            print("No signal.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(60 * 60)  # Проверка раз в час
