import numpy as np
import pandas as pd

def generate_mock_data(tickers, underlying_price_map):
    """
    Genera dati mock realistici per una lista di ticker.
    """
    mock_data = {}
    for ticker in tickers:
        try:
            underlying_price = underlying_price_map[ticker]['price']
            hv_20 = underlying_price_map[ticker]['hv_20']
            
            options = []
            # Genera strike prices intorno al prezzo del sottostante
            strikes = np.arange(underlying_price * 0.85, underlying_price * 1.02, 1.0)
            
            for strike in strikes:
                dte = np.random.randint(18, 40)
                iv = hv_20 + np.random.uniform(0.05, 0.15) # IV leggermente > HV
                moneyness = (strike - underlying_price) / underlying_price
                
                # Formula semplificata per il premio (Black-Scholes non necessario per mock)
                premium = max(0.05, strike * np.exp(moneyness) * 0.015 * (dte / 365)**0.5 * iv)
                
                # Genera Greeks realistici
                delta = max(0.05, min(0.55, 0.5 + moneyness * 5)) # Delta tra 0.05 e 0.55
                gamma = (0.6 / (strike * (dte/365)**0.5)) * np.random.uniform(0.8, 1.2)
                theta = -(premium / dte) * np.random.uniform(0.8, 1.2)

                options.append({
                    'strike': strike,
                    'premium': round(premium, 2),
                    'iv': round(iv, 3),
                    'delta': round(delta, 3),
                    'gamma': round(gamma, 4),
                    'theta': round(theta, 3),
                    'volume': np.random.randint(50, 2000),
                    'open_interest': np.random.randint(200, 10000),
                    'dte': dte,
                    'bid': round(premium * 0.99, 2),
                    'ask': round(premium * 1.01, 2),
                    'last': round(premium, 2)
                })

            mock_data[ticker] = {
                'underlying_price': underlying_price,
                'hv_20': hv_20,
                'options': options
            }
        except Exception:
            # Salta ticker se yfinance non trova dati
            continue

    return mock_data
