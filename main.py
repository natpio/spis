import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# =========================================================
# 1. KONFIGURACJA SYSTEMU
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER", layout="wide")

# Czysty, nowoczesny styl bez ryzyka błędów w renderowaniu tabeli
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap');
        .stApp { background-color: #0E0E0E; color: #E0E0E0; font-family: 'Montserrat', sans-serif; }
        h1, h2, h3 { color: #B58863 !important; text-transform: uppercase; letter-spacing: 2px; }
        .vorteza-card {
            background-color: rgba(25, 25, 25, 0.95);
            padding: 20px;
            border-radius: 5px;
            border-left: 5px solid #B58863;
            margin-bottom: 20px;
        }
        [data-testid="stMetricValue"] { color: #B58863 !important; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 2. POŁĄCZENIE Z BAZĄ (GOOGLE SHEETS)
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl=0)
    # Usuwamy spacje i ukryte znaki z nagłówków
    df.columns = [str(c).strip() for c in df.columns]
    
    # Automatyczne wykrywanie kolumny statusu (odporność na literówki w arkuszu)
    status_col = next((c for c in df.columns if 'status' in c.lower() or 'aktyw' in c.lower()), None)
    if status_col:
        df.rename(columns={status_col: 'STATUS_AKT'}, inplace=True)
    else:
        df['STATUS_AKT'] = True
        
    df['display_name'] = df['firma_id'].astype(str) + " | " + df['uzytkownik_id'].astype(str)
    return df

try:
    data = load_data()
except Exception as e:
    st.error(f"BŁĄD DANYCH: {e}")
    st.stop()

# =========================================================
# 3. NAWIGACJA
# =========================================================
menu = ["📊 DASHBOARD", "🔧 KONFIGURACJA", "➕ NOWY KLIENT"]
choice = st.sidebar.selectbox("NAWIGACJA", menu)

# =========================================================
# 4. DASHBOARD (BEZPIECZNA TABELA NATYWNA)
# =========================================================
if choice == "📊 DASHBOARD":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("STATUS OPERACYJNY")
    
    active_df = data[data['STATUS_AKT'] == True]
    total_rev = active_df['kwota_subskrypcji'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("PRZYCHÓD (M)", f"{total_rev:,.2f} PLN")
    m2.metric("AKTYWNE SYSTEMY", len(active_df))
    m3.metric("SUMA INSTANCJI", len(data))
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("LISTA MONITOROWANIA")

    # Funkcja do wizualnego oznaczania wygasłych subskrypcji
    def style_dataframe(row):
        try:
            today = datetime.now().date()
            expiry = pd.to_datetime(row['data_konca']).date()
            if expiry < today and row['STATUS_AKT']:
                return ['background-color: rgba(255, 75, 75, 0.1); color: #ffbaba'] * len(row)
        except: pass
        return [''] * len(row)

    # Wyświetlenie tabeli przez natywny, bezpieczny widget st.dataframe
    cols_to_show = ['firma_id', 'uzytkownik_id', 'STATUS_AKT', 'data_konca', 'kwota_subskrypcji']
    styled_df = data[cols_to_show].style.apply(style_dataframe, axis=1)\
                .format({'kwota_subskrypcji': "{:.2f} PLN"})

    st.dataframe(
        styled_df, 
        use_container_width=True, 
        height=500, 
        hide_index=True
    )

# =========================================================
# 5. KONFIGURACJA (EDYCJA)
# =========================================================
elif choice == "🔧 KONFIGURACJA":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("EDYCJA DOSTĘPU")
    selected = st.selectbox("Wybierz instancję:", data['display_name'].tolist())
    idx = data[data['display_name'] == selected].index[0]
    row = data.loc[idx]

    with st.form("edit_form"):
        c1, c2 = st.columns(2)
        with c1:
            n_pass = st.text_input("Hasło", value=str(row['haslo']))
            n_status = st.checkbox("Dostęp Aktywny", value=bool(row['STATUS_AKT']))
        with c2:
            n_end = st.text_input("Termin (RRRR-MM-DD)", value=str(row['data_konca']))
            n_price = st.number_input("Stawka", value=float(row['kwota_subskrypcji']))
            
        if st.form_submit_button("ZAKTUALIZUJ BAZĘ"):
            df_up = data.copy().drop(columns=['display_name', 'STATUS_AKT'])
            # Szukamy oryginalnej nazwy kolumny statusu w arkuszu
            orig_col = next((c for c in df_up.columns if 'status' in c.lower() or 'aktyw' in c.lower()), 'status_aktywny')
            
            df_up.at[idx, 'haslo'] = n_pass
            df_up.at[idx, orig_col] = n_status
            df_up.at[idx, 'data_konca'] = n_end
            df_up.at[idx, 'kwota_subskrypcji'] = n_price
            
            conn.update(data=df_up)
            st.success("Zapisano zmiany.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. NOWY KLIENT
# =========================================================
elif choice == "➕ NOWY KLIENT":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("DODAWANIE NOWEJ INSTANCJI")
    with st.form("new_form"):
        f = st.text_input("FIRMA ID")
        u = st.text_input("USER ID")
        h = st.text_input("HASŁO")
        d = st.date_input("DATA KOŃCA")
        k = st.number_input("KWOTA", value=250.0)

        if st.form_submit_button("DODAJ DO SYSTEMU"):
            new_r = {
                "firma_id": f, "uzytkownik_id": u, "haslo": h,
                "data_konca": str(d), "kwota_subskrypcji": k,
                "status_aktywny": True, "data_startu": datetime.now().strftime("%Y-%m-%d")
            }
            final_df = pd.concat([data.drop(columns=['display_name', 'STATUS_AKT']), pd.DataFrame([new_r])], ignore_index=True)
            conn.update(data=final_df)
            st.success("Dodano klienta.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
