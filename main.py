import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# =========================================================
# 1. KONFIGURACJA STRONY I STYLIZACJA (STYL VORTEZA)
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER ADMIN", layout="wide")

# Wstrzyknięcie CSS dla zachowania spójności z innymi aplikacjami
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #ff4b4b; }
    div[data-testid="stExpander"] { border: 1px solid #333; background-color: #161a25; }
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
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 class='vorteza-header'>VORTEZA - CENTRUM ZARZĄDZANIA</h1>", unsafe_allow_html=True)

# =========================================================
# 2. POŁĄCZENIE Z BAZĄ GOOGLE SHEETS
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Pobieramy dane z arkusza (ttl=0 zapewnia brak opóźnień w odświeżaniu)
    df = conn.read(ttl=0)
    # Tworzymy unikalną nazwę wyświetlaną, aby rozróżnić użytkowników o tych samych loginach
    if not df.empty:
        df['display_name'] = df['klient_id'].astype(str) + " | " + df['uzytkownik_id'].astype(str)
    return df

data = load_data()

# =========================================================
# 3. MENU BOCZNE
# =========================================================
st.sidebar.image("https://www.sqm.pl/wp-content/uploads/2021/03/logo-sqm-white.png", width=150) # Przykładowe logo
menu = ["📊 Dashboard Finansowy", "🔧 Zarządzanie Kontami", "➕ Dodaj Nowego Klienta"]
choice = st.sidebar.selectbox("NAWIGACJA", menu)

# =========================================================
# 4. DASHBOARD FINANSOWY
# =========================================================
if choice == "📊 Dashboard Finansowy":
    st.subheader("STATUS SUBSKRYPCJI I PRZYCHODY")
    
    if data is not None and not data.empty:
        # Statystyki na górze
        col1, col2, col3 = st.columns(3)
        total_active = data[data['status_aktywny'] == True].shape[0]
        total_revenue = data[data['status_aktywny'] == True]['kwota_subskrypcji'].sum()
        
        col1.metric("AKTYWNE KONTA", total_active)
        col2.metric("SUMA MIESIĘCZNA", f"{total_revenue:,.2f} PLN")
        col3.metric("WSZYSTKIE WPISY", len(data))

        st.markdown("---")
        # Tabela z kolorowaniem aktywnych statusów
        def color_status(val):
            color = '#2ecc71' if val == True else '#e74c3c'
            return f'color: {color}; font-weight: bold'

        view_df = data[['klient_id', 'uzytkownik_id', 'status_aktywny', 'kwota_subskrypcji', 'data_konca']]
        st.dataframe(view_df.style.applymap(color_status, subset=['status_aktywny']), use_container_width=True)
    else:
        st.warning("Baza danych jest pusta.")

# =========================================================
# 5. ZARZĄDZANIE KONTAMI (EDYCJA I BLOKOWANIE)
# =========================================================
elif choice == "🔧 Zarządzanie Kontami":
    st.subheader("EDYCJA UPRAWNIEŃ I PŁATNOŚCI")
    
    if not data.empty:
        selected_user = st.selectbox("Wybierz konto do modyfikacji", data['display_name'].tolist())
        
        # Pobranie indeksu i danych konkretnego wiersza
        idx = data[data['display_name'] == selected_user].index[0]
        row = data.loc[idx]

        with st.form("edit_user_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.info(f"Firma: {row['klient_id']}")
                st.info(f"Login: {row['uzytkownik_id']}")
                new_pass = st.text_input("Hasło (widoczne dla admina)", value=str(row['haslo']))
                new_status = st.checkbox("DOSTĘP AKTYWNY", value=bool(row['status_aktywny']))
            
            with col_b:
                new_price = st.number_input("Kwota subskrypcji (PLN)", value=float(row['kwota_subskrypcji']))
                new_date = st.text_input("Data wygaśnięcia (RRRR-MM-DD)", value=str(row['data_konca']))
                st.write("---")
                save = st.form_submit_button("ZAPISZ ZMIANY W BAZIE")

            if save:
                # Kopia danych do zapisu (usuwamy kolumnę pomocniczą)
                df_to_save = data.copy().drop(columns=['display_name'])
                df_to_save.at[idx, 'haslo'] = new_pass
                df_to_save.at[idx, 'status_aktywny'] = new_status
                df_to_save.at[idx, 'kwota_subskrypcji'] = new_price
                df_to_save.at[idx, 'data_konca'] = new_date
                
                conn.update(data=df_to_save)
                st.success(f"Zaktualizowano dane dla: {selected_user}")
                st.rerun()
    else:
        st.error("Brak danych do edycji.")

# =========================================================
# 6. DODAWANIE NOWEGO KLIENTA
# =========================================================
elif choice == "➕ Dodaj Nowego Klienta":
    st.subheader("REJESTRACJA NOWEGO KONTA W SYSTEMIE")
    
    with st.form("add_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_klient = st.selectbox("Wybierz Firmę", ["PEPEL", "PREMIUM", "INNA"])
            if new_klient == "INNA":
                new_klient = st.text_input("Wpisz nazwę nowej firmy")
            new_user = st.text_input("Login użytkownika (np. admin, biuro)")
            new_pass = st.text_input("Hasło startowe")
        with c2:
            new_price = st.number_input("Cena subskrypcji", min_value=0.0, value=250.0)
            new_date = st.date_input("Data końca subskrypcji")
            new_active = st.checkbox("Aktywuj natychmiast", value=True)
            
        submit_new = st.form_submit_button("DODAJ DO BAZY")
        
        if submit_new:
            if new_klient and new_user and new_pass:
                new_row = {
                    "klient_id": new_klient,
                    "uzytkownik_id": new_user,
                    "haslo": new_pass,
                    "status_aktywny": new_active,
                    "kwota_subskrypcji": new_price,
                    "data_konca": new_date.strftime("%Y-%m-%d")
                }
                
                # Dodajemy nowy wiersz do istniejących danych
                df_to_save = data.copy().drop(columns=['display_name'])
                df_to_save = pd.concat([df_to_save, pd.DataFrame([new_row])], ignore_index=True)
                
                conn.update(data=df_to_save)
                st.success(f"Dodano użytkownika {new_user} do firmy {new_klient}!")
                st.rerun()
            else:
                st.warning("Wypełnij wszystkie pola!")
