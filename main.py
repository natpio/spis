import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import base64
from PIL import Image

# =========================================================
# 1. KONFIGURACJA SYSTEMU I STYL VORTEZA
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER OPS", layout="wide", initial_sidebar_state="expanded")

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

def load_logo(logo_path):
    try:
        logo = Image.open(logo_path)
        return logo
    except:
        return None

def apply_vorteza_theme():
    # Wczytanie tła
    bg_img_base64 = get_base64_of_bin_file('bg_vorteza.png')

    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700&display=swap');
            
            :root {{
                --v-copper: #B58863;
                --v-dark: #000000; /* Głęboka czerń */
                --v-panel: rgba(20, 20, 20, 0.98);
                --v-text: #E0E0E0;
            }}

            .stApp {{
                background-image: url("data:image/png;base64,{bg_img_base64}");
                background-size: cover;
                background-attachment: fixed;
                color: var(--v-text);
                font-family: 'Montserrat', sans-serif;
            }}
            
            [data-testid="stSidebar"] {{
                background-color: var(--v-dark) !important; /* Czarny pasek boczny */
                border-right: 1px solid #222;
            }}

            h1, h2, h3, .stSubheader {{
                color: var(--v-copper) !important;
                font-weight: 700 !important;
                text-transform: uppercase;
                letter-spacing: 3px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            }}

            .vorteza-card {{
                background: var(--v-panel);
                padding: 25px;
                border-radius: 4px;
                border-left: 5px solid var(--v-copper);
                box-shadow: 0 15px 35px rgba(0,0,0,0.7);
                backdrop-filter: blur(15px);
                margin-bottom: 25px;
            }}

            [data-testid="stMetricValue"] {{
                color: var(--v-copper) !important;
                font-size: 1.8rem !important;
                font-weight: 700 !important;
            }}

            .stButton > button {{
                background-color: transparent !important;
                color: var(--v-copper) !important;
                border: 1px solid var(--v-copper) !important;
                padding: 12px 24px !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                width: 100%;
                transition: all 0.3s ease;
            }}
            .stButton > button:hover {{
                background-color: var(--v-copper) !important;
                color: black !important;
                box-shadow: 0 0 15px var(--v-copper);
            }}
            
            div[data-baseweb="input"], input {{
                background-color: rgba(15, 15, 15, 0.9) !important;
                color: white !important;
                border: 1px solid #444 !important;
            }}
        </style>
    """, unsafe_allow_html=True)

apply_vorteza_theme()

# =========================================================
# 2. KOMUNIKACJA Z BAZĄ GOOGLE SHEETS
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_live_data():
    df = conn.read(ttl=0)
    # Czyszczenie i standaryzacja kolumn
    df.columns = [str(c).strip() for c in df.columns]
    # Szukamy kolumny statusu
    status_col = next((c for c in df.columns if 'status' in c.lower() or 'aktyw' in c.lower()), 'status_aktywny')
    df.rename(columns={status_col: 'STATUS_CORE'}, inplace=True)
    
    # Konwersja kwot
    df['kwota_subskrypcji'] = pd.to_numeric(df['kwota_subskrypcji'], errors='coerce').fillna(0)
    
    # Konwersja dat z obsługą pustych wartości (NaT) i naprawa błędu TypeError
    df['data_konca'] = pd.to_datetime(df['data_konca'], errors='coerce').dt.date
    
    df['display_name'] = df['firma_id'].astype(str) + " // " + df['uzytkownik_id'].astype(str)
    return df

try:
    data = get_live_data()
except Exception as e:
    st.error(f"KRYTYCZNY BŁĄD BAZY: {e}")
    st.stop()

# =========================================================
# 3. LOGIKA RENDEROWANIA TABELI (AWESOME TABLE)
# =========================================================
def render_vorteza_table(df):
    today = datetime.now().date()
    
    table_rows = ""
    for _, row in df.iterrows():
        is_active = bool(row['STATUS_CORE'])
        status_label = "AKTYWNY" if is_active else "BLOKADA"
        status_color = "#4CAF50" if is_active else "#F44336"
        
        # Sprawdzamy czy data_konca nie jest pusta (pd.notna) przed porównaniem
        row_bg = "transparent"
        expiry_val = row['data_konca']
        
        if pd.notna(expiry_val) and is_active:
            if expiry_val < today:
                row_bg = "rgba(244, 67, 54, 0.15)" # Czerwony alarm - wygasło
            elif (expiry_val - today).days <= 7:
                row_bg = "rgba(181, 136, 99, 0.1)" # Miedziany alert - kończy się za tydzień
        
        display_date = expiry_val if pd.notna(expiry_val) else "BRAK DATY"
        
        table_rows += f"""
        <tr style="background-color: {row_bg}; border-bottom: 1px solid #222;">
            <td style="padding: 15px; color: #fff; font-weight: bold;">{row['firma_id']}</td>
            <td style="padding: 15px; color: #AAA;">{row['uzytkownik_id']}</td>
            <td style="padding: 15px;">
                <span style="color: {status_color}; font-size: 0.75rem; font-weight: bold; border: 1px solid {status_color}; padding: 3px 8px; border-radius: 3px;">
                    {status_label}
                </span>
            </td>
            <td style="padding: 15px; color: #EEE;">{display_date}</td>
            <td style="padding: 15px; color: #B58863; font-weight: bold;">{row['kwota_subskrypcji']:.2f} PLN</td>
        </tr>
        """

    html_code = f"""
    <div style="font-family: 'Montserrat', sans-serif; background-color: transparent;">
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
                <tr style="border-bottom: 2px solid #B58863;">
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.75rem;">Firma</th>
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.75rem;">User</th>
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.75rem;">Status</th>
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.75rem;">Termin</th>
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.75rem;">Stawka</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """
    # Renderowanie jako komponent - to eliminuje błąd surowego tekstu
    components.html(html_code, height=500, scrolling=True)

# =========================================================
# 4. MODUŁY SYSTEMU
# =========================================================
# Wczytanie loga na pasku bocznym
logo = load_logo('logo_vorteza.png')
if logo:
    st.sidebar.image(logo, use_column_width=True)
else:
    st.sidebar.markdown("<h2 style='text-align:center; color:#B58863;'>VORTEZA</h2>", unsafe_allow_html=True) # Fallback

menu = ["📊 DASHBOARD", "⚙️ ZARZĄDZANIE", "➕ NOWY KLIENT"]
choice = st.sidebar.selectbox("NAWIGACJA", menu)

if choice == "📊 DASHBOARD":
    st.header("PANEL MONITORINGU")
    
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    active_mask = data['STATUS_CORE'] == True
    total_rev = data[active_mask]['kwota_subskrypcji'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("PRZYCHÓD MIESIĘCZNY", f"{total_rev:,.2f} PLN")
    c2.metric("AKTYWNE SYSTEMY", len(data[active_mask]))
    c3.metric("ŁĄCZNA BAZA", len(data))
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("LISTA OPERACYJNA")
    render_vorteza_table(data)

elif choice == "⚙️ ZARZĄDZANIE":
    st.header("EDYCJA DOSTĘPÓW")
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    
    target = st.selectbox("Wybierz instancję do modyfikacji:", data['display_name'].tolist())
    idx = data[data['display_name'] == target].index[0]
    row = data.loc[idx]

    with st.form("update_form"):
        col1, col2 = st.columns(2)
        with col1:
            u_pass = st.text_input("Hasło Dostępowe", value=str(row['haslo']))
            u_status = st.checkbox("Status Aktywny", value=bool(row['STATUS_CORE']))
            u_app = st.text_input("Aplikacja ID", value=str(row.get('aplikacja_id', '')))
        with col2:
            # Obsługa domyślnej daty w formularzu jeśli w bazie jest pusto
            def_date = row['data_konca'] if pd.notna(row['data_konca']) else datetime.now().date()
            u_date = st.date_input("Termin Ważności", value=def_date)
            u_price = st.number_input("Stawka", value=float(row['kwota_subskrypcji']))
        
        if st.form_submit_button("ZAKTUALIZUJ BAZĘ INWENTARZOWĄ"):
            df_up = data.copy().drop(columns=['display_name', 'STATUS_CORE'])
            # Szukamy oryginalnej nazwy kolumny w arkuszu
            orig_col = next((c for c in df_up.columns if 'status' in c.lower() or 'aktyw' in c.lower()), 'status_aktywny')
            
            df_up.at[idx, 'haslo'] = u_pass
            df_up.at[idx, orig_col] = u_status
            df_up.at[idx, 'data_konca'] = str(u_date)
            df_up.at[idx, 'kwota_subskrypcji'] = u_price
            df_up.at[idx, 'aplikacja_id'] = u_app
            
            conn.update(data=df_up)
            st.success("ZSYNCHRONIZOWANO Z GOOGLE SHEETS")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif choice == "➕ NOWY KLIENT":
    st.header("REJESTRACJA NOWEJ INSTANCJI")
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    with st.form("new_client"):
        f_id = st.text_input("ID FIRMY")
        u_id = st.text_input("ID UŻYTKOWNIKA")
        h_id = st.text_input("HASŁO")
        d_id = st.date_input("KONIEC SUBSKRYPCJI")
        k_id = st.number_input("STAWKA (PLN)", value=250.0)
        
        if st.form_submit_button("DODAJ NOWEGO KLIENTA"):
            if f_id and u_id:
                new_entry = {
                    "firma_id": f_id, "uzytkownik_id": u_id, "haslo": h_id,
                    "data_konca": str(d_id), "kwota_subskrypcji": k_id, 
                    "status_aktywny": True, "data_startu": datetime.now().strftime("%Y-%m-%d")
                }
                # Połączenie i wysyłka
                save_df = pd.concat([data.drop(columns=['display_name', 'STATUS_CORE']), pd.DataFrame([new_entry])], ignore_index=True)
                conn.update(data=save_df)
                st.success("DODANO NOWEGO KLIENTA POMYŚLNIE")
                st.rerun()
            else:
                st.warning("Pola ID FIRMY i ID UŻYTKOWNIKA są wymagane.")
    st.markdown('</div>', unsafe_allow_html=True)
