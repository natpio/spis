import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import base64
from PIL import Image

# =========================================================
# 1. KONFIGURACJA I STYLIZACJA VORTEZA MASTER
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER | CENTRAL", layout="wide")

def apply_vorteza_theme():
    # Czysty CSS dopasowany do Twoich poprzednich systemów
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700&display=swap');

            :root {
                --v-copper: #B58863;
                --v-dark: #0E0E0E;
                --v-panel: rgba(20, 20, 20, 0.95);
            }

            .stApp {
                background-color: var(--v-dark);
                color: #E0E0E0;
                font-family: 'Montserrat', sans-serif;
            }

            h1, h2, h3 {
                color: var(--v-copper) !important;
                font-weight: 700 !important;
                text-transform: uppercase;
                letter-spacing: 2px;
            }

            .vorteza-card {
                background-color: var(--v-panel);
                padding: 25px;
                border-radius: 5px;
                border-left: 5px solid var(--v-copper);
                box-shadow: 0 10px 40px rgba(0,0,0,0.8);
                margin-bottom: 25px;
            }

            /* Stylizacja metryk */
            [data-testid="stMetricValue"] {
                color: var(--v-copper) !important;
                font-weight: 700 !important;
            }
            
            /* Przycisk VORTEZA */
            .stButton > button {
                background-color: transparent;
                color: var(--v-copper);
                border: 1px solid var(--v-copper);
                padding: 10px 20px;
                font-weight: 700;
                text-transform: uppercase;
                width: 100%;
                transition: 0.3s;
            }
            .stButton > button:hover {
                background-color: var(--v-copper);
                color: black;
            }
        </style>
    """, unsafe_allow_html=True)

apply_vorteza_theme()

# =========================================================
# 2. KOMUNIKACJA Z BAZĄ DANYCH (GOOGLE SHEETS)
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Pobranie danych w czasie rzeczywistym
    df = conn.read(ttl=0)
    
    # Naprawa nagłówków (usuwanie spacji, literówek)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Inteligentne wykrywanie kolumny statusu
    status_col = next((c for c in df.columns if 'status' in c.lower() or 'aktyw' in c.lower()), 'status_aktywny')
    df.rename(columns={status_col: 'AKTYWNY'}, inplace=True)
    
    # Konwersja daty na obiekt datetime dla poprawnego sortowania
    df['data_konca'] = pd.to_datetime(df['data_konca']).dt.date
    
    # Tworzenie nazwy wyświetlanej do edycji
    df['display_name'] = df['firma_id'].astype(str) + " | " + df['uzytkownik_id'].astype(str)
    return df

try:
    data = load_data()
except Exception as e:
    st.error(f"KRYTYCZNY BŁĄD BAZY: {e}")
    st.stop()

# =========================================================
# 3. INTERFEJS GŁÓWNY
# =========================================================
st.title("VORTEZA MASTER OPS")

menu = ["📊 DASHBOARD", "🔧 ZARZĄDZANIE", "➕ NOWA INSTANCJA"]
choice = st.sidebar.selectbox("MENU SYSTEMU", menu)

# --- DASHBOARD ---
if choice == "📊 DASHBOARD":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("ANALIZA FINANSOWA I OPERACYJNA")
    
    active_mask = data['AKTYWNY'] == True
    total_rev = data[active_mask]['kwota_subskrypcji'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("PRZYCHÓD MIESIĘCZNY", f"{total_rev:,.2f} PLN")
    m2.metric("AKTYWNE SYSTEMY", len(data[active_mask]))
    m3.metric("ŁĄCZNIE INSTANCJI", len(data))
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("MONITORING SUBSKRYPCJI")

    # NATYWNA TABELA VORTEZA - ODPORNA NA BŁĘDY RENDEROWANIA
    st.dataframe(
        data[['firma_id', 'uzytkownik_id', 'AKTYWNY', 'data_konca', 'kwota_subskrypcji']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "firma_id": st.column_config.TextColumn("FIRMA"),
            "uzytkownik_id": st.column_config.TextColumn("UŻYTKOWNIK"),
            "AKTYWNY": st.column_config.CheckboxColumn("STATUS"),
            "data_konca": st.column_config.DateColumn("TERMIN WYGASANIA", format="DD.MM.YYYY"),
            "kwota_subskrypcji": st.column_config.NumberColumn("STAWKA", format="%.2f PLN"),
        }
    )

# --- ZARZĄDZANIE (EDYCJA) ---
elif choice == "🔧 ZARZĄDZANIE":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("MODYFIKACJA PARAMETRÓW DOSTĘPU")
    
    selected = st.selectbox("Wybierz klienta do modyfikacji:", data['display_name'].tolist())
    idx = data[data['display_name'] == selected].index[0]
    row = data.loc[idx]

    with st.form("edit_vorteza"):
        c1, c2 = st.columns(2)
        with c1:
            n_pass = st.text_input("Klucz Systemowy (Hasło)", value=str(row['haslo']))
            n_status = st.checkbox("Dostęp Aktywny", value=bool(row['AKTYWNY']))
            n_app_id = st.text_input("Aplikacja ID", value=str(row.get('aplikacja_id', '')))
        with c2:
            n_end = st.date_input("Nowy termin wygasania", value=row['data_konca'])
            n_price = st.number_input("Stawka Miesięczna", value=float(row['kwota_subskrypcji']))
            n_url = st.text_input("URL Systemu", value=str(row.get('url_aplikacji', '')))
            
        if st.form_submit_button("ZAKTUALIZUJ RDZEŃ BAZY"):
            # Przygotowanie kopii do wysyłki
            df_up = data.copy().drop(columns=['display_name', 'AKTYWNY'])
            
            # Przywrócenie oryginalnej nazwy kolumny dla Sheets
            real_col = next((c for c in data.columns if 'status' in c.lower() or 'aktyw' in c.lower()), 'status_aktywny')
            df_up[real_col] = data['AKTYWNY']
            
            # Wpisanie nowych wartości
            df_up.at[idx, 'haslo'] = n_pass
            df_up.at[idx, real_col] = n_status
            df_up.at[idx, 'data_konca'] = str(n_end)
            df_up.at[idx, 'kwota_subskrypcji'] = n_price
            df_up.at[idx, 'url_aplikacji'] = n_url
            df_up.at[idx, 'aplikacja_id'] = n_app_id
            
            conn.update(data=df_up)
            st.success("ZMIANY ZAPISANE W CHMURZE")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- NOWY KLIENT ---
elif choice == "➕ NOWA INSTANCJA":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("REJESTRACJA NOWEGO KLIENTA W SYSTEMIE")
    with st.form("new_client"):
        cc1, cc2 = st.columns(2)
        with cc1:
            f = st.text_input("FIRMA ID (np. LOG-TRANS)")
            u = st.text_input("USER ID (np. ADMIN-1)")
            h = st.text_input("HASŁO DOSTĘPU")
        with cc2:
            aid = st.text_input("ID APLIKACJI (np. FLOW)")
            d_k = st.date_input("DATA KOŃCA SUBSKRYPCJI")
            kw = st.number_input("KWOTA (PLN)", value=250.0)

        if st.form_submit_button("UTWÓRZ PROFIL KLIENTA"):
            if f and u:
                new_r = {
                    "firma_id": f, "uzytkownik_id": u, "haslo": h, "aplikacja_id": aid,
                    "data_startu": datetime.now().strftime("%Y-%m-%d"),
                    "data_konca": str(d_k), "kwota_subskrypcji": kw, 
                    "status_aktywny": True, "url_aplikacji": ""
                }
                # Połączenie danych i wysyłka
                final_df = pd.concat([data.drop(columns=['display_name', 'AKTYWNY']), pd.DataFrame([new_r])], ignore_index=True)
                conn.update(data=final_df)
                st.success(f"PROFIL {f} DODANY DO BAZY")
                st.rerun()
            else:
                st.error("FIRMA ID i USER ID są wymagane!")
    st.markdown('</div>', unsafe_allow_html=True)
