import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import base64
from PIL import Image

# =========================================================
# 1. KONFIGURACJA I STYLIZACJA VORTEZA SYSTEMS
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER | SPIS", layout="wide")

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

def apply_vorteza_theme():
    bin_str = get_base64_of_bin_file('bg_vorteza.png')
    bg_css = f'background-image: url("data:image/png;base64,{bin_str}");' if bin_str else "background-color: #0E0E0E;"
    
    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700&display=swap');

            :root {{
                --v-copper: #B58863;
                --v-dark: #0E0E0E;
                --v-panel: rgba(20, 20, 20, 0.95);
                --v-text: #E0E0E0;
            }}

            .stApp {{
                {bg_css}
                background-size: cover;
                background-attachment: fixed;
                color: var(--v-text);
                font-family: 'Montserrat', sans-serif;
            }}

            h1, h2, h3, .stSubheader {{
                color: var(--v-copper) !important;
                font-weight: 700 !important;
                text-transform: uppercase;
                letter-spacing: 2px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            }}

            .vorteza-card {{
                background-color: var(--v-panel);
                padding: 25px;
                border-radius: 5px;
                border-left: 5px solid var(--v-copper);
                box-shadow: 0 10px 40px rgba(0,0,0,0.8);
                backdrop-filter: blur(15px);
                margin-bottom: 25px;
            }}

            .cost-table {{
                width: 100%;
                border-collapse: collapse;
                background-color: transparent;
                margin-top: 10px;
            }}
            .cost-table th {{
                text-align: left;
                color: var(--v-copper);
                border-bottom: 2px solid var(--v-copper);
                padding: 12px;
                text-transform: uppercase;
                font-size: 0.85rem;
            }}
            .cost-table td {{
                padding: 12px;
                border-bottom: 1px solid #333;
                font-size: 0.95rem;
                color: #E0E0E0;
            }}

            .stButton > button {{
                background-color: rgba(0, 0, 0, 0.7);
                color: var(--v-copper);
                border: 1px solid var(--v-copper);
                padding: 10px;
                width: 100%;
                font-weight: 700;
                text-transform: uppercase;
                transition: 0.3s;
            }}
            .stButton > button:hover {{
                background-color: var(--v-copper);
                color: black;
            }}

            div[data-baseweb="select"] > div, input {{
                background-color: rgba(15, 15, 15, 0.9) !important;
                color: white !important;
                border: 1px solid #444 !important;
            }}

            [data-testid="stMetricValue"] {{
                color: var(--v-copper) !important;
                font-weight: 700 !important;
            }}
        </style>
    """, unsafe_allow_html=True)

apply_vorteza_theme()

# =========================================================
# 2. NAGŁÓWEK I LOGO
# =========================================================
col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        logo = Image.open('logo_vorteza.png')
        st.image(logo, use_container_width=True)
    except:
        st.markdown("<h2 style='color:#B58863;'>VORTEZA</h2>", unsafe_allow_html=True)

with col_title:
    st.markdown("<h1 style='margin-bottom:0;'>VORTEZA MASTER</h1>", unsafe_allow_html=True)
    st.markdown("<p style='letter-spacing:3px; color:#666;'>CENTRALNY SPIS SUBSKRYPCJI I DOSTĘPÓW</p>", unsafe_allow_html=True)

# =========================================================
# 3. POŁĄCZENIE I CZYSZCZENIE DANYCH
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(ttl=0)
    # Usuwamy spacje i ukryte znaki z nagłówków kolumn
    df.columns = [str(c).strip().replace('\n', '') for c in df.columns]
    
    # Mapowanie kolumny statusu (na wypadek różnych nazw w arkuszu)
    possible_status_names = ['status_aktywny', 'status_aktywn_y', 'aktywny']
    for name in possible_status_names:
        if name in df.columns:
            df.rename(columns={name: 'status_main'}, inplace=True)
            break
            
    if 'status_main' not in df.columns:
        df['status_main'] = True # Domyślnie True jeśli nie ma kolumny
        
    df['display_name'] = df['firma_id'].astype(str) + " | " + df['uzytkownik_id'].astype(str)
    return df

try:
    data = load_data()
except Exception as e:
    st.error(f"BŁĄD DANYCH: {e}")
    st.stop()

# =========================================================
# 4. NAWIGACJA
# =========================================================
st.sidebar.markdown("<h3 style='text-align:center;'>MENU SYSTEMU</h3>", unsafe_allow_html=True)
menu = ["📊 DASHBOARD", "🔧 KONFIGURACJA KLIENTA", "➕ NOWA REJESTRACJA"]
choice = st.sidebar.selectbox("NAWIGACJA", menu)

# =========================================================
# 5. DASHBOARD - TUTAJ BYŁ BŁĄD FORMATOWANIA
# =========================================================
if choice == "📊 DASHBOARD":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("STATUS EKONOMICZNY")
    
    today = datetime.now().date()
    active_mask = data['status_main'] == True
    total_rev = data[active_mask]['kwota_subskrypcji'].sum()
    active_count = data[active_mask].shape[0]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("PRZYCHÓD (M)", f"{total_rev:,.2f} PLN")
    m2.metric("AKTYWNE SYSTEMY", active_count)
    m3.metric("SUMA KLIENTÓW", len(data))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("LISTA OPERACYJNA")
    
    # BUDOWANIE TABELI HTML
    table_html = """
    <table class="cost-table">
        <thead>
            <tr>
                <th>Firma</th><th>Użytkownik</th><th>Status</th><th>Wygasa</th><th>Kwota</th>
            </tr>
        </thead>
        <tbody>
    """
    for _, row in data.iterrows():
        is_active = row['status_main']
        status_txt = "✅ AKTYWNY" if is_active else "❌ BLOKADA"
        row_style = ""
        
        try:
            end_dt = pd.to_datetime(row['data_konca']).date()
            if end_dt < today and is_active:
                row_style = 'style="background-color: rgba(181, 136, 99, 0.15); color: #ffbaba;"'
        except: pass
        
        table_html += f"""
        <tr {row_style}>
            <td>{row['firma_id']}</td>
            <td>{row['uzytkownik_id']}</td>
            <td>{status_txt}</td>
            <td>{row['data_konca']}</td>
            <td>{row['kwota_subskrypcji']:.2f} PLN</td>
        </tr>
        """
    table_html += "</tbody></table>"
    
    # KLUCZOWE: Użycie unsafe_allow_html=True
    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 6. KONFIGURACJA (EDYCJA)
# =========================================================
elif choice == "🔧 KONFIGURACJA KLIENTA":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("MODYFIKACJA DOSTĘPU")
    
    selected = st.selectbox("Wybierz instancję do edycji:", data['display_name'].tolist())
    idx = data[data['display_name'] == selected].index[0]
    row = data.loc[idx]

    with st.form("edit_vorteza"):
        c1, c2 = st.columns(2)
        with c1:
            n_pass = st.text_input("Klucz Dostępu (Hasło)", value=str(row['haslo']))
            n_status = st.checkbox("Dostęp Aktywny", value=bool(row['status_main']))
            n_app_id = st.text_input("Aplikacja ID", value=str(row.get('aplikacja_id', '')))
        with c2:
            n_end = st.text_input("Termin ważności (RRRR-MM-DD)", value=str(row['data_konca']))
            n_price = st.number_input("Stawka Subskrypcji", value=float(row['kwota_subskrypcji']))
            n_url = st.text_input("URL Systemu", value=str(row.get('url_aplikacji', '')))
            
        if st.form_submit_button("ZAKTUALIZUJ RDZEŃ BAZY"):
            df_up = data.copy().drop(columns=['display_name'])
            # Przywracamy oryginalną nazwę kolumny przed zapisem
            orig_col = 'status_aktywn_y' if 'status_aktywn_y' in df_up.columns else 'status_aktywny'
            df_up.rename(columns={'status_main': orig_col}, inplace=True)
            
            df_up.at[idx, 'haslo'] = n_pass
            df_up.at[idx, orig_col] = n_status
            df_up.at[idx, 'data_konca'] = n_end
            df_up.at[idx, 'kwota_subskrypcji'] = n_price
            df_up.at[idx, 'url_aplikacji'] = n_url
            df_up.at[idx, 'aplikacja_id'] = n_app_id
            
            conn.update(data=df_up)
            st.success("ZMIANY ZAPISANE W SYSTEMIE")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 7. REJESTRACJA (NOWY)
# =========================================================
elif choice == "➕ NOWA REJESTRACJA":
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    st.subheader("DODAWANIE NOWEGO KLIENTA")
    with st.form("new_client"):
        cc1, cc2 = st.columns(2)
        with cc1:
            f = st.text_input("FIRMA ID")
            u = st.text_input("USER ID")
            h = st.text_input("HASŁO")
        with cc2:
            aid = st.text_input("APLIKACJA ID")
            d_s = st.date_input("DATA STARTU")
            d_k = st.date_input("DATA KOŃCA")
            kw = st.number_input("KWOTA", value=250.0)

        if st.form_submit_button("UTWÓRZ NOWY PROFIL"):
            new_r = {
                "firma_id": f, "uzytkownik_id": u, "haslo": h, "aplikacja_id": aid,
                "data_startu": str(d_s), "data_konca": str(d_k),
                "kwota_subskrypcji": kw, "status_aktywny": True, "url_aplikacji": ""
            }
            final_df = pd.concat([data.drop(columns=['display_name', 'status_main']), pd.DataFrame([new_r])], ignore_index=True)
            conn.update(data=final_df)
            st.success("KLIENT DODANY POMYŚLNIE")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
