import pandas as pd
import numpy as np
import streamlit as st
import asyncio
import nest_asyncio
from datetime import datetime, timedelta

# Configura event loop per Streamlit
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Applica nest_asyncio per permettere nested event loops
nest_asyncio.apply()

from ib_insync import IB, Stock, Option

class IBClient:
    def __init__(self):
        self.ib = IB()
        self.connected = False
    
    def connect(self, host='127.0.0.1', port=7497, clientId=1):
        """Connette a Interactive Brokers TWS/Gateway"""
        try:
            self.ib.connect(host, port, clientId)
            self.connected = True
            return True
        except Exception as e:
            st.error(f"Errore connessione IB: {e}")
            return False
    
    def disconnect(self):
        """Disconnette da IB"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False

@st.cache_data(ttl=3600)
def get_ib_stock_data(ticker):
    """Ottiene dati stock da Interactive Brokers"""
    try:
        ib_client = IBClient()
        if not ib_client.connect():
            return None, None
        
        # Crea contratto stock
        stock = Stock(ticker, 'SMART', 'USD')
        ib_client.ib.qualifyContracts(stock)
        
        # Ottieni prezzo corrente
        ticker_data = ib_client.ib.reqMktData(stock, '', False, False)
        ib_client.ib.sleep(2)  # Attendi dati
        
        if ticker_data.last:
            current_price = ticker_data.last
        else:
            current_price = (ticker_data.bid + ticker_data.ask) / 2
        
        # Ottieni dati storici per HV
        bars = ib_client.ib.reqHistoricalData(
            stock, endDateTime='', durationStr='1 Y',
            barSizeSetting='1 day', whatToShow='MIDPOINT',
            useRTH=True, formatDate=1
        )
        
        if bars:
            df = pd.DataFrame(bars)
            log_returns = np.log(df['close'] / df['close'].shift(1))
            hv_20 = log_returns.rolling(window=20).std().iloc[-1] * np.sqrt(252)
        else:
            hv_20 = None
        
        ib_client.disconnect()
        return current_price, hv_20
        
    except Exception as e:
        st.error(f"Errore IB stock data per {ticker}: {e}")
        return None, None

@st.cache_data(ttl=1800)
def get_ib_options_data(ticker):
    """Ottiene option chain da Interactive Brokers"""
    try:
        ib_client = IBClient()
        if not ib_client.connect():
            return pd.DataFrame()
        
        # Crea contratto stock
        stock = Stock(ticker, 'SMART', 'USD')
        ib_client.ib.qualifyContracts(stock)
        
        # Ottieni chain opzioni
        chains = ib_client.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
        
        all_puts = []
        
        for chain in chains[:3]:  # Primi 3 exchange
            for expiry in chain.expirations[:6]:  # Prime 6 scadenze
                try:
                    exp_date = datetime.strptime(expiry, '%Y%m%d')
                    dte = (exp_date - datetime.now()).days
                    
                    if dte < 7:  # Skip scadenze troppo vicine
                        continue
                    
                    # Crea contratti PUT
                    for strike in chain.strikes[::5]:  # Ogni 5° strike
                        put_contract = Option(ticker, expiry, strike, 'P', 'SMART')
                        ib_client.ib.qualifyContracts(put_contract)
                        
                        # Richiedi dati market
                        ticker_data = ib_client.ib.reqMktData(put_contract, '', False, False)
                        ib_client.ib.sleep(0.5)
                        
                        if ticker_data.bid and ticker_data.ask and ticker_data.bid > 0:
                            premium = (ticker_data.bid + ticker_data.ask) / 2
                            iv = ticker_data.impliedVolatility if ticker_data.impliedVolatility else 0.2
                            
                            put_data = {
                                'strike': strike,
                                'premium': premium,
                                'iv': iv,
                                'bid': ticker_data.bid,
                                'ask': ticker_data.ask,
                                'last': ticker_data.last if ticker_data.last else premium,
                                'volume': ticker_data.volume if ticker_data.volume else 0,
                                'open_interest': 0,  # Non disponibile real-time
                                'dte': dte
                            }
                            all_puts.append(put_data)
                            
                except Exception as e:
                    continue
        
        ib_client.disconnect()
        return pd.DataFrame(all_puts) if all_puts else pd.DataFrame()
        
    except Exception as e:
        st.error(f"Errore IB options data per {ticker}: {e}")
        return pd.DataFrame()
