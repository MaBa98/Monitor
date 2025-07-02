def apply_custom_styling():
    """Applica CSS custom all'app Streamlit."""
    custom_css = """
    <style>
        /* Stile generale */
        .stApp {
            background-color: #f0f2f6;
        }
        /* Stile cards metriche */
        .metric-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .metric-card h4 {
            margin: 0;
            color: #1e3a8a; /* Blu scuro */
        }
        .metric-card p {
            font-size: 24px;
            font-weight: bold;
            margin: 5px 0 0 0;
            color: #333;
        }
        /* Badge di avviso */
        .risk-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: bold;
            color: white;
            background-color: #ef4444; /* Rosso */
        }
        .ok-badge {
            background-color: #22c55e; /* Verde */
        }
    </style>
    """
    return custom_css
