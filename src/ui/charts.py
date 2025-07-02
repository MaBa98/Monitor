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

def create_radar_chart(data, title='Confronto Opzioni'):
    """Crea un radar chart per confrontare diverse opzioni."""
    categories = list(data[0].keys())[1:] # Esclude 'label'
    
    fig = go.Figure()

    for item in data:
        fig.add_trace(go.Scatterpolar(
            r=[item[cat] for cat in categories],
            theta=categories,
            fill='toself',
            name=item['label']
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(max(d.values()) for d in data for d in [d if isinstance(d, dict) else {'val': d}]) if data else 1]
            )),
        showlegend=True,
        title=title
    )
    return fig
