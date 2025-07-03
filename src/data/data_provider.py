import streamlit as st
import pandas as pd
import numpy as np
from src.data.yfinance_client import get_stock_data, get_options_data, calculate_greeks_approximation
from src.data.mock_generator import generate_mock_data

class DataProvider:
    """
    Classe per gestire diverse fonti di dati per le opzioni.
    Permette di switchare facilmente tra dati reali e mock.
    """
    
    def __init__(self, data_source='real'):
        """
        Inizializza il provider di dati.
        
        Args:
            data_source (str): 'real' per dati yfinance, 'ib' per Interactive Brokers, 'mock' per dati simulati
        """
        self.data_source = data_source
    
    def get_options_data(self, tickers):
        """
        Ottiene i dati delle opzioni PUT per i ticker specificati.
        
        Args:
            tickers (list): Lista di ticker symbols
            
        Returns:
            dict: Dizionario con dati delle opzioni per ogni ticker
        """
        if self.data_source == 'real':
            return self._get_real_options_data(tickers)
        elif self.data_source == 'ib':
            return self._get_ib_options_data(tickers)
        elif self.data_source == 'mock':
            return self._get_mock_options_data(tickers)
        else:
            raise ValueError(f"Data source non supportata: {self.data_source}")
    
    def _get_real_options_data(self, tickers):
        """Ottiene dati reali da yfinance"""
        options_data = {}
        
        for ticker in tickers:
            try:
                # Ottieni dati del sottostante
                underlying_price, hv_20 = get_stock_data(ticker)
                if underlying_price is None or hv_20 is None:
                    st.warning(f"Impossibile ottenere dati del sottostante per {ticker}")
                    continue
                
                # Ottieni option chain
                options_df = get_options_data(ticker)
                if options_df.empty:
                    st.warning(f"Nessuna opzione PUT trovata per {ticker}")
                    continue
                
                # Converti DataFrame in lista di dizionari
                options_list = []
                for _, row in options_df.iterrows():
                    # Calcola Greeks approssimativi
                    greeks = calculate_greeks_approximation(
                        row['strike'], underlying_price, row['iv'], row['dte']
                    )
                    
                    option_dict = {
                        'strike': row['strike'],
                        'premium': row['premium'],
                        'iv': row['iv'],
                        'delta': greeks['delta'],
                        'gamma': greeks['gamma'],
                        'theta': greeks['theta'],
                        'volume': row['volume'],
                        'open_interest': row['open_interest'],
                        'dte': row['dte'],
                        'bid': row['bid'],
                        'ask': row['ask'],
                        'last': row['last']
                    }
                    options_list.append(option_dict)
                
                options_data[ticker] = {
                    'underlying_price': underlying_price,
                    'hv_20': hv_20,
                    'options': options_list
                }
                
            except Exception as e:
                st.error(f"Errore nel caricamento dati per {ticker}: {e}")
                continue
        
        return options_data
    
    def _get_ib_options_data(self, tickers):
        """Ottiene dati da Interactive Brokers (fallback a yfinance)"""
        try:
            # Import dinamico per evitare errori all'avvio
            import asyncio
            import nest_asyncio
            
            # Configura event loop per Streamlit
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Applica nest_asyncio per permettere nested event loops
            nest_asyncio.apply()
            
            from src.data.ib_client import get_ib_stock_data, get_ib_options_data
            
            options_data = {}
            
            for ticker in tickers:
                try:
                    underlying_price, hv_20 = get_ib_stock_data(ticker)
                    if underlying_price is None or hv_20 is None:
                        st.warning(f"Impossibile ottenere dati IB per {ticker}, uso yfinance")
                        underlying_price, hv_20 = get_stock_data(ticker)
                        if underlying_price is None or hv_20 is None:
                            continue
                    
                    options_df = get_ib_options_data(ticker)
                    if options_df.empty:
                        st.warning(f"Nessuna opzione PUT IB per {ticker}, uso yfinance")
                        options_df = get_options_data(ticker)
                        if options_df.empty:
                            continue
                    
                    options_list = []
                    for _, row in options_df.iterrows():
                        greeks = calculate_greeks_approximation(
                            row['strike'], underlying_price, row['iv'], row['dte']
                        )
                        
                        option_dict = {
                            'strike': row['strike'],
                            'premium': row['premium'],
                            'iv': row['iv'],
                            'delta': greeks['delta'],
                            'gamma': greeks['gamma'],
                            'theta': greeks['theta'],
                            'volume': row['volume'],
                            'open_interest': row['open_interest'],
                            'dte': row['dte'],
                            'bid': row['bid'],
                            'ask': row['ask'],
                            'last': row['last']
                        }
                        options_list.append(option_dict)
                    
                    options_data[ticker] = {
                        'underlying_price': underlying_price,
                        'hv_20': hv_20,
                        'options': options_list
                    }
                    
                except Exception as e:
                    st.error(f"Errore IB per {ticker}: {e}")
                    continue
            
            return options_data
            
        except ImportError as e:
            st.warning(f"Interactive Brokers non disponibile ({e}), uso yfinance")
            return self._get_real_options_data(tickers)
        except Exception as e:
            st.error(f"Errore configurazione IB: {e}")
            return self._get_real_options_data(tickers)
    
    def _get_mock_options_data(self, tickers):
        """Ottiene dati mock"""
        price_map = {}
        for ticker in tickers:
            price, hv_20 = get_stock_data(ticker)
            if price is not None and hv_20 is not None:
                price_map[ticker] = {'price': price, 'hv_20': hv_20}
        
        return generate_mock_data(tickers, price_map)
    
    def set_data_source(self, source):
        """
        Cambia la fonte dati.
        
        Args:
            source (str): 'real', 'ib' o 'mock'
        """
        if source not in ['real', 'ib', 'mock']:
            raise ValueError(f"Data source non supportata: {source}")
        self.data_source = source
