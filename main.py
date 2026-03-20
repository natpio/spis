import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# =========================================================
# 1. KONFIGURACJA I STYLIZACJA (STYL VORTEZA)
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER ADMIN", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #ff4b4b; }
    .vorteza-header {
        color: #ff4b4b;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 2px solid #ff4b4b;
        padding-bottom: 10px;
        margin-bottom: 25px;
    }
    .stButton>button {
        width: 100%;
        background-color: #ff4b4b;
        color: white;
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 class='vorteza-header'>VORTEZA - CENTRUM ZARZĄDZANIA</h1>", unsafe_allow_html=True)

# =========================================================
# 2. POŁĄCZENIE I POBIERANIE DANYCH
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl=0)
    
    # Sprawdzenie czy wymagane kolumny istnieją (zgodnie z Twoim zrzutem)
    required = ['firma_id', 'uzytkownik_id', 'haslo', 'data_startu', 'data_konca', 'kwota_subskrypcji', 'status_aktywny']
    for col in required:
        if col not in df.columns:
            st.error(f"BRAK KOLUMNY: {col}. Sprawdź nagłówki w Google Sheets!")
            st.stop()
            
    # Tworzymy nazwę do wyboru w menu (Firma + User)
    df['display_name'] = df['firma_id'].astype(str) + " | " + df['uzytkownik_id'].astype(str)
    return df

data = load_data()

# =========================================================
# 3. MENU BOCZNE
# =========================================================
st.sidebar.title("VORTEZA ADMIN")
menu = ["📊 Dashboard Finansowy", "🔧 Zarządzanie Kontami", "➕ Dodaj Nowy Wpis"]
choice = st.sidebar.selectbox("NAWIGACJA", menu)

# =========================================================
# 4. DASHBOARD FINANSOWY
# =========================================================
if choice == "📊 Dashboard Finansowy":
    st.subheader("BIEŻĄCY STATUS BIZNESU")
    
    today = datetime.now().date()
    
    # Przeliczanie danych
    total_revenue = data[data['status_aktywny'] == True]['kwota_subskrypcji'].sum()
    active_accounts = data[data['status_aktywny'] == True].shape[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("MIESIĘCZNY PRZYCHÓD", f"{total_revenue:,.2f} PLN")
    col2.metric("AKTYWNE SUBSKRYPCJE", active_accounts)
    col3.metric("WSZYSTKIE KONTA", len(data))

    st.markdown("---")
    
    # Wyświetlanie tabeli z podświetleniem wygasających
    st.write("### Lista wszystkich kont")
    
    def highlight_expired(row):
        try:
            end_date = pd.to_datetime(row['data_konca']).date()
            if end_date < today and row['status_aktywny']:
                return ['background-color: #4b0000'] * len(row) # Ciemna czerwień dla wygasłych
        except:
            pass
        return [''] * len(row)

    st.dataframe(data.style.apply(highlight_expired, axis=1), use_container_width=True)

# =========================================================
# 5. ZARZĄDZANIE KONTAMI
# =========================================================
elif choice == "🔧 Zarządzanie Kontami":
    st.subheader("MODYFIKACJA KLIENTA")
    
    user_to_edit = st.selectbox("Wybierz konto do edycji", data['display_name'].tolist())
    idx = data[data['display_name'] == user_to_edit].index[0]
    row = data.loc[idx]

    with st.form("edit_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Dane Podstawowe**")
            new_firma = st.text_input("Firma ID", value=row['firma_id'])
            new_user = st.text_input("Użytkownik ID", value=row['uzytkownik_id'])
            new_pass = st.text_input("Hasło", value=row['haslo'])
            new_app = st.text_input("Aplikacja ID", value=row.get('aplikacja_id', ''))
        
        with c2:
            st.markdown("**Terminy i Płatności**")
            new_start = st.text_input("Data Startu (RRRR-MM-DD)", value=str(row['data_startu']))
            new_end = st.text_input("Data Końca (RRRR-MM-DD)", value=str(row['data_konca']))
            new_price = st.number_input("Kwota Subskrypcji", value=float(row['kwota_subskrypcji']))
        
        with c3:
            st.markdown("**Dostęp**")
            new_url = st.text_input("URL Aplikacji", value=row.get('url_aplikacji', ''))
            new_status = st.checkbox("STATUS AKTYWNY", value=bool(row['status_aktywny']))
            st.write("---")
            save = st.form_submit_button("ZAPISZ ZMIANY")

        if save:
            df_save = data.copy().drop(columns=['display_name'])
            df_save.at[idx, 'firma_id'] = new_firma
            df_save.at[idx, 'uzytkownik_id'] = new_user
            df_save.at[idx, 'haslo'] = new_pass
            df_save.at[idx, 'aplikacja_id'] = new_app
            df_save.at[idx, 'data_startu'] = new_start
            df_save.at[idx, 'data_konca'] = new_end
            df_save.at[idx, 'kwota_subskrypcji'] = new_price
            df_save.at[idx, 'url_aplikacji'] = new_url
            df_save.at[idx, 'status_aktywny'] = new_status
            
            conn.update(data=df_save)
            st.success("Zaktualizowano pomyślnie!")
            st.rerun()

# =========================================================
# 6. DODAWANIE NOWEGO WPISU
# =========================================================
elif choice == "➕ Dodaj Nowy Wpis":
    st.subheader("REJESTRACJA NOWEJ USŁUGI")
    
    with st.form("add_form"):
        col_left, col_right = st.columns(2)
        with col_left:
            a1 = st.text_input("Firma ID (np. PEPEL)")
            a2 = st.text_input("Użytkownik ID (np. admin)")
            a3 = st.text_input("Hasło")
            a4 = st.text_input("Aplikacja ID (np. vortezaflowpepel)")
        with col_right:
            a5 = st.text_input("URL Aplikacji")
            a6 = st.date_input("Data Startu")
            a7 = st.date_input("Data Końca")
            a8 = st.number_input("Kwota Subskrypcji", value=250.0)
            a9 = st.checkbox("Aktywuj od razu", value=True)
            
        if st.form_submit_button("DODAJ DO SYSTEMU"):
            if a1 and a2 and a3:
                new_row = {
                    "firma_id": a1, "uzytkownik_id": a2, "haslo": a3,
                    "aplikacja_id": a4, "url_aplikacji": a5,
                    "data_startu": str(a6), "data_konca": str(a7),
                    "kwota_subskrypcji": a8, "status_aktywny": a9
                }
                df_final = pd.concat([data.drop(columns=['display_name']), pd.DataFrame([new_row])], ignore_index=True)
                conn.update(data=df_final)
                st.success("Nowe konto zostało utworzone!")
                st.rerun()
            else:
                st.warning("Pola Firma, Użytkownik i Hasło są wymagane!")
