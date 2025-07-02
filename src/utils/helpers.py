import pandas as pd

def color_code_dataframe(df, columns):
    """Applica color coding basato sui quartili a colonne specifiche."""
    styled_df = df.style
    for col in columns:
        if col in df.columns:
            # Calcola quartili
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            
            def color_cells(val):
                if val >= q3:
                    color = '#dcfce7' # Verde (top)
                elif val < q1:
                    color = '#fee2e2' # Rosso (bottom)
                else:
                    color = '#fef9c3' # Giallo (medio)
                return f'background-color: {color}'
            
            # Per AS, il colore è invertito (più basso è meglio)
            if col == 'AS':
                 def color_cells(val):
                    if val <= q1:
                        color = '#dcfce7'
                    elif val > q3:
                        color = '#fee2e2'
                    else:
                        color = '#fef9c3'
                    return f'background-color: {color}'
            
            styled_df = styled_df.applymap(color_cells, subset=[col])
            
    # Formattazione numerica
    format_dict = {
        'Premium Yield %': '{:.2f}%', 'Moneyness %': '{:.2f}%', 'POP %': '{:.2f}%',
        'Strike': '${:.2f}', 'Premium': '${:.2f}', 'Breakeven': '${:.2f}'
    }
    return styled_df.format(format_dict)
