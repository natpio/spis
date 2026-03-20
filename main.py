import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# =========================================================
# 1. KONFIGURACJA SYSTEMU I STYL VORTEZA
# =========================================================
st.set_page_config(page_title="VORTEZA MASTER OPS", layout="wide", initial_sidebar_state="expanded")

def apply_vorteza_theme():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;700&display=swap');
            
            :root {
                --v-copper: #B58863;
                --v-dark: #0E0E0E;
                --v-panel: rgba(20, 20, 20, 0.98);
            }

            .stApp {
                background-color: var(--v-dark);
                color: #E0E0E0;
                font-family: 'Montserrat', sans-serif;
            }

            /* Styl nagłówków */
            h1, h2, h3 {
                color: var(--v-copper) !important;
                font-weight: 700 !important;
                text-transform: uppercase;
                letter-spacing: 3px;
                margin-bottom: 20px;
            }

            /* Karty statystyk */
            .vorteza-card {
                background: var(--v-panel);
                padding: 25px;
                border-radius: 4px;
                border-left: 5px solid var(--v-copper);
                box-shadow: 0 15px 35px rgba(0,0,0,0.7);
                margin-bottom: 25px;
            }

            /* Metryki */
            [data-testid="stMetricValue"] {
                color: var(--v-copper) !important;
                font-size: 1.8rem !important;
                font-weight: 700 !important;
            }
            [data-testid="stMetricLabel"] {
                color: #888 !important;
                text-transform: uppercase;
            }

            /* Sidebar */
            [data-testid="stSidebar"] {
                background-color: #050505 !important;
                border-right: 1px solid #222;
            }

            /* Przyciski */
            .stButton > button {
                background-color: transparent !important;
                color: var(--v-copper) !important;
                border: 1px solid var(--v-copper) !important;
                padding: 12px 24px !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                width: 100%;
                transition: all 0.3s ease;
            }
            .stButton > button:hover {
                background-color: var(--v-copper) !important;
                color: black !important;
                box-shadow: 0 0 15px var(--v-copper);
            }
            
            /* Formularze */
            div[data-baseweb="input"] {
                background-color: #111 !important;
                border: 1px solid #333 !important;
            }
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
    
    # Naprawa formatów
    df['kwota_subskrypcji'] = pd.to_numeric(df['kwota_subskrypcji'], errors='coerce').fillna(0)
    df['data_konca'] = pd.to_datetime(df['data_konca'], errors='coerce').dt.date
    df['display_name'] = df['firma_id'].astype(str) + " // " + df['uzytkownik_id'].astype(str)
    return df

try:
    data = get_live_data()
except Exception as e:
    st.error(f"KRYTYCZNY BŁĄD POŁĄCZENIA: {e}")
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
        
        # Ostrzeżenie o terminie
        row_bg = "transparent"
        if row['data_konca'] and row['data_konca'] < today and is_active:
            row_bg = "rgba(181, 136, 99, 0.1)"
        
        table_rows += f"""
        <tr style="background-color: {row_bg}; border-bottom: 1px solid #222;">
            <td style="padding: 15px; color: #fff; font-weight: bold;">{row['firma_id']}</td>
            <td style="padding: 15px; color: #AAA;">{row['uzytkownik_id']}</td>
            <td style="padding: 15px;">
                <span style="color: {status_color}; font-size: 0.8rem; font-weight: bold; border: 1px solid {status_color}; padding: 3px 8px; border-radius: 3px;">
                    {status_label}
                </span>
            </td>
            <td style="padding: 15px; color: #EEE;">{row['data_konca']}</td>
            <td style="padding: 15px; color: #B58863; font-weight: bold;">{row['kwota_subskrypcji']:.2f} PLN</td>
        </tr>
        """

    html_code = f"""
    <div style="font-family: 'Montserrat', sans-serif; background-color: #0E0E0E; padding: 10px;">
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
                <tr style="border-bottom: 2px solid #B58863;">
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.8rem;">Firma</th>
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.8rem;">User</th>
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.8rem;">Status</th>
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.8rem;">Termin</th>
                    <th style="padding: 15px; color: #B58863; text-transform: uppercase; font-size: 0.8rem;">Stawka</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """
    # Renderowanie jako komponent - to eliminuje błąd surowego tekstu
    components.html(html_code, height=600, scrolling=True)

# =========================================================
# 4. NAWIGACJA I MODUŁY
# =========================================================
st.sidebar.markdown(f"<h2 style='text-align:center;'>VORTEZA</h2>", unsafe_allow_html=True)
menu = ["📊 DASHBOARD", "⚙️ ZARZĄDZANIE", "➕ NOWA INSTANCJA"]
choice = st.sidebar.selectbox("NAWIGACJA", menu)

# --- DASHBOARD ---
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

# --- ZARZĄDZANIE ---
elif choice == "⚙️ ZARZĄDZANIE":
    st.header("KONFIGURACJA RDZENIA")
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    
    target = st.selectbox("Wybierz instancję do modyfikacji:", data['display_name'].tolist())
    idx = data[data['display_name'] == target].index[0]
    row = data.loc[idx]

    with st.form("update_vorteza"):
        col1, col2 = st.columns(2)
        with col1:
            u_pass = st.text_input("Hasło Dostępowe", value=str(row['haslo']))
            u_status = st.checkbox("Status Aktywny", value=bool(row['STATUS_CORE']))
            u_app = st.text_input("Aplikacja ID", value=str(row.get('aplikacja_id', '')))
        with col2:
            u_date = st.date_input("Termin Ważności", value=row['data_konca'])
            u_price = st.number_input("Stawka Subskrypcji", value=float(row['kwota_subskrypcji']))
            u_url = st.text_input("System URL", value=str(row.get('url_aplikacji', '')))
        
        if st.form_submit_button("ZAPISZ ZMIANY W CHMURZE"):
            df_up = data.copy().drop(columns=['display_name', 'STATUS_CORE'])
            # Szukamy oryginalnej nazwy kolumny w arkuszu
            orig_col = next((c for c in df_up.columns if 'status' in c.lower() or 'aktyw' in c.lower()), 'status_aktywny')
            
            df_up.at[idx, 'haslo'] = u_pass
            df_up.at[idx, orig_col] = u_status
            df_up.at[idx, 'data_konca'] = str(u_date)
            df_up.at[idx, 'kwota_subskrypcji'] = u_price
            df_up.at[idx, 'aplikacja_id'] = u_app
            df_up.at[idx, 'url_aplikacji'] = u_url
            
            conn.update(data=df_up)
            st.success("ZSYNCHRONIZOWANO Z GOOGLE SHEETS")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- NOWY KLIENT ---
elif choice == "➕ NOWA INSTANCJA":
    st.header("REJESTRACJA SYSTEMU")
    st.markdown('<div class="vorteza-card">', unsafe_allow_html=True)
    
    with st.form("new_instance"):
        cx1, cx2 = st.columns(2)
        with cx1:
            f_id = st.text_input("ID FIRMY")
            u_id = st.text_input("ID UŻYTKOWNIKA")
            h_id = st.text_input("HASŁO")
        with cx2:
            a_id = st.text_input("APLIKACJA ID")
            d_id = st.date_input("DATA KOŃCA")
            k_id = st.number_input("STAWKA (PLN)", value=250.0)
            
        if st.form_submit_button("DODAJ NOWĄ INSTANCJĘ"):
            if f_id and u_id:
                new_entry = {
                    "firma_id": f_id, "uzytkownik_id": u_id, "haslo": h_id,
                    "aplikacja_id": a_id, "data_konca": str(d_id),
                    "kwota_subskrypcji": k_id, "status_aktywny": True,
                    "data_startu": datetime.now().strftime("%Y-%m-%d"),
                    "url_aplikacji": ""
                }
                # Połączenie i wysyłka
                save_df = pd.concat([data.drop(columns=['display_name', 'STATUS_CORE']), pd.DataFrame([new_entry])], ignore_index=True)
                conn.update(data=save_df)
                st.success(f"SYSTEM DLA {f_id} ZOSTAŁ UTWORZONY")
                st.rerun()
            else:
                st.warning("Pola ID FIRMY i ID UŻYTKOWNIKA są wymagane.")
    st.markdown('</div>', unsafe_allow_html=True)
