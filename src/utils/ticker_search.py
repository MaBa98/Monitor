import requests
import streamlit as st

@st.cache_data(ttl=3600)
def search_ticker(company_name):
    """
    Cerca ticker basato sul nome dell'azienda usando Yahoo Finance API.
    """
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        params = {"q": company_name, "quotes_count": 10, "country": "United States"}
        res = requests.get(url=url, params=params, headers={'User-Agent': user_agent})
        data = res.json()
        results = data.get('quotes', [])
        
        # Filtra solo equity (azioni)
        equity_results = [
            (item['symbol'], item.get('shortname', item.get('longname', '')))
            for item in results
            if item.get('quoteType') == 'EQUITY'
        ]
        
        return equity_results[:5]  # Limita a 5 risultati
        
    except Exception as e:
        st.error(f"Errore nella ricerca ticker: {e}")
        return []

def render_ticker_search():
    """
    Renderizza l'interfaccia di ricerca ticker.
    """
    st.write("🔍 **Ricerca per nome azienda:**")
    
    # Input di ricerca
    search_query = st.text_input(
        "Inserisci nome azienda:",
        placeholder="es: Apple, Microsoft, Tesla",
        key="company_search"
    )
    
    selected_tickers = []
    
    if search_query:
        # Esegui ricerca
        results = search_ticker(search_query)
        
        if results:
            st.write("**Risultati trovati:**")
            
            # Multiselect per scegliere i ticker
            options = [f"{ticker} - {name}" for ticker, name in results]
            selected_options = st.multiselect(
                "Seleziona ticker:",
                options,
                key="ticker_multiselect"
            )
            
            # Estrai solo i ticker selezionati
            selected_tickers = [
                option.split(" - ")[0] 
                for option in selected_options
            ]
            
            if selected_tickers:
                st.success(f"Selezionati: {', '.join(selected_tickers)}")
        else:
            st.warning("Nessun risultato trovato per questa ricerca.")
    
    return selected_tickers
