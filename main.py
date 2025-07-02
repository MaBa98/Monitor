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
from src.data.data_provider import DataProvider

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
if 'selected_option_index' not in st.session_state:
    st.session_state.selected_option_index = None
if 'comparison_list' not in st.session_state:
    st.session_state.comparison_list = []

# --- CARICAMENTO E CACHING DATI ---
@st.cache_data(show_spinner="Caricamento dati di mercato...")
def load_data(tickers, data_source):
    """Carica i dati usando il DataProvider"""
    provider = DataProvider(data_source=data_source)
    return provider.get_options_data(tickers)

# --- FUNZIONI DI CALLBACK ---
def handle_details_selection():
    """
    Gestisce la selezione per l'analisi dettagliata tramite pulsante.
    """
    edited_rows = st.session_state.main_table.get('edited_rows', {})
    
    for row_index, changes in edited_rows.items():
        # Verifica se il pulsante "Dettagli" è stato cliccato
        if changes.get('Dettagli', None) == True:
            st.session_state.selected_option_index = row_index
            # Reset del pulsante per evitare loop
            st.session_state.main_table['edited_rows'][row_index]['Dettagli'] = False
            break

def handle_comparison_selection():
    """
    Gestisce la selezione per il confronto tramite checkbox.
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

def update_table_state():
    """
    Callback unificato per aggiornare lo stato della tabella.
    """
    handle_details_selection()
    handle_comparison_selection()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎯 Analizzatore Wheel")
    
    ticker_mode = st.radio(
        "Modalità selezione ticker:",
        ["Lista predefinita", "Inserimento manuale"],
        horizontal=True
    )
    
    if ticker_mode == "Lista predefinita":
        available_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "SPY", "QQQ", "JPM", "V"]
        selected_tickers = st.multiselect("Seleziona Tickers", available_tickers, default=["AAPL", "MSFT", "TSLA"])
    else:
        # Input manuale
        ticker_input = st.text_input(
            "Inserisci ticker (separati da virgola):",
            placeholder="es: AAPL, MSFT, TSLA",
            help="Inserisci i simboli ticker separati da virgola"
        )
        
        if ticker_input:
            # Pulisci e valida input
            selected_tickers = [ticker.strip().upper() for ticker in ticker_input.split(",") if ticker.strip()]
            selected_tickers = list(dict.fromkeys(selected_tickers))  # Rimuovi duplicati
            
            if selected_tickers:
                st.success(f"Ticker selezionati: {', '.join(selected_tickers)}")
            else:
                st.warning("Inserisci almeno un ticker valido")
        else:
            selected_tickers = []

    st.header("📊 Fonte Dati")
    data_source = st.radio(
        "Scegli fonte dati:",
        options=['real', 'mock'],
        format_func=lambda x: 'Dati Reali (yfinance)' if x == 'real' else 'Dati Simulati (Mock)',
        index=0,
        help="Dati Reali: usa le option chain di yfinance\nDati Simulati: usa dati generati per test"
    )
    
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

options_data = load_data(selected_tickers, data_source)

if not options_data:
    st.error("Nessun dato disponibile per i ticker selezionati. Verifica la connessione o prova con dati simulati.")
    st.stop()
    
all_options = []

for ticker, data in options_data.items():
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

    # Preparazione colonne per la visualizzazione
    display_cols = ['Ticker', 'Strike', 'DTE', 'Premium', 'Premium Yield %', 'AS', 'POP %', 'Moneyness %']
    df_display = df[display_cols].copy()
    
    # Aggiunta colonne di controllo
    df_display.insert(0, 'Dettagli', False)  # Pulsante per analisi dettagliata
    df_display.insert(1, 'Confronta', False)  # Checkbox per confronto
    
    # Ripristino stato checkbox confronto
    for index in st.session_state.comparison_list:
        if index in df_display.index:
            df_display.loc[index, 'Confronta'] = True

    # Visualizzazione tabella interattiva
    edited_df = st.data_editor(
        color_code_dataframe(df_display, ['Premium Yield %', 'AS', 'POP %']),
        hide_index=True,
        use_container_width=True,
        key="main_table",
        on_change=update_table_state,
        column_config={
            "Dettagli": st.column_config.CheckboxColumn(
                "🔍",
                help="Clicca per visualizzare i dettagli",
                default=False,
                width="small"
            ),
            "Confronta": st.column_config.CheckboxColumn(
                "⚖️",
                help="Spunta per aggiungere al confronto",
                default=False,
                width="small"
            ),
            "Premium Yield %": st.column_config.NumberColumn(
                "Premium Yield %",
                help="Rendimento del premio",
                format="%.2f%%"
            ),
            "AS": st.column_config.NumberColumn(
                "AS",
                help="Assignment Score",
                format="%.4f"
            ),
            "POP %": st.column_config.NumberColumn(
                "POP %",
                help="Probability of Profit",
                format="%.1f%%"
            ),
            "Moneyness %": st.column_config.NumberColumn(
                "Moneyness %",
                help="Percentuale di moneyness",
                format="%.1f%%"
            )
        }
    )

    # Informazioni di utilizzo
    col1, col2 = st.columns(2)
    with col1:
        st.info("🔍 **Per i dettagli**: Clicca sulla casella nella colonna 'Dettagli'")
    with col2:
        st.info("⚖️ **Per il confronto**: Spunta le caselle nella colonna 'Confronta'")

    # Aggiornamento opzione selezionata per i dettagli
    if st.session_state.selected_option_index is not None and st.session_state.selected_option_index < len(df):
        st.session_state.selected_option = df.iloc[st.session_state.selected_option_index]

    # Mostra stato attuale
    if st.session_state.selected_option is not None:
        st.success(f"✅ **Selezionata per dettagli**: {st.session_state.selected_option['Ticker']} - Strike ${st.session_state.selected_option['Strike']:.2f}")
    
    if st.session_state.comparison_list:
        comparison_tickers = [df.iloc[i]['Ticker'] + f" ${df.iloc[i]['Strike']:.2f}" for i in st.session_state.comparison_list]
        st.success(f"✅ **In confronto**: {', '.join(comparison_tickers)}")

# --- TAB 2: ANALISI DETTAGLIATA ---
with tab2:
    if st.session_state.selected_option is None:
        st.info("🔍 Seleziona un'opzione dalla tabella 'Panoramica' cliccando sulla colonna 'Dettagli' per visualizzare l'analisi completa.")
        
        # Pulsante per tornare alla panoramica
        if st.button("📈 Vai alla Panoramica", type="primary"):
            st.switch_page("main.py")
    else:
        opt = st.session_state.selected_option
        
        # Header con informazioni principali
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.header(f"📊 Analisi {opt['Ticker']} - Strike ${opt['Strike']:.2f}")
        with col2:
            if st.button("🔄 Aggiorna Selezione", help="Torna alla panoramica per selezionare un'altra opzione"):
                st.session_state.selected_option = None
                st.session_state.selected_option_index = None
                st.rerun()
        with col3:
            if st.button("⚖️ Aggiungi al Confronto", help="Aggiungi questa opzione al confronto"):
                if st.session_state.selected_option_index not in st.session_state.comparison_list:
                    st.session_state.comparison_list.append(st.session_state.selected_option_index)
                    st.success("Aggiunta al confronto!")
                else:
                    st.info("Già presente nel confronto")

        st.subheader(f"📅 Scadenza: {opt['DTE']} giorni | 💰 Sottostante: ${float(opt['Sottostante'].replace('$', '')):.2f}")

        st.markdown("---")
        
        # Metriche principali in grid
        cols = st.columns(4)
        metric_items = [
            ("Premium Yield", f"{opt['Premium Yield %']}%", "💰"),
            ("Assignment Score", f"{opt['AS']:.4f}", "📊"),
            ("Prob. of Profit", f"{opt['POP %']}%", "🎯"),
            ("Return on Risk", f"{opt['Return on Risk %']}%", "⚡"),
            ("Breakeven", f"${opt['Breakeven']:.2f}", "🔒"),
            ("Theta Daily Decay", f"${opt['Theta Daily']:.3f}", "⏰"),
            ("IV", f"{opt['IV']:.1%}", "📈"),
            ("Moneyness", f"{opt['Moneyness %']}%", "💵")
        ]
        
        for i, (label, value, icon) in enumerate(metric_items):
            with cols[i % 4]:
                st.markdown(f"""
                <div class="metric-card">
                    <h4>{icon} {label}</h4>
                    <p>{value}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        
        # Grafici e analisi del rischio
        chart_col, risk_col = st.columns([2, 1])

        with chart_col:
            st.subheader("📊 Payoff Diagram")
            st.plotly_chart(create_payoff_diagram(opt['Strike'], opt['Premium'], float(opt['Sottostante'].replace('$', ''))), use_container_width=True)

        with risk_col:
            st.subheader("⚠️ Valutazione Rischio")
            
            # Analisi Assignment Score
            if opt['AS'] > df['AS'].quantile(0.75):
                st.markdown('<span class="risk-badge">🔴 RISCHIO ASSEGN. ALTO</span>', unsafe_allow_html=True)
                st.write("L'Assignment Score è nel quartile più alto, indicando un rischio di assegnazione elevato rispetto alle altre opzioni.")
            else:
                st.markdown('<span class="risk-badge ok-badge">🟢 RISCHIO ASSEGN. OK</span>', unsafe_allow_html=True)
                st.write("L'Assignment Score è nella norma.")
            
            # Analisi Delta
            if abs(opt['delta']) > 0.45:
                st.markdown('<span class="risk-badge">🔴 DELTA ELEVATO</span>', unsafe_allow_html=True)
                st.write("Il delta è alto, suggerendo una maggiore sensibilità al prezzo del sottostante e una più alta probabilità di finire ITM.")
            else:
                st.markdown('<span class="risk-badge ok-badge">🟢 DELTA OK</span>', unsafe_allow_html=True)
                st.write("Il delta è nella norma.")
            
            # Analisi DTE
            if opt['DTE'] < 21:
                st.markdown('<span class="risk-badge">🟡 DTE BREVE</span>', unsafe_allow_html=True)
                st.write("Il tempo alla scadenza è relativamente breve, aumentando l'effetto del time decay.")
            else:
                st.markdown('<span class="risk-badge ok-badge">🟢 DTE OK</span>', unsafe_allow_html=True)

# --- TAB 3: CONFRONTO ---
with tab3:
    if not st.session_state.comparison_list:
        st.info("⚖️ Seleziona due o più opzioni dalla tabella 'Panoramica' usando le checkbox nella colonna 'Confronta' per visualizzare il confronto.")
        
        # Pulsante per tornare alla panoramica
        if st.button("📈 Vai alla Panoramica per Selezionare", type="primary"):
            st.switch_page("main.py")
    else:
        comparison_df = df.iloc[st.session_state.comparison_list]
        
        # Header con controlli
        col1, col2 = st.columns([3, 1])
        with col1:
            st.header(f"⚖️ Confronto tra {len(st.session_state.comparison_list)} Opzioni Selezionate")
        with col2:
            if st.button("🗑️ Svuota Confronto", help="Rimuovi tutte le opzioni dal confronto"):
                st.session_state.comparison_list = []
                st.rerun()

        # Lista opzioni in confronto
        st.subheader("📋 Opzioni in Confronto:")
        for i, idx in enumerate(st.session_state.comparison_list):
            row = df.iloc[idx]
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{i+1}.** {row['Ticker']} - Strike ${row['Strike']:.2f} | DTE: {row['DTE']} | Yield: {row['Premium Yield %']:.2f}%")
            with col2:
                if st.button(f"❌", key=f"remove_{idx}", help="Rimuovi dal confronto"):
                    st.session_state.comparison_list.remove(idx)
                    st.rerun()

        st.markdown("---")
        
        # Preparazione dati per radar chart
        radar_data = []
        for i, row in comparison_df.iterrows():
            as_inverted_normalized = 1 - (row['AS'] / df['AS'].max())
            radar_data.append({
                'label': f"{row['Ticker']} ${row['Strike']:.0f}",
                'Premium Yield': row['Premium Yield %'],
                'POP': row['POP %'],
                'AS (Invertito)': as_inverted_normalized * 100
            })
        
        # Normalizzazione per radar chart
        if radar_data:
            max_yield = max(d['Premium Yield'] for d in radar_data) or 1
            max_pop = max(d['POP'] for d in radar_data) or 1
            for d in radar_data:
                d['Premium Yield'] = (d['Premium Yield'] / max_yield) * 100
                d['POP'] = (d['POP'] / max_pop) * 100

        # Layout confronto
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🕸️ Radar Chart Comparativo")
            if radar_data:
                st.plotly_chart(create_radar_chart(radar_data), use_container_width=True)
            else:
                st.info("Nessun dato disponibile per il radar chart.")
        
        with col2:
            st.subheader("📊 Tabella di Confronto")
            display_cols_comp = ['Ticker', 'Strike', 'Premium Yield %', 'AS', 'POP %', 'Return on Risk %', 'Breakeven']
            comparison_table = comparison_df[display_cols_comp].copy()
            
            # Evidenziazione valori migliori
            st.dataframe(
                comparison_table.style.highlight_max(subset=['Premium Yield %', 'POP %', 'Return on Risk %'], color='lightgreen')
                                    .highlight_min(subset=['AS'], color='lightgreen'),
                use_container_width=True
            )

        # Riassunto confronto
        st.markdown("---")
        st.subheader("📝 Riassunto Confronto")
        
        best_yield = comparison_df.loc[comparison_df['Premium Yield %'].idxmax()]
        best_pop = comparison_df.loc[comparison_df['POP %'].idxmax()]
        best_as = comparison_df.loc[comparison_df['AS'].idxmin()]  # Minore è meglio per AS
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏆 Miglior Premium Yield", 
                     f"{best_yield['Ticker']} ${best_yield['Strike']:.2f}", 
                     f"{best_yield['Premium Yield %']:.2f}%")
        with col2:
            st.metric("🏆 Miglior POP", 
                     f"{best_pop['Ticker']} ${best_pop['Strike']:.2f}", 
                     f"{best_pop['POP %']:.1f}%")
        with col3:
            st.metric("🏆 Miglior AS (più basso)", 
                     f"{best_as['Ticker']} ${best_as['Strike']:.2f}", 
                     f"{best_as['AS']:.4f}")
