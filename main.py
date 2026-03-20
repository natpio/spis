import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# =========================================================
# 1. KONFIGURACJA I STYLIZACJA VORTEZA
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap');
        .stApp { background-color: #0E0E0E; color: #E0E0E0; font-family: 'Montserrat', sans-serif; }
        h1, h2, h3 { color: #B58863 !important; text-transform: uppercase; letter-spacing: 2px; }
        /* Stylizacja metryk */
        [data-testid="stMetricValue"] { color: #B58863 !important; font-weight: 700; }
        /* Karta VORTEZA */
        .vorteza-card {
            background-color: #181818;
            padding: 20px;
            border-radius: 4px;
            border-left: 4px solid #B58863;
            margin-bottom: 25px;
        }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 2. DANE I POŁĄCZENIE
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl=0)
    df.columns = [str(c).strip() for c in df.columns]
    # Mapowanie statusu
    status_col = next((c for c in df.columns if 'status' in c.lower() or 'aktyw' in c.lower()), 'status_aktywny')
    df.rename(columns={status_col: 'AKTYWNY'}, inplace=True)
    df['display_name'] = df['firma_id'].astype(str) + " | " + df['uzytkownik_id'].astype(str)
    return df

try:
    data = load_data()
except Exception as e:
    st.error(f"BŁĄD DANYCH: {e}")
    st.stop()

# =========================================================
# 3. INTERFEJS UŻYTKOWNIKA
# =========================================================
menu = ["📊 DASHBOARD", "🔧 KONFIGURACJA", "➕ NOWY KLIENT"]
choice = st.sidebar.selectbox("NAWIGACJA", menu)

if choice == "📊 DASHBOARD":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("SYSTEM STATUS")
    
    active_mask = data['AKTYWNY'] == True
    total_rev = data[active_mask]['kwota_subskrypcji'].sum()
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("PRZYCHÓD (M)", f"{total_rev:,.2f} PLN")
    col_m2.metric("AKTYWNE SYSTEMY", len(data[active_mask]))
    col_m3.metric("SUMA KLIENTÓW", len(data))
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("LISTA OPERACYJNA")

    # Używamy natywnego st.dataframe z zaawansowaną konfiguracją kolumn
    # To rozwiązanie NIGDY nie wyświetli surowego kodu HTML
    st.dataframe(
        data[['firma_id', 'uzytkownik_id', 'AKTYWNY', 'data_konca', 'kwota_subskrypcji']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "firma_id": st.column_config.TextColumn("FIRMA"),
            "uzytkownik_id": st.column_config.TextColumn("UŻYTKOWNIK"),
            "AKTYWNY": st.column_config.CheckboxColumn("STATUS"),
            "data_konca": st.column_config.DateColumn("TERMIN WYGAŚNIĘCIA"),
            "kwota_subskrypcji": st.column_config.NumberColumn("KWOTA", format="%.2f PLN"),
        }
    )

elif choice == "🔧 KONFIGURACJA":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("EDYCJA PARAMETRÓW")
    selected = st.selectbox("Wybierz instancję:", data['display_name'].tolist())
    idx = data[data['display_name'] == selected].index[0]
    row = data.loc[idx]

    with st.form("edit_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_pass = st.text_input("Klucz (Hasło)", value=str(row['haslo']))
            n_status = st.checkbox("Dostęp Aktywny", value=bool(row['AKTYWNY']))
        with c2:
            n_end = st.text_input("Termin (RRRR-MM-DD)", value=str(row['data_konca']))
            n_price = st.number_input("Stawka", value=float(row['kwota_subskrypcji']))
            
        if st.form_submit_button("ZAPISZ ZMIANY W BAZIE"):
            df_up = data.copy().drop(columns=['display_name', 'AKTYWNY'])
            # Przywracamy nazwę do arkusza
            real_col = next((c for c in data.columns if 'status' in c.lower() or 'aktyw' in c.lower()), 'status_aktywny')
            df_up[real_col] = data['AKTYWNY']
            
            df_up.at[idx, 'haslo'] = n_pass
            df_up.at[idx, real_col] = n_status
            df_up.at[idx, 'data_konca'] = n_end
            df_up.at[idx, 'kwota_subskrypcji'] = n_price
            
            conn.update(data=df_up)
            st.success("Synchronizacja zakończona pomyślnie.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif choice == "➕ NOWY KLIENT":
    with st.form("new_client"):
        st.subheader("REJESTRACJA")
        f = st.text_input("FIRMA ID")
        u = st.text_input("USER ID")
        h = st.text_input("HASŁO")
        d = st.date_input("DATA KOŃCA")
        k = st.number_input("KWOTA", value=250.0)
        
        if st.form_submit_button("DODAJ"):
            new_r = {"firma_id":f, "uzytkownik_id":u, "haslo":h, "data_konca":str(d), "kwota_subskrypcji":k, "status_aktywny":True}
            final = pd.concat([data.drop(columns=['display_name', 'AKTYWNY']), pd.DataFrame([new_r])], ignore_index=True)
            conn.update(data=final)
            st.success("Dodano klienta.")
            st.rerun()
