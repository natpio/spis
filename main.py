import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="Master Admin Panel", layout="wide")

st.title("🎛️ Panel Zarządzania Subskrypcjami i Dostępem")

# Nawiązanie połączenia z Twoim arkuszem Google
# Wykorzystuje dane wprowadzone w Streamlit Cloud Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=0 zapewnia, że przy każdym odświeżeniu pobieramy najświeższe dane z arkusza
    return conn.read(ttl=0)

# Pobieramy aktualne dane
data = load_data()

# Menu boczne
menu = ["Podgląd Klientów", "Dodaj Nowego Klienta", "Zarządzaj Dostępem"]
choice = st.sidebar.selectbox("Menu", menu)

# --- 1. PODGLĄD KLIENTÓW ---
if choice == "Podgląd Klientów":
    st.subheader("Lista wszystkich współprac i płatności")
    
    if data is not None and not data.empty:
        # Wyświetlamy tabelę z danymi
        st.dataframe(data, use_container_width=True)
        
        # Szybkie podsumowanie finansowe (tylko dla aktywnych kont)
        if 'status_aktywny' in data.columns and 'kwota_subskrypcji' in data.columns:
            # Konwersja na liczby na wypadek, gdyby arkusz traktował to jako tekst
            data['kwota_subskrypcji'] = pd.to_numeric(data['kwota_subskrypcji'], errors='coerce').fillna(0)
            active_revenue = data[data['status_aktywny'] == True]['kwota_subskrypcji'].sum()
            st.metric("Suma aktywnych subskrypcji (miesięcznie)", f"{active_revenue} PLN")
    else:
        st.info("Twój arkusz Google jest pusty. Dodaj pierwszego klienta w menu obok.")

# --- 2. DODAJ NOWEGO KLIENTA ---
elif choice == "Dodaj Nowego Klienta":
    st.subheader("Rejestracja nowego klienta w systemie")
    
    with st.form("add_form", clear_on_submit=True):
        new_client = st.text_input("Nazwa Klienta (np. Firma X)")
        new_url = st.text_input("URL Aplikacji (Streamlit URL)")
        new_pass = st.text_input("Hasło dla klienta", type="default")
        new_date = st.date_input("Data rozpoczęcia współpracy", datetime.now())
        new_amount = st.number_input("Kwota subskrypcji (PLN)", min_value=0, step=10)
        
        submit = st.form_submit_button("Zapisz klienta w bazie")
        
        if submit:
            if new_client and new_pass:
                # Tworzymy nowy wiersz
                new_row = pd.DataFrame([{
                    "klient_id": new_client,
                    "url_aplikacji": new_url,
                    "haslo": new_pass,
                    "data_startu": new_date.strftime("%Y-%m-%d"),
                    "kwota_subskrypcji": new_amount,
                    "status_aktywny": True
                }])
                
                # Łączymy ze starymi danymi i wysyłamy do Google Sheets
                updated_df = pd.concat([data, new_row], ignore_index=True)
                conn.update(data=updated_df)
                
                st.success(f"Pomyślnie dodano klienta: {new_client}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Nazwa klienta i hasło są wymagane!")

# --- 3. ZARZĄDZAJ DOSTĘPEM ---
elif choice == "Zarządzaj Dostępem":
    st.subheader("Zmiana haseł i blokowanie kont")
    
    if data is not None and not data.empty:
        client_list = data['klient_id'].tolist()
        selected_client = st.selectbox("Wybierz klienta do edycji", client_list)
        
        # Znajdujemy indeks wybranego klienta
        client_idx = data[data['klient_id'] == selected_client].index[0]
        
        with st.form("edit_form"):
            st.write(f"Edytujesz: **{selected_client}**")
            
            # Pobieramy obecne wartości, żeby formularz nie był pusty
            curr_pass = st.text_input("Hasło", value=str(data.at[client_idx, 'haslo']))
            curr_status = st.checkbox("Konto Aktywne (odznacz, aby zablokować)", value=bool(data.at[client_idx, 'status_aktywny']))
            curr_amount = st.number_input("Kwota subskrypcji", value=float(data.at[client_idx, 'kwota_subskrypcji']))
            
            save_changes = st.form_submit_button("Zastosuj zmiany")
            
            if save_changes:
                # Aktualizujemy dataframe
                data.at[client_idx, 'haslo'] = curr_pass
                data.at[client_idx, 'status_aktywny'] = curr_status
                data.at[client_idx, 'kwota_subskrypcji'] = curr_amount
                
                # Wysyłamy całość do arkusza
                conn.update(data=data)
                
                st.success(f"Zaktualizowano dane dla {selected_client}")
                st.cache_data.clear()
                st.rerun()
    else:
        st.warning("Brak klientów w bazie do edycji.")
