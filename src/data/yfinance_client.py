import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import time

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealOptionsDataClient:
    """
    Client unificato per ottenere dati reali di option chain da multiple fonti.
    Supporta Yahoo Finance (gratuito) e Alpha Vantage (con API key).
    """
    
    def __init__(self, alpha_vantage_key: Optional[str] = None):
        self.alpha_vantage_key = alpha_vantage_key
        self.session = requests.Session()
        
    def get_stock_data(self, ticker: str) -> Tuple[float, float]:
        """
        Ottiene prezzo corrente e volatilità storica a 20 giorni.
        
        Args:
            ticker: Symbol del titolo (es. 'AAPL')
            
        Returns:
            Tuple[price, hv_20]: Prezzo corrente e volatilità storica 20gg
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Prezzo corrente
            info = stock.info
            current_price = info.get('currentPrice') or info.get('previousClose')
            
            # Volatilità storica 20 giorni
            hist = stock.history(period='1mo', interval='1d')
            if len(hist) >= 20:
                returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna()
                hv_20 = returns.std() * np.sqrt(252)  # Annualizzata
            else:
                hv_20 = 0.25  # Default se non ci sono abbastanza dati
                
            logger.info(f"✅ {ticker}: Prezzo=${current_price:.2f}, HV20={hv_20:.2%}")
            return current_price, hv_20
            
        except Exception as e:
            logger.error(f"❌ Errore nel recupero dati per {ticker}: {e}")
            return None, None

    def get_options_chain_yahoo(self, ticker: str, max_dte: int = 60) -> Dict:
        """
        Ottiene option chain completa da Yahoo Finance.
        
        Args:
            ticker: Symbol del titolo
            max_dte: Massimo Days To Expiration da considerare
            
        Returns:
            Dict con dati opzioni organizzati
        """
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            
            if not expirations:
                logger.warning(f"⚠️ Nessuna opzione trovata per {ticker}")
                return {}
            
            all_options = []
            current_date = datetime.now().date()
            
            for exp_date_str in expirations:
                exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                dte = (exp_date - current_date).days
                
                if dte <= max_dte and dte > 0:
                    try:
                        chain = stock.option_chain(exp_date_str)
                        
                        # Processa PUT options
                        puts = chain.puts
                        for _, row in puts.iterrows():
                            option_data = {
                                'type': 'PUT',
                                'strike': row['strike'],
                                'expiration': exp_date_str,
                                'dte': dte,
                                'last_price': row.get('lastPrice', 0),
                                'bid': row.get('bid', 0),
                                'ask': row.get('ask', 0),
                                'volume': row.get('volume', 0),
                                'open_interest': row.get('openInterest', 0),
                                'implied_volatility': row.get('impliedVolatility', 0),
                                'delta': -abs(row.get('delta', 0)),  # PUT delta è negativo
                                'gamma': row.get('gamma', 0),
                                'theta': row.get('theta', 0),
                                'vega': row.get('vega', 0),
                                'rho': row.get('rho', 0)
                            }
                            
                            # Calcola mid price se bid/ask disponibili
                            if option_data['bid'] > 0 and option_data['ask'] > 0:
                                option_data['mid_price'] = (option_data['bid'] + option_data['ask']) / 2
                            else:
                                option_data['mid_price'] = option_data['last_price']
                            
                            all_options.append(option_data)
                            
                        time.sleep(0.1)  # Rate limiting
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Errore per scadenza {exp_date_str}: {e}")
                        continue
            
            logger.info(f"✅ {ticker}: Recuperate {len(all_options)} opzioni PUT")
            return {'options': all_options}
            
        except Exception as e:
            logger.error(f"❌ Errore nel recupero option chain per {ticker}: {e}")
            return {}

    def get_options_chain_alpha_vantage(self, ticker: str) -> Dict:
        """
        Ottiene option chain da Alpha Vantage (richiede API key).
        
        Args:
            ticker: Symbol del titolo
            
        Returns:
            Dict con dati opzioni
        """
        if not self.alpha_vantage_key:
            logger.warning("⚠️ API key Alpha Vantage non configurata")
            return {}
            
        try:
            url = 'https://www.alphavantage.co/query'
            params = {
                'function': 'OPTION_CHAIN',
                'symbol': ticker,
                'apikey': self.alpha_vantage_key
            }
            
            response = self.session.get(url, params=params)
            data = response.json()
            
            if 'data' not in data:
                logger.warning(f"⚠️ Dati non disponibili per {ticker} su Alpha Vantage")
                return {}
            
            # Processa i dati Alpha Vantage
            options_data = []
            for contract in data['data']:
                if contract['type'] == 'put':
                    option_data = {
                        'type': 'PUT',
                        'strike': float(contract['strike']),
                        'expiration': contract['expiration'],
                        'dte': self._calculate_dte(contract['expiration']),
                        'last_price': float(contract.get('last', 0)),
                        'bid': float(contract.get('bid', 0)),
                        'ask': float(contract.get('ask', 0)),
                        'volume': int(contract.get('volume', 0)),
                        'open_interest': int(contract.get('open_interest', 0)),
                        'implied_volatility': float(contract.get('implied_volatility', 0)),
                        'delta': float(contract.get('delta', 0)),
                        'gamma': float(contract.get('gamma', 0)),
                        'theta': float(contract.get('theta', 0)),
                        'vega': float(contract.get('vega', 0)),
                        'rho': float(contract.get('rho', 0))
                    }
                    
                    option_data['mid_price'] = (option_data['bid'] + option_data['ask']) / 2
                    options_data.append(option_data)
            
            logger.info(f"✅ {ticker}: Recuperate {len(options_data)} opzioni da Alpha Vantage")
            return {'options': options_data}
            
        except Exception as e:
            logger.error(f"❌ Errore Alpha Vantage per {ticker}: {e}")
            return {}

    def get_options_data(self, ticker: str, source: str = 'yahoo') -> Dict:
        """
        Metodo principale per ottenere dati opzioni.
        
        Args:
            ticker: Symbol del titolo
            source: Fonte dati ('yahoo' o 'alphavantage')
            
        Returns:
            Dict con option chain e dati sottostante
        """
        # Ottieni dati sottostante
        underlying_price, hv_20 = self.get_stock_data(ticker)
        
        if underlying_price is None:
            return {}
        
        # Ottieni option chain
        if source == 'yahoo':
            options_data = self.get_options_chain_yahoo(ticker)
        elif source == 'alphavantage':
            options_data = self.get_options_chain_alpha_vantage(ticker)
        else:
            logger.error(f"❌ Fonte non supportata: {source}")
            return {}
        
        if not options_data:
            return {}
        
        # Combina tutti i dati
        result = {
            'underlying_price': underlying_price,
            'hv_20': hv_20,
            'options': options_data['options'],
            'data_source': source,
            'timestamp': datetime.now().isoformat()
        }
        
        return result

    def _calculate_dte(self, expiration_str: str) -> int:
        """Calcola Days To Expiration da stringa data."""
        try:
            exp_date = datetime.strptime(expiration_str, '%Y-%m-%d').date()
            return (exp_date - datetime.now().date()).days
        except:
            return 0

    def get_multiple_tickers(self, tickers: List[str], source: str = 'yahoo') -> Dict:
        """
        Ottiene dati per multiple tickers con rate limiting.
        
        Args:
            tickers: Lista di symbols
            source: Fonte dati
            
        Returns:
            Dict con dati per ogni ticker
        """
        results = {}
        
        for i, ticker in enumerate(tickers):
            logger.info(f"📊 Processando {ticker} ({i+1}/{len(tickers)})")
            
            data = self.get_options_data(ticker, source)
            if data:
                results[ticker] = data
            
            # Rate limiting per evitare ban
            if i < len(tickers) - 1:
                time.sleep(1 if source == 'yahoo' else 12)  # Alpha Vantage: 5 req/min
                
        return results


# --- FUNZIONI DI COMPATIBILITÀ CON IL CODICE ESISTENTE ---

def get_stock_data(ticker: str) -> Tuple[float, float]:
    """
    Funzione di compatibilità con il codice esistente.
    """
    client = RealOptionsDataClient()
    return client.get_stock_data(ticker)

def get_real_options_data(tickers: List[str], source: str = 'yahoo', alpha_vantage_key: str = None) -> Dict:
    """
    Funzione principale per ottenere dati reali da usare nella tua app.
    
    Args:
        tickers: Lista di symbols
        source: 'yahoo' (gratuito) o 'alphavantage' (API key richiesta)
        alpha_vantage_key: API key per Alpha Vantage (opzionale)
        
    Returns:
        Dict con structure compatibile con generate_mock_data()
    """
    client = RealOptionsDataClient(alpha_vantage_key)
    
    logger.info(f"🚀 Inizio recupero dati reali per {len(tickers)} tickers da {source.upper()}")
    
    raw_data = client.get_multiple_tickers(tickers, source)
    
    # Trasforma i dati nel formato atteso dalla tua app
    processed_data = {}
    
    for ticker, data in raw_data.items():
        if not data or not data.get('options'):
            logger.warning(f"⚠️ Nessun dato opzione per {ticker}")
            continue
            
        # Filtra solo PUT options valide con IV > 0
        valid_options = []
        for opt in data['options']:
            if (opt['implied_volatility'] > 0 and 
                opt['mid_price'] > 0 and 
                opt['dte'] > 0):
                
                # Standardizza i nomi dei campi per compatibilità
                processed_opt = {
                    'strike': opt['strike'],
                    'expiration': opt['expiration'],
                    'DTE': opt['dte'],
                    'premium': opt['mid_price'],
                    'bid': opt['bid'],
                    'ask': opt['ask'],
                    'volume': opt['volume'],
                    'open_interest': opt['open_interest'],
                    'IV': opt['implied_volatility'],
                    'delta': opt['delta'],
                    'gamma': opt['gamma'],
                    'theta': opt['theta'],
                    'vega': opt['vega'],
                    'rho': opt['rho']
                }
                valid_options.append(processed_opt)
        
        if valid_options:
            processed_data[ticker] = {
                'underlying_price': data['underlying_price'],
                'hv_20': data['hv_20'],
                'options': valid_options,
                'data_source': data['data_source'],
                'timestamp': data['timestamp']
            }
            
            logger.info(f"✅ {ticker}: {len(valid_options)} opzioni valide processate")
    
    logger.info(f"🎉 Completato! {len(processed_data)} tickers con dati reali")
    return processed_data

