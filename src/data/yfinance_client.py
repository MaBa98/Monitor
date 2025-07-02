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

@st.cache_data(ttl=1800) # Cache per 30 minuti
def get_options_data(ticker):
    """
    Ottiene le option chain reali da yfinance per PUT options.
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Ottieni le date di scadenza disponibili
        expiration_dates = stock.options
        if not expiration_dates:
            return []
        
        all_puts = []
        
        for exp_date in expiration_dates[:6]:  # Limita alle prime 6 scadenze
            try:
                option_chain = stock.option_chain(exp_date)
                puts = option_chain.puts
                
                if puts.empty:
                    continue
                
                # Calcola DTE
                exp_datetime = pd.to_datetime(exp_date)
                today = pd.Timestamp.now()
                dte = (exp_datetime - today).days
                
                # Filtra solo PUT con volume > 0 e IV valida
                puts = puts[
                    (puts['volume'] > 0) & 
                    (puts['impliedVolatility'] > 0) &
                    (puts['bid'] > 0) &
                    (puts['ask'] > 0)
                ].copy()
                
                if puts.empty:
                    continue
                
                # Aggiungi colonne calcolate
                puts['dte'] = dte
                puts['premium'] = (puts['bid'] + puts['ask']) / 2
                puts['iv'] = puts['impliedVolatility']
                puts['open_interest'] = puts['openInterest']
                
                # Rinomina colonne per compatibilità
                puts = puts.rename(columns={
                    'strike': 'strike',
                    'lastPrice': 'last',
                    'volume': 'volume'
                })
                
                # Seleziona solo le colonne necessarie
                puts_filtered = puts[[
                    'strike', 'premium', 'iv', 'bid', 'ask', 'last',
                    'volume', 'open_interest', 'dte'
                ]].copy()
                
                all_puts.append(puts_filtered)
                
            except Exception as e:
                st.warning(f"Errore nel caricamento opzioni per {ticker} scadenza {exp_date}: {e}")
                continue
        
        if all_puts:
            return pd.concat(all_puts, ignore_index=True)
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Errore nel caricamento option chain per {ticker}: {e}")
        return pd.DataFrame()

def calculate_greeks_approximation(strike, underlying_price, iv, dte, option_type='put'):
    """
    Calcola i Greeks in modo approssimativo per le opzioni.
    """
    try:
        # Parametri per calcolo semplificato
        time_to_expiry = dte / 365.0
        moneyness = strike / underlying_price
        
        if option_type == 'put':
            # Delta approssimativo per PUT
            if strike < underlying_price:  # OTM
                delta = -0.05 - (underlying_price - strike) / underlying_price * 0.4
            else:  # ITM
                delta = -0.5 - (strike - underlying_price) / underlying_price * 0.3
            
            delta = max(-0.95, min(-0.05, delta))
        
        # Gamma approssimativo
        gamma = 0.01 / (underlying_price * time_to_expiry**0.5) if time_to_expiry > 0 else 0
        
        # Theta approssimativo (sempre negativo per long options)
        theta = -(strike * 0.01 * iv) / (365 * 2) if time_to_expiry > 0 else 0
        
        return {
            'delta': round(delta, 3),
            'gamma': round(gamma, 4),
            'theta': round(theta, 3)
        }
        
    except Exception:
        return {'delta': -0.3, 'gamma': 0.01, 'theta': -0.05}
