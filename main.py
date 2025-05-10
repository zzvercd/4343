import os
import pandas as pd
from binance.client import Client
from ta.trend import EMAIndicator, MACD, PSARIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import requests
import time

# Настройки
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "OPUSDT", "LINKUSDT"]
INTERVAL = '4h'
LIMIT = 150

# Переменные окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")

client = Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET)

def fetch_klines(symbol):
    klines = client.get_klines(symbol=symbol, interval=INTERVAL, limit=LIMIT)
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
    if len(df) < 30:
        return False  # Недостаточно данных

    df = df.copy()
    ema9 = EMAIndicator(df['close'], window=9).ema_indicator()
    ema21 = EMAIndicator(df['close'], window=21).ema_indicator()
    rsi = RSIIndicator(df['close'], window=14).rsi()
    bb = BollingerBands(df['close'], window=20, window_dev=2)
    lower_band = bb.bollinger_lband()
    macd = MACD(df['close'])
    macd_line = macd.macd()
    signal_line = macd.macd_signal()
    volume = df['volume']
    psar = PSARIndicator(df['high'], df['low'], df['close'])
    psar_values = psar.psar()

    i = -1  # Последняя свеча

    conditions = [
        ema9[i - 1] > ema21[i - 1] and ema9[i] < ema21[i],  # EMA пересечение
        30 < rsi[i] < 70,                                   # RSI нормальный
        df['close'][i] <= lower_band[i] * 1.03,             # Bollinger нижняя полоса
        macd_line[i - 1] < signal_line[i - 1] and macd_line[i] > signal_line[i],  # MACD пересечение
        volume[i] > volume[i - 1],                          # Рост объёма
        psar_values[i] < df['close'][i],                    # Parabolic SAR
    ]

    return all(conditions)

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials not set.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Failed to send message: {e}")

def main():
    for symbol in SYMBOLS:
        try:
            df = fetch_klines(symbol)
            if analyze(df):
                send_telegram_message(f"📈 BUY SIGNAL for {symbol} (4H)")
            else:
                print(f"No signal for {symbol}")
        except Exception as e:
            print(f"Error with {symbol}: {e}")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(60 * 5)  # Проверять каждый час
