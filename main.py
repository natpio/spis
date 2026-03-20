import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import base64
from PIL import Image

# =========================================================
# 1. KONFIGURACJA STRONY I STYLE (VORTEZA DESIGN)
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER", layout="wide")

def apply_vorteza_theme():
    # Stylizacja interfejsu bez użycia tabel HTML w treści
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700&display=swap');
            
            :root {
                --v-copper: #B58863;
                --v-dark: #0E0E0E;
                --v-panel: rgba(25, 25, 25, 0.9);
            }

            .stApp {
                background-color: var(--v-dark);
                color: #E0E0E0;
                font-family: 'Montserrat', sans-serif;
            }

            .vorteza-card {
                background-color: var(--v-panel);
                padding: 20px;
                border-radius: 4px;
                border-left: 4px solid var(--v-copper);
                margin-bottom: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            }

            h1, h2, h3 {
                color: var(--v-copper) !important;
                text-transform: uppercase;
                letter-spacing: 2px;
            }

            /* Stylizacja przycisków */
            .stButton > button {
                background-color: transparent;
                color: var(--v-copper);
                border: 1px solid var(--v-copper);
                width: 100%;
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
# 2. LOGIKA DANYCH (GOOGLE SHEETS)
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_clean_data():
    # Pobranie danych
    df = conn.read(ttl=0)
    
    # Czyszczenie nazw kolumn (usuwanie spacji, nowych linii, małe litery dla stabilności)
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    # Inteligentne mapowanie kolumny statusu
    # Szukamy kolumny która zawiera 'status' lub 'aktyw'
    status_col = None
    for col in df.columns:
        if 'status' in col or 'aktyw' in col:
            status_col = col
            break
    
    if status_col:
        df.rename(columns={status_col: 'status_bool'}, inplace=True)
    else:
        df['status_bool'] = True # Fail-safe
        
    # Tworzenie identyfikatora do list wyboru
    df['display_name'] = df['firma_id'].astype(str) + " | " + df['uzytkownik_id'].astype(str)
    return df

try:
    data = load_clean_data()
except Exception as e:
    st.error(f"Błąd połączenia z bazą: {e}")
    st.stop()

# =========================================================
# 3. NAWIGACJA
# =========================================================
st.sidebar.title("VORTEZA OPS")
menu = ["📊 DASHBOARD", "🔧 ZARZĄDZANIE", "➕ NOWY KLIENT"]
choice = st.sidebar.selectbox("MENU", menu)

# =========================================================
# 4. DASHBOARD (ROZWIĄZANIE PROBLEMU FORMATOWANIA)
# =========================================================
if choice == "📊 DASHBOARD":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("STATUS SYSTEMÓW")
    
    # Statystyki
    active_mask = data['status_bool'] == True
    total_rev = data[active_mask]['kwota_subskrypcji'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("MIESIĘCZNY PRZYCHÓD", f"{total_rev:,.2f} PLN")
    m2.metric("AKTYWNE INSTANCJE", len(data[active_mask]))
    m3.metric("WSZYSCY KLIENCI", len(data))
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("LISTA MONITOROWANIA")

    # Przygotowanie danych do wyświetlenia (tylko kluczowe kolumny)
    display_df = data[['firma_id', 'uzytkownik_id', 'status_bool', 'data_konca', 'kwota_subskrypcji']].copy()
    
    # Funkcja stylowania Pandas (zamiast HTML)
    def highlight_expired(row):
        try:
            today = datetime.now().date()
            expiry = pd.to_datetime(row['data_konca']).date()
            if expiry < today and row['status_bool'] == True:
                return ['background-color: #4B0000; color: white'] * len(row)
        except:
            pass
        return [''] * len(row)

    # Renderowanie tabeli przez st.dataframe (odporne na błędy wyświetlania)
    styled_table = display_df.style.apply(highlight_expired, axis=1)\
        .format({'kwota_subskrypcji': "{:.2f} PLN"})\
        .set_properties(**{'text-align': 'left'})

    st.dataframe(
        styled_table, 
        use_container_width=True, 
        height=500,
        hide_index=True
    )

# =========================================================
# 5. ZARZĄDZANIE (EDYCJA)
# =========================================================
elif choice == "🔧 ZARZĄDZANIE":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("EDYCJA PARAMETRÓW DOSTĘPU")
    
    client = st.selectbox("Wybierz klienta:", data['display_name'].tolist())
    idx = data[data['display_name'] == client].index[0]
    row = data.loc[idx]

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_pass = st.text_input("Klucz (Hasło)", value=str(row['haslo']))
            new_status = st.checkbox("Dostęp Aktywny", value=bool(row['status_bool']))
            new_app_id = st.text_input("App ID", value=str(row.get('aplikacja_id', '')))
        with col2:
            new_end = st.text_input("Wygasa (RRRR-MM-DD)", value=str(row['data_konca']))
            new_price = st.number_input("Stawka", value=float(row['kwota_subskrypcji']))
            new_url = st.text_input("URL Systemu", value=str(row.get('url_aplikacji', '')))
            
        if st.form_submit_button("ZAPISZ ZMIANY W CHMURZE"):
            # Przygotowanie kopii do zapisu (powrót do oryginalnych nazw)
            df_save = data.copy().drop(columns=['display_name'])
            
            # Znajdujemy jak faktycznie nazywa się kolumna statusu w arkuszu
            real_status_col = [c for c in df_save.columns if 'status' in c or 'aktyw' in c][0]
            
            df_save.at[idx, 'haslo'] = new_pass
            df_save.at[idx, real_status_col] = new_status
            df_save.at[idx, 'data_konca'] = new_end
            df_save.at[idx, 'kwota_subskrypcji'] = new_price
            df_save.at[idx, 'url_aplikacji'] = new_url
            df_save.at[idx, 'aplikacja_id'] = new_app_id
            
            # Usunięcie kolumny 'status_bool' jeśli została stworzona jako alias
            if 'status_bool' in df_save.columns:
                df_save.drop(columns=['status_bool'], inplace=True)

            conn.update(data=df_save)
            st.success("Baza danych została zaktualizowana.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. REJESTRACJA
# =========================================================
elif choice == "➕ NOWY KLIENT":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("REJESTRACJA NOWEJ INSTANCJI")
    with st.form("new_client_form"):
        f_id = st.text_input("ID FIRMY")
        u_id = st.text_input("ID UŻYTKOWNIKA")
        pwd = st.text_input("HASŁO")
        end_d = st.date_input("TERMIN WAŻNOŚCI")
        price = st.number_input("KWOTA SUBSKRYPCJI", value=250.0)

        if st.form_submit_button("DODAJ KLIENTA"):
            new_row = {
                "firma_id": f_id, "uzytkownik_id": u_id, "haslo": pwd,
                "data_konca": str(end_d), "kwota_subskrypcji": price,
                "status_aktywny": True, "aplikacja_id": "VORTEZA_GEN",
                "data_startu": datetime.now().strftime("%Y-%m-%d")
            }
            # Usuwamy kolumny pomocnicze przed dodaniem
            clean_df = data.copy().drop(columns=['display_name', 'status_bool'], errors='ignore')
            final_df = pd.concat([clean_df, pd.DataFrame([new_row])], ignore_index=True)
            
            conn.update(data=final_df)
            st.success("Dodano pomyślnie.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
