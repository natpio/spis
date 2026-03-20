import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# =========================================================
# 1. KONFIGURACJA STRONY I STYLIZACJA VORTEZA
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER ADMIN", layout="wide")

st.markdown("""
    <style>
    /* Ciemne tło i czerwone akcenty */
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #ff4b4b; }
    
    /* Nagłówek w stylu pozostałych aplikacji */
    .vorteza-header {
        color: #ff4b4b;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 2px solid #ff4b4b;
        padding-bottom: 10px;
        margin-bottom: 25px;
    }
    
    /* Przyciski */
    .stButton>button {
        width: 100%;
        background-color: #ff4b4b;
        color: white;
        border-radius: 5px;
        font-weight: bold;
        border: none;
    }
    
    /* Poprawa czytelności tabeli */
    [data-testid="stTable"] {
        background-color: #161a25;
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 class='vorteza-header'>VORTEZA - CENTRUM ZARZĄDZANIA</h1>", unsafe_allow_html=True)

# =========================================================
# 2. POŁĄCZENIE Z BAZĄ (GOOGLE SHEETS)
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=0 zapewnia pobieranie danych na żywo bez buforowania
    df = conn.read(ttl=0)
    
    # Czyszczenie nazw kolumn (usuwanie spacji)
    df.columns = [c.strip() for c in df.columns]
    
    # Tworzenie identyfikatora do list wyboru
    df['display_name'] = df['firma_id'].astype(str) + " | " + df['uzytkownik_id'].astype(str)
    return df

try:
    data = load_data()
except Exception as e:
    st.error(f"Błąd połączenia z arkuszem: {e}")
    st.stop()

# =========================================================
# 3. MENU BOCZNE
# =========================================================
st.sidebar.title("PANEL STEROWANIA")
menu = ["📊 Dashboard i Finanse", "🔧 Zarządzanie Kontami", "➕ Dodaj Nowy Wpis"]
choice = st.sidebar.selectbox("Wybierz sekcję:", menu)

# =========================================================
# 4. DASHBOARD I FINANSE (CZYSTY WIDOK)
# =========================================================
if choice == "📊 Dashboard i Finanse":
    st.subheader("PODSUMOWANIE PORTFELA")
    
    today = datetime.now().date()
    
    # Obliczenia
    active_mask = data['status_aktywny'] == True
    total_rev = data[active_mask]['kwota_subskrypcji'].sum()
    active_count = data[active_mask].shape[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("PRZYCHÓD MIESIĘCZNY", f"{total_rev:,.2f} PLN")
    col2.metric("AKTYWNE USŁUGI", active_count)
    col3.metric("WSZYSTKIE KONTA", len(data))

    st.markdown("---")
    st.write("### 📋 Status Klientów")

    # Przygotowanie tabeli do wyświetlenia (tylko kluczowe dane)
    # Usuwamy techniczne kolumny, żeby nie robić tłoku
    view_df = data[['firma_id', 'uzytkownik_id', 'status_aktywny', 'data_konca', 'kwota_subskrypcji']].copy()

    def style_rows(df):
        def apply_logic(row):
            styles = [''] * len(row)
            try:
                # Konwersja daty do porównania
                end_dt = pd.to_datetime(row['data_konca']).date()
                if not row['status_aktywny']:
                    return ['background-color: #3d0000; color: #ff9999'] * len(row) # ZABLOKOWANY
                if end_dt < today:
                    return ['background-color: #4d3d00; color: #ffeb99'] * len(row) # WYGASŁY
            except:
                pass
            return styles
        return df.style.apply(apply_logic, axis=1).format({'kwota_subskrypcji': '{:.2f} PLN'})

    st.table(style_rows(view_df))
    
    st.info("💡 Legenda: Czerwony = Brak dostępu | Żółty = Subskrypcja wygasła | Czarny = OK")

# =========================================================
# 5. ZARZĄDZANIE KONTAMI (EDYCJA)
# =========================================================
elif choice == "🔧 Zarządzanie Kontami":
    st.subheader("EDYCJA PARAMETRÓW KLIENTA")
    
    selected = st.selectbox("Wybierz konto do modyfikacji:", data['display_name'].tolist())
    idx = data[data['display_name'] == selected].index[0]
    row = data.loc[idx]

    with st.form("edit_form"):
        st.markdown(f"Edytujesz: **{selected}**")
        c1, c2 = st.columns(2)
        
        with c1:
            n_pass = st.text_input("Hasło", value=str(row['haslo']))
            n_status = st.checkbox("Status Aktywny", value=bool(row['status_aktywny']))
            n_url = st.text_input("URL Aplikacji", value=str(row.get('url_aplikacji', '')))
            n_app_id = st.text_input("Aplikacja ID", value=str(row.get('aplikacja_id', '')))
            
        with c2:
            n_start = st.text_input("Data Startu (RRRR-MM-DD)", value=str(row['data_startu']))
            n_end = st.text_input("Data Końca (RRRR-MM-DD)", value=str(row['data_konca']))
            n_price = st.number_input("Cena (PLN)", value=float(row['kwota_subskrypcji']))

        if st.form_submit_button("ZAPISZ ZMIANY W GOOGLE SHEETS"):
            df_update = data.copy().drop(columns=['display_name'])
            # Aktualizacja wartości
            df_update.at[idx, 'haslo'] = n_pass
            df_update.at[idx, 'status_aktywny'] = n_status
            df_update.at[idx, 'url_aplikacji'] = n_url
            df_update.at[idx, 'aplikacja_id'] = n_app_id
            df_update.at[idx, 'data_startu'] = n_start
            df_update.at[idx, 'data_konca'] = n_end
            df_update.at[idx, 'kwota_subskrypcji'] = n_price
            
            conn.update(data=df_update)
            st.success("Baza została zaktualizowana!")
            st.rerun()

# =========================================================
# 6. DODAWANIE NOWEGO WPISU
# =========================================================
elif choice == "➕ Dodaj Nowy Wpis":
    st.subheader("REJESTRACJA NOWEJ FIRMY / KONTA")
    
    with st.form("add_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            f_id = st.text_input("Firma ID (np. PEPEL)")
            u_id = st.text_input("Użytkownik ID (np. admin)")
            h_id = st.text_input("Hasło dostępu")
            a_id = st.text_input("Aplikacja ID (np. vortezaflowpepel)")
            
        with col_b:
            url_id = st.text_input("URL Aplikacji")
            d_s = st.date_input("Data Startu")
            d_e = st.date_input("Data Końca")
            price = st.number_input("Cena miesięczna", value=250.0)
            
        if st.form_submit_button("DODAJ KLIENTA"):
            if f_id and u_id and h_id:
                new_data = {
                    "firma_id": f_id, "uzytkownik_id": u_id, "haslo": h_id,
                    "aplikacja_id": a_id, "url_aplikacji": url_id,
                    "data_startu": str(d_s), "data_konca": str(d_e),
                    "kwota_subskrypcji": price, "status_aktywny": True
                }
                
                final_df = pd.concat([data.drop(columns=['display_name']), pd.DataFrame([new_data])], ignore_index=True)
                conn.update(data=final_df)
                st.success("Nowy klient został dodany do bazy!")
                st.rerun()
            else:
                st.warning("Pola Firma, Użytkownik i Hasło są obowiązkowe!")
