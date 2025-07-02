import streamlit as st
import pandas as pd
import numpy as np

# Importa moduli custom
from src.data.yfinance_client import get_stock_data
from src.data.mock_generator import generate_mock_data
from src.core.calculations import calculate_metrics
from src.ui.styling import apply_custom_styling
from src.ui.charts import create_payoff_diagram, create_radar_chart
from src.utils.helpers import color_code_dataframe

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Analizzatore Opzioni PUT - Strategia Wheel",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Applica stile CSS custom
st.markdown(apply_custom_styling(), unsafe_allow_html=True)

# --- STATO DELL'APPLICAZIONE ---
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None
if 'comparison_list' not in st.session_state:
    st.session_state.comparison_list = []

# --- CARICAMENTO E CACHING DATI ---
@st.cache_data(show_spinner="Caricamento dati di mercato...")
def load_data(tickers):
    price_map = {}
    for ticker in tickers:
        price, hv_20 = get_stock_data(ticker)
        if price is not None and hv_20 is not None:
            price_map[ticker] = {'price': price, 'hv_20': hv_20}
    
    return generate_mock_data(tickers, price_map)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎯 Analizzatore Wheel")
    
    available_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "SPY", "QQQ", "JPM", "V"]
    selected_tickers = st.multiselect("Seleziona Tickers", available_tickers, default=["AAPL", "MSFT", "TSLA"])

    st.header("Filtri")
    min_yield = st.slider("Premium Yield Min %", 0.0, 5.0, 0.5, 0.1)
    max_dte = st.slider("Max DTE", 15, 60, 35, 1)
    max_delta = st.slider("Max Delta", 0.1, 0.6, 0.4, 0.01)
    k_param = st.slider("Parametro 'k' per AS", 5, 20, 10, 1)
    
    st.header("Ordinamento")
    sort_by = st.selectbox("Ordina per", ["Premium Yield %", "AS", "POP %", "Moneyness %"], index=0)
    sort_ascending = st.checkbox("Ordinamento crescente", value=(sort_by == 'AS'))

# --- ELABORAZIONE DATI ---
if not selected_tickers:
    st.warning("Per favore, seleziona almeno un ticker dalla sidebar.")
    st.stop()

mock_data = load_data(selected_tickers)
all_options = []

for ticker, data in mock_data.items():
    underlying_price = data['underlying_price']
    hv_20 = data['hv_20']
    for option in data['options']:
        # Aggiungo HV20 all'opzione per passarlo ai calcoli
        option['hv_20'] = hv_20
        metrics = calculate_metrics(option, underlying_price, k_param)
        
        # Filtro delta prima di calcolare tutto
        if abs(option['delta']) <= max_delta:
            row = {
                'Ticker': ticker,
                'Sottostante': f"${underlying_price:.2f}",
                'HV20': f"{hv_20:.2%}",
                **option, # Dati originali opzione
                **metrics, # Metriche calcolate
            }
            # Filtro Yield e DTE
            if row['Premium Yield %'] >= min_yield and row['DTE'] <= max_dte:
                 all_options.append(row)

if not all_options:
    st.warning("Nessuna opzione trovata con i filtri correnti. Prova ad allargare i criteri.")
    st.stop()

df = pd.DataFrame(all_options)
df = df.sort_values(by=sort_by, ascending=sort_ascending)

# --- MAIN AREA ---
st.title("Dashboard Opzioni PUT")
st.markdown(f"Analisi per i tickers: **{', '.join(selected_tickers)}** | Dati aggiornati al: **{pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}**")

tab1, tab2, tab3 = st.tabs(["Panoramica 📈", "Analisi Dettagliata 🔬", "Confronto ⚖️"])

# --- TAB 1: PANORAMICA ---
with tab1:
    st.header("Panoramica Opzioni filtrate")

    # Colonne essenziali per la tabella principale
    display_cols = ['Ticker', 'Strike', 'DTE', 'Premium', 'Premium Yield %', 'AS', 'POP %', 'Moneyness %']
    df_display = df[display_cols].reset_index(drop=True)

    # Aggiungi checkbox per confronto
    df_display.insert(0, 'Confronta', False)
    edited_df = st.data_editor(
        color_code_dataframe(df_display, ['Premium Yield %', 'AS', 'POP %']),
        hide_index=True,
        use_container_width=True,
        key="main_table",
        on_change=lambda: st.session_state.update(
            comparison_list=[i for i, row in st.session_state.main_table['edited_rows'].items() if row['Confronta']]
        )
    )

    st.info("💡 Clicca su una riga per vederne i dettagli nella tab 'Analisi Dettagliata'. Seleziona le checkbox per la tab 'Confronto'.")
    
    # Logica per selezionare un'opzione per la vista dettagliata
    if st.session_state.main_table and st.session_state.main_table['selection']['rows']:
        selected_row_index = st.session_state.main_table['selection']['rows'][0]
        st.session_state.selected_option = df.iloc[selected_row_index]


# --- TAB 2: ANALISI DETTAGLIATA ---
with tab2:
    if st.session_state.selected_option is None:
        st.info("Seleziona un'opzione dalla tabella 'Panoramica' per visualizzare i dettagli.")
    else:
        opt = st.session_state.selected_option
        st.header(f"Analisi per {opt['Ticker']} - Strike ${opt['Strike']:.2f}")
        st.subheader(f"Scadenza: {opt['DTE']} giorni | Sottostante: ${float(opt['Sottostante'].replace('$', '')):.2f}")

        # Sezione Metriche
        st.markdown("---")
        cols = st.columns(4)
        metric_items = {
            "Premium Yield": f"{opt['Premium Yield %']}%",
            "Assignment Score": f"{opt['AS']:.4f}",
            "Prob. of Profit": f"{opt['POP %']}%",
            "Return on Risk": f"{opt['Return on Risk %']}%",
            "Breakeven": f"${opt['Breakeven']:.2f}",
            "Theta Daily Decay": f"${opt['Theta Daily']:.3f}",
            "IV": f"{opt['IV']:.1%}",
            "Moneyness": f"{opt['Moneyness %']}%"
        }
        
        for i, (label, value) in enumerate(metric_items.items()):
            with cols[i % 4]:
                st.markdown(f"""
                <div class="metric-card">
                    <h4>{label}</h4>
                    <p>{value}</p>
                </div>
                """, unsafe_allow_html=True)

        # Sezione Grafici e Rischio
        st.markdown("---")
        chart_col, risk_col = st.columns([2, 1])

        with chart_col:
            st.plotly_chart(create_payoff_diagram(opt['Strike'], opt['Premium'], float(opt['Sottostante'].replace('$', ''))), use_container_width=True)

        with risk_col:
            st.subheader("Valutazione Rischio")
            if opt['AS'] > df['AS'].quantile(0.75):
                st.markdown('<span class="risk-badge">RISCHIO ASSEGN. ALTO</span>', unsafe_allow_html=True)
                st.write("L'Assignment Score è nel quartile più alto, indicando un rischio di assegnazione elevato rispetto alle altre opzioni.")
            else:
                 st.markdown('<span class="risk-badge ok-badge">RISCHIO ASSEGN. OK</span>', unsafe_allow_html=True)
            
            if abs(opt['delta']) > 0.45:
                st.markdown('<span class="risk-badge">DELTA ELEVATO</span>', unsafe_allow_html=True)
                st.write("Il delta è alto, suggerendo una maggiore sensibilità al prezzo del sottostante e una più alta probabilità di finire ITM.")
            else:
                st.markdown('<span class="risk-badge ok-badge">DELTA OK</span>', unsafe_allow_html=True)
            
# --- TAB 3: CONFRONTO ---
with tab3:
    if not st.session_state.comparison_list:
        st.info("Seleziona due o più opzioni dalla tabella 'Panoramica' usando le checkbox per confrontarle.")
    else:
        comparison_df = df.iloc[st.session_state.comparison_list]
        st.header("Confronto tra Opzioni Selezionate")
        
        # Dati per il Radar Chart
        radar_data = []
        for i, row in comparison_df.iterrows():
            # Inverti e normalizza AS (più alto è meglio)
            as_inverted_normalized = 1 - (row['AS'] / df['AS'].max())
            
            radar_data.append({
                'label': f"{row['Ticker']} ${row['Strike']}",
                'Premium Yield': row['Premium Yield %'],
                'POP': row['POP %'],
                'AS (Invertito)': as_inverted_normalized * 100 # Scala a 100
            })
        
        # Normalizzazione dati per radar chart
        max_yield = max(d['Premium Yield'] for d in radar_data) if radar_data else 1
        max_pop = max(d['POP'] for d in radar_data) if radar_data else 1
        
        for d in radar_data:
            d['Premium Yield'] = (d['Premium Yield'] / max_yield) * 100
            d['POP'] = (d['POP'] / max_pop) * 100

        # Visualizzazioni
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Radar Chart Comparativo")
            st.plotly_chart(create_radar_chart(radar_data), use_container_width=True)
        
        with col2:
            st.subheader("Tabella di Confronto")
            display_cols_comp = ['Ticker', 'Strike', 'Premium Yield %', 'AS', 'POP %', 'Return on Risk %', 'Breakeven']
            st.dataframe(comparison_df[display_cols_comp], use_container_width=True, hide_index=True)
