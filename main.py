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

# --- FUNZIONE DI CALLBACK ---
def update_comparison_list():
    """
    Aggiorna la lista di opzioni da confrontare in base alle checkbox spuntate.
    """
    edited_rows = st.session_state.main_table.get('edited_rows', {})
    current_list = st.session_state.get('comparison_list', [])
    
    for row_index, changes in edited_rows.items():
        is_checked = changes.get('Confronta', None)
        if is_checked is True and row_index not in current_list:
            current_list.append(row_index)
        elif is_checked is False and row_index in current_list:
            current_list.remove(row_index)
    
    st.session_state.comparison_list = sorted(current_list)

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
        option['hv_20'] = hv_20
        metrics = calculate_metrics(option, underlying_price, k_param)
        
        if abs(option['delta']) <= max_delta:
            row = {
                'Ticker': ticker,
                'Sottostante': f"${underlying_price:.2f}",
                'HV20': f"{hv_20:.2%}",
                **option,
                **metrics,
            }
            if row['Premium Yield %'] >= min_yield and row['DTE'] <= max_dte:
                 all_options.append(row)

if not all_options:
    st.warning("Nessuna opzione trovata con i filtri correnti. Prova ad allargare i criteri.")
    st.stop()

df = pd.DataFrame(all_options).sort_values(by=sort_by, ascending=sort_ascending).reset_index(drop=True)

# --- MAIN AREA ---
st.title("Dashboard Opzioni PUT")
st.markdown(f"Analisi per i tickers: **{', '.join(selected_tickers)}** | Dati aggiornati al: **{pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}**")

tab1, tab2, tab3 = st.tabs(["Panoramica 📈", "Analisi Dettagliata 🔬", "Confronto ⚖️"])

# --- TAB 1: PANORAMICA ---
with tab1:
    st.header("Panoramica Opzioni filtrate")

    display_cols = ['Ticker', 'Strike', 'DTE', 'Premium', 'Premium Yield %', 'AS', 'POP %', 'Moneyness %']
    df_display = df[display_cols].copy()
    
    df_display.insert(0, 'Confronta', False)
    for index in st.session_state.comparison_list:
        if index in df_display.index:
            df_display.loc[index, 'Confronta'] = True

    edited_df = st.data_editor(
        color_code_dataframe(df_display, ['Premium Yield %', 'AS', 'POP %']),
        hide_index=True,
        use_container_width=True,
        key="main_table",
        on_change=update_comparison_list
    )

    st.info("💡 **Per i dettagli**: Clicca su una riga O spunta la casella 'Confronta'.")

    # --- NUOVA LOGICA DI SELEZIONE UNIFICATA ---
    selected_index = None

    # Caso 1: L'utente ha interagito con una checkbox.
    edited_rows = st.session_state.main_table.get('edited_rows', {})
    if edited_rows:
        last_edited_index = list(edited_rows.keys())[-1]
        # Se la casella è stata SPUNTATA, seleziona la riga per i dettagli.
        if edited_rows[last_edited_index].get('Confronta') is True:
            selected_index = last_edited_index
    
    # Caso 2: L'utente ha cliccato direttamente su una riga. Questa azione ha la priorità.
    if 'selection' in st.session_state.main_table and st.session_state.main_table['selection']['rows']:
        selected_index = st.session_state.main_table['selection']['rows'][0]

    # Aggiorna l'opzione per la vista dettagliata se un indice è stato selezionato.
    if selected_index is not None and selected_index < len(df):
        st.session_state.selected_option = df.iloc[selected_index]
    # Se l'ultima azione è stata deselezionare tutto, svuota i dettagli.
    elif not st.session_state.comparison_list:
        st.session_state.selected_option = None
    # --- FINE LOGICA DI SELEZIONE ---


# --- TAB 2: ANALISI DETTAGLIATA ---
with tab2:
    if st.session_state.selected_option is None:
        st.info("Seleziona un'opzione dalla tabella 'Panoramica' per visualizzare i dettagli.")
    else:
        opt = st.session_state.selected_option
        st.header(f"Analisi per {opt['Ticker']} - Strike ${opt['Strike']:.2f}")
        st.subheader(f"Scadenza: {opt['DTE']} giorni | Sottostante: ${float(opt['Sottostante'].replace('$', '')):.2f}")

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
        
        radar_data = []
        for i, row in comparison_df.iterrows():
            as_inverted_normalized = 1 - (row['AS'] / df['AS'].max())
            radar_data.append({
                'label': f"{row['Ticker']} ${row['Strike']:.0f}",
                'Premium Yield': row['Premium Yield %'],
                'POP': row['POP %'],
                'AS (Invertito)': as_inverted_normalized * 100
            })
        
        if radar_data:
            max_yield = max(d['Premium Yield'] for d in radar_data) or 1
            max_pop = max(d['POP'] for d in radar_data) or 1
            for d in radar_data:
                d['Premium Yield'] = (d['Premium Yield'] / max_yield) * 100
                d['POP'] = (d['POP'] / max_pop) * 100

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Radar Chart Comparativo")
            st.plotly_chart(create_radar_chart(radar_data), use_container_width=True)
        
        with col2:
            st.subheader("Tabella di Confronto")
            display_cols_comp = ['Ticker', 'Strike', 'Premium Yield %', 'AS', 'POP %', 'Return on Risk %', 'Breakeven']
            st.dataframe(comparison_df[display_cols_comp].set_index('Ticker'), use_container_width=True)
