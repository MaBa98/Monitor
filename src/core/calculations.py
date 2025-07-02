import numpy as np

def calculate_metrics(option_data, underlying_price, k_as_param):
    """
    Calcola tutte le metriche core per una singola opzione.
    """
    strike = option_data['strike']
    premium = option_data['premium']
    iv = option_data['iv']
    delta = option_data['delta']
    gamma = option_data['gamma']
    theta = option_data['theta']
    dte = option_data['dte']
    
    # --- Metriche Primarie ---
    
    # Premium Yield
    premium_yield = (premium / strike) * 100
    
    # Moneyness
    moneyness = (strike - underlying_price) / underlying_price
    
    # Assignment Score (AS)
    # L'HV20 viene passato direttamente dal chiamante per efficienza
    hv_20 = option_data['hv_20']
    assignment_score = (iv / hv_20) * abs(delta) * np.exp(-k_as_param * abs(moneyness)) if hv_20 > 0 else 0
        
    # Probability of Profit (POP)
    # Stima del movimento atteso del sottostante
    expected_move = underlying_price * iv * np.sqrt(dte / 365)
    pop = abs(delta) + (gamma * expected_move * 0.5)
    pop = min(pop, 1.0) # POP non può superare 100%

    # --- Metriche Secondarie ---
    
    # Expected PnL
    # Per una put venduta, il PnL atteso è il premio per la probabilità che scada OTM (1 - delta)
    expected_pnl = premium * (1 - abs(delta))
    
    # Return on Risk (ROR)
    # Ritorno sul capitale a rischio (margine richiesto)
    return_on_risk = (premium / (strike - premium)) * 100 if (strike - premium) > 0 else np.inf
    
    # Breakeven Price
    breakeven = strike - premium
    
    # Theta per day (già negativo, lo rendiamo positivo per chiarezza)
    theta_daily = abs(theta)

    return {
        'Premium Yield %': round(premium_yield, 2),
        'AS': round(assignment_score, 4),
        'POP %': round(pop * 100, 2),
        'Moneyness %': round(moneyness * 100, 2),
        'Expected PnL': round(expected_pnl, 2),
        'Return on Risk %': round(return_on_risk, 2),
        'Breakeven': round(breakeven, 2),
        'Theta Daily': round(theta_daily, 3),
        'Strike': strike,
        'DTE': dte,
        'Premium': premium,
        'IV': iv
    }
