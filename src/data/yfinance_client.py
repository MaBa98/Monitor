import yfinance as yf
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

@st.cache_data(ttl=3600) # Cache per 1 ora
def get_stock_data(ticker):
    """
    Ottiene il prezzo corrente 'adjusted' e la volatilità storica a 20 giorni.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y", auto_adjust=True) # Dati adjusted
        if hist.empty:
            return None, None
        
        # Prezzo corrente
        current_price = hist['Close'].iloc[-1]
        
        # Volatilità storica a 20 giorni annualizzata
        log_returns = np.log(hist['Close'] / hist['Close'].shift(1))
        hv_20 = log_returns.rolling(window=20).std().iloc[-1] * np.sqrt(252)
        
        return current_price, hv_20
    except Exception as e:
        st.error(f"Errore nel caricamento dati per {ticker}: {e}")
        return None, None
