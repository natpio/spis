import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import base64
from PIL import Image

# =========================================================
# 1. KONFIGURACJA I STYLIZACJA (VORTEZA MASTER)
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER", layout="wide")

def apply_vorteza_theme():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700&display=swap');
            
            :root {
                --v-copper: #B58863;
                --v-dark: #0E0E0E;
                --v-panel: rgba(25, 25, 25, 0.95);
            }

            .stApp {
                background-color: var(--v-dark);
                color: #E0E0E0;
                font-family: 'Montserrat', sans-serif;
            }

            .vorteza-card {
                background-color: var(--v-panel);
                padding: 25px;
                border-radius: 5px;
                border-left: 5px solid var(--v-copper);
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }

            h1, h2, h3 {
                color: var(--v-copper) !important;
                text-transform: uppercase;
                letter-spacing: 2px;
                font-weight: 700 !important;
            }

            /* STYLIZACJA TABELI - KLUCZ DO ROZWIĄZANIA */
            .vorteza-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                background-color: transparent;
            }
            .vorteza-table th {
                color: var(--v-copper);
                text-align: left;
                padding: 15px;
                border-bottom: 2px solid var(--v-copper);
                text-transform: uppercase;
                font-size: 0.85rem;
            }
            .vorteza-table td {
                padding: 15px;
                border-bottom: 1px solid #333;
                font-size: 0.9rem;
            }
            .row-expired {
                background-color: rgba(255, 0, 0, 0.1);
                color: #ffbaba !important;
            }

            .stButton > button {
                background-color: transparent;
                color: var(--v-copper);
                border: 1px solid var(--v-copper);
                transition: 0.3s;
                font-weight: bold;
            }
            .stButton > button:hover {
                background-color: var(--v-copper);
                color: black;
            }
        </style>
    """, unsafe_allow_html=True)

apply_vorteza_theme()

# =========================================================
# 2. POŁĄCZENIE I DANE
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    df = conn.read(ttl=0)
    # Czyszczenie nagłówków
    df.columns = [str(c).strip() for c in df.columns]
    
    # Obsługa kolumny statusu
    status_col = next((c for c in df.columns if 'status' in c.lower() or 'aktyw' in c.lower()), None)
    if status_col:
        df.rename(columns={status_col: 'STATUS_INTERNAL'}, inplace=True)
    else:
        df['STATUS_INTERNAL'] = True
        
    df['display_name'] = df['firma_id'].astype(str) + " | " + df['uzytkownik_id'].astype(str)
    return df

try:
    data = get_data()
except Exception as e:
    st.error(f"Błąd danych: {e}")
    st.stop()

# =========================================================
# 3. INTERFEJS
# =========================================================
menu = ["📊 DASHBOARD", "🔧 KONFIGURACJA", "➕ NOWY KLIENT"]
choice = st.sidebar.selectbox("NAWIGACJA", menu)

if choice == "📊 DASHBOARD":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("STATUS EKONOMICZNY")
    
    active_mask = data['STATUS_INTERNAL'] == True
    total_rev = data[active_mask]['kwota_subskrypcji'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("PRZYCHÓD (M)", f"{total_rev:,.2f} PLN")
    m2.metric("AKTYWNE SYSTEMY", len(data[active_mask]))
    m3.metric("SUMA KLIENTÓW", len(data))
    st.markdown('</div>', unsafe_allow_html=True)

    # --- GENEROWANIE TABELI JAKO JEDEN CIĄG HTML (NAJBARDZIEJ STABILNE) ---
    st.subheader("LISTA OPERACYJNA")
    
    html_code = '<table class="vorteza-table"><thead><tr>'
    html_code += '<th>Firma</th><th>Użytkownik</th><th>Status</th><th>Wygasa</th><th>Kwota</th>'
    html_code += '</tr></thead><tbody>'

    today = datetime.now().date()

    for _, row in data.iterrows():
        is_active = row['STATUS_INTERNAL']
        status_txt = "✅ AKTYWNY" if is_active else "❌ BLOKADA"
        
        # Sprawdzanie daty wygaśnięcia
        style_class = ""
        try:
            exp_date = pd.to_datetime(row['data_konca']).date()
            if exp_date < today and is_active:
                style_class = 'class="row-expired"'
        except:
            pass

        html_code += f'''
        <tr {style_class}>
            <td>{row['firma_id']}</td>
            <td>{row['uzytkownik_id']}</td>
            <td>{status_txt}</td>
            <td>{row['data_konca']}</td>
            <td>{row['kwota_subskrypcji']:.2f} PLN</td>
        </tr>
        '''
    
    html_code += '</tbody></table>'
    
    # WYŚWIETLENIE GOTOWEJ TABELI
    st.markdown(html_code, unsafe_allow_html=True)

elif choice == "🔧 KONFIGURACJA":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    selected = st.selectbox("Wybierz instancję:", data['display_name'].tolist())
    idx = data[data['display_name'] == selected].index[0]
    row = data.loc[idx]

    with st.form("edit_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_pass = st.text_input("Hasło", value=str(row['haslo']))
            n_status = st.checkbox("Status Aktywny", value=bool(row['STATUS_INTERNAL']))
        with c2:
            n_end = st.text_input("Data Końca (RRRR-MM-DD)", value=str(row['data_konca']))
            n_price = st.number_input("Kwota", value=float(row['kwota_subskrypcji']))
            
        if st.form_submit_button("ZAKTUALIZUJ"):
            df_up = data.copy().drop(columns=['display_name', 'STATUS_INTERNAL'])
            # Przywrócenie nazwy kolumny statusu dla GSheets
            real_col = next((c for c in data.columns if 'status' in c.lower() or 'aktyw' in c.lower()), 'status_aktywny')
            df_up[real_col] = data['STATUS_INTERNAL']
            
            df_up.at[idx, 'haslo'] = n_pass
            df_up.at[idx, real_col] = n_status
            df_up.at[idx, 'data_konca'] = n_end
            df_up.at[idx, 'kwota_subskrypcji'] = n_price
            
            conn.update(data=df_up)
            st.success("Dane zapisane.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif choice == "➕ NOWY KLIENT":
    with st.form("new"):
        f = st.text_input("FIRMA ID")
        u = st.text_input("USER ID")
        h = st.text_input("HASŁO")
        d = st.date_input("DATA KOŃCA")
        k = st.number_input("KWOTA", value=250.0)
        if st.form_submit_button("DODAJ"):
            new_r = {"firma_id":f, "uzytkownik_id":u, "haslo":h, "data_konca":str(d), "kwota_subskrypcji":k, "status_aktywny":True}
            final = pd.concat([data.drop(columns=['display_name','STATUS_INTERNAL']), pd.DataFrame([new_r])], ignore_index=True)
            conn.update(data=final)
            st.success("Dodano.")
            st.rerun()
