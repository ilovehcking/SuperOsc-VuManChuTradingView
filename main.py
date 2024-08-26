import requests
import math
import pandas as pd
import pandas_ta as ta
import time
from termcolor import colored
import threading
from datetime import datetime

def round_up_to_one_decimal_place(number):
    return math.ceil(number * 10) / 10.0



KLINE_API_URL = "https://contract.mexc.com/api/v1/contract/kline/BTC_USDT"

def get_kline_data(symbol="BTC_USDT", interval="Min1", limit=50):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    response = requests.get(KLINE_API_URL, params=params)
    data = response.json()
    
    if not data['success']:
        raise Exception("API call failed")

    df = pd.DataFrame({
        'timestamp': data['data']['time'],
        'open': data['data']['open'],
        'high': data['data']['high'],
        'low': data['data']['low'],
        'close': data['data']['close'],
        'volume': data['data']['vol']
    })
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    return df


def vumanchu_indicator(df):
    # Variables based on Cipher B settings
    n1 = 9  # channel length
    n2 = 12  # average length
    ma_length = 3  # Moving average length for WT2

    # WaveTrend calculation
    df['ap'] = (df['high'] + df['low'] + df['close']) / 3  # WT MA source
    df['esa'] = ta.ema(df['ap'], n1)  # EMA of the MA source by the channel length
    df['d'] = ta.ema(abs(df['ap'] - df['esa']), n1)
    df['ci'] = (df['ap'] - df['esa']) / (0.015 * df['d'])
    df['wt1'] = ta.ema(df['ci'], n2)
    df['wt2'] = ta.sma(df['wt1'], ma_length)

    # Calculate crossing points for buy/sell signals
    df["green_wt"] = (df['wt1'] > df['wt2']) & (df['wt1'].shift(1) <= df['wt2'].shift(1))
    df["red_wt"] = (df['wt1'] < df['wt2']) & (df['wt1'].shift(1) >= df['wt2'].shift(1))

    return df


global superTrendOsc
global vumanChu
global wt1Value
global wt2Value

wt1Value = 0
wt2Value = 0
superTrendOsc = 0
vumanChu = 0



def schreibe_in_datei(dateiname: str, text: str):
    aktuelle_zeit = datetime.datetime.now().strftime("%H:%M:%S")
    text_mit_zeit = f"{aktuelle_zeit} - {text}\n"
    with open(dateiname, "a") as datei:
        datei.write(text_mit_zeit)




def checkIfGood():
    if superTrendOsc > 0 and "green" in vumanChu and wt1Value < -60 and wt2Value < -60:
        print("good time to buy")
        schreibe_in_datei("log.txt", "good time to buy")
    if superTrendOsc < 0 and "red" in vumanChu and wt1Value > 60 and wt2Value > 60:
        print("good time to sell")
        schreibe_in_datei("log.txt", "good time to sell")



def wait_for_full_minute():
    while True:
        now = datetime.now()
        if now.second == 0:
            checkIfGood()
            break
        time.sleep(1)



thread = threading.Thread(target=wait_for_full_minute)
thread.start()


while True:
   
    upperArray = [0]
    lowerArray = [0]
    trendArray = [0]

    oscArray = [0]

    vuManChuArray = [0]



    df = get_kline_data(symbol="BTC_USDT", interval="Min1", limit=50)
    atr = df.ta.atr(length=10)

    for i in range(1, len(atr)):  
        newValue = atr[i] * 8.0
        newValue = round(newValue, 1)
        hl2 = (df.high[i] + df.low[i]) / 2
        hl2 = round_up_to_one_decimal_place(hl2)
        up = hl2 + newValue
        up = round(up, 1)
        dn = hl2 - newValue
        dn = round(dn, 1)
        upper = min(up, upperArray[i - 1]) if df.close[i - 1] < upperArray[i - 1] else up
        lower = max(dn, lowerArray[i - 1]) if df.close[i - 1] > lowerArray[i - 1] else dn
        upperArray.append(upper)
        lowerArray.append(lower)

        trend = 1 if df.close[i] > upperArray[i - 1] else (0 if df.close[i] < lowerArray[i - 1] else trendArray[i - 1])
        trendArray.append(trend)

        Spt = trend * lower + (1 - trend) * upper

        osc = max(min((df.close[i] - Spt) / (upper - lower), 1), -1)

        oscArray.append(osc * 100)


    
    try:
        df = vumanchu_indicator(df)
        
        wt1 = df['wt1'].iloc[-1]
        wt2 = df['wt2'].iloc[-1]
        green_signal = df['green_wt'].iloc[-1]
        red_signal = df['red_wt'].iloc[-1]

        if pd.notnull(wt1) and pd.notnull(wt2):  # Check if wt1 and wt2 are not None
            if green_signal:
                line = f"WT1: {wt1:.2f}, WT2: {wt2:.2f} " + colored("●", "green")
            elif red_signal:
                line = f"WT1: {wt1:.2f}, WT2: {wt2:.2f} " + colored("●", "red")
            else:
                line = f"WT1: {wt1:.2f}, WT2: {wt2:.2f}"
        else:
            line = "WT1 or WT2 not available"

        vuManChuArray.append(line)



    except KeyboardInterrupt:
        print("Programm beendet.")
        break
    except Exception as e:
        print(f"Fehler: {e}")




    print("superTrend Oscillator: " + str(oscArray[-1])) 
    print("vuManChu: " + str(vuManChuArray[-1]))
    print(" ")
    wt1Value = wt1
    wt2Value = wt2
    vumanChu = vuManChuArray[-1]
    superTrendOsc = oscArray[-1]
    time.sleep(0.5)