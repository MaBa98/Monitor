import plotly.graph_objects as go
import numpy as np
import pandas as pd

def create_payoff_diagram(strike, premium, underlying_price):
    """Crea il diagramma di payoff per una PUT venduta."""
    breakeven = strike - premium
    
    # Range di prezzi del sottostante
    price_range = np.linspace(underlying_price * 0.8, underlying_price * 1.2, 100)
    
    # Calcolo del P/L
    pnl = [min(premium, premium - (strike - s)) for s in price_range]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=price_range, y=pnl, mode='lines', name='P/L at Expiration'))
    
    # Linee di riferimento
    fig.add_hline(y=0, line_dash="dash", line_color="grey")
    fig.add_vline(x=strike, line_dash="dash", line_color="orange", name="Strike")
    fig.add_vline(x=breakeven, line_dash="dash", line_color="red", name="Breakeven")
    fig.add_vline(x=underlying_price, line_dash="dash", line_color="blue", name="Current Price")

    fig.update_layout(
        title="Diagramma di Payoff (Short PUT)",
        xaxis_title="Prezzo Sottostante alla Scadenza",
        yaxis_title="Profit/Loss",
        legend=dict(x=0.01, y=0.99)
    )
    return fig

# --- FUNZIONE CORRETTA ---
def create_radar_chart(data, title='Confronto Opzioni'):
    """Crea un radar chart per confrontare diverse opzioni."""
    if not data:
        return go.Figure().update_layout(title=title)

    # Estrae le categorie numeriche (tutte le chiavi tranne 'label')
    categories = [k for k in data[0].keys() if k != 'label']
    
    fig = go.Figure()

    for item in data:
        fig.add_trace(go.Scatterpolar(
            r=[item.get(cat, 0) for cat in categories], # Usa i dati numerici
            theta=categories,
            fill='toself',
            name=item['label'] # Usa la label per il nome della traccia
        ))

    # --- LOGICA DI CALCOLO DEL RANGE CORRETTA ---
    # Calcola il valore massimo solo sui dati numerici per impostare correttamente l'asse.
    max_val = 0
    for d in data:
        # Prende tutti i valori tranne la label e calcola il massimo parziale
        numeric_values = [v for k, v in d.items() if isinstance(v, (int, float))]
        if numeric_values:
            max_val = max(max_val, max(numeric_values))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max_val * 1.05] # Imposta il range con un 5% di margine
            )
        ),
        showlegend=True,
        title=title,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
    )
    return fig
