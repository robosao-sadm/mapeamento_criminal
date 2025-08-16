# -*- coding: utf-8 -*-
# =======================
# app.py - Código unificado com navegação por botões e teclado (via componente)
# =======================
import os
import warnings
import locale
import base64
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import AntPath
from folium.features import DivIcon

# =======================
# 0) Configuração
# =======================
st.set_page_config(page_title="Apresentação da Incidência Criminal", page_icon="📍", layout="wide")
warnings.filterwarnings("ignore")

# =======================
# 1) CSS / UI
# =======================
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        return None

background_style = ""
st.markdown(f"""
<style>
.block-container {{
    max-width: 80% !important;
    padding: 2rem !important;
}}
[data-testid="stAppViewContainer"] {{ overflow-y: auto; }}
html, body {{ height: 85%; }}
.centered-text {{ text-align: center; }}
.header-content {{
    text-align: center;
    padding: 15px 0;
    box-shadow: 0 1px 1px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
}}
.header-content h1 {{
    margin: 0;
    line-height: 1.0;
    color: white;
    text-shadow: 2px 2px 3px #000000;
}}
.centered-text h2 {{ margin-bottom: 0; }}
{background_style}
</style>
""", unsafe_allow_html=True)

# =======================
# 2) Dados
# =======================
@st.cache_data(show_spinner=False)
def carregar_dados(caminho_csv: str) -> pd.DataFrame:
    df = pd.read_csv(caminho_csv, sep=";")
    df.columns = df.columns.str.strip()

    obrig = {"LATITUDE", "LONGITUDE", "DATA_FATO", "DESCR_NATUREZA_PRINCIPAL", "MUNICIPIO", "CAUSA_PRESUMIDA", "DESCRICAO_LOCAL_IMEDIATO", "SINTESE"}
    faltando = obrig - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes no CSV: {', '.join(sorted(faltando))}")

    df["DATA_FATO"] = pd.to_datetime(df["DATA_FATO"], dayfirst=True, errors="coerce")
    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"].astype(str).str.replace(",", "."), errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"].astype(str).str.replace(",", "."), errors="coerce")
    df = df.dropna(subset=["LATITUDE", "LONGITUDE"]).reset_index(drop=True)

    if df["DATA_FATO"].notna().any():
        data_max = df["DATA_FATO"].max()
        data_corte = data_max - pd.DateOffset(months=6)
        df = df[df["DATA_FATO"] >= data_corte]

    return df.sort_values("DATA_FATO", na_position="last").reset_index(drop=True)

csv_path = "relatorio_estatisticas_reds.csv"
try:
    df_raw = carregar_dados(csv_path)
except Exception as e:
    st.error(f"Falha ao carregar '{csv_path}': {e}")
    st.stop()
if df_raw.empty:
    st.warning("Nenhum dado válido para exibir após o filtro dos últimos 6 meses.")
    st.stop()

# =======================
# 3) KML / Mapa
# =======================
@st.cache_data(show_spinner=False)
def kml_to_geojson(kml_path: str):
    if not os.path.exists(kml_path):
        return None
    try:
        gdf = gpd.read_file(kml_path, driver="KML")
        return gdf
    except Exception:
        return None

def add_limites(mapa):
    kml_file = "limites_municipais.kml"
    gdf_limites = kml_to_geojson(kml_file)
    if gdf_limites is not None:
        folium.GeoJson(
            gdf_limites.to_json(),
            name="Limites Municipais",
            style_function=lambda x: {"fillColor": "green", "color": "black", "weight": 1, "fillOpacity": 0.5},
        ).add_to(mapa)

def renderizar_mapa_completo(mapa: folium.Map, dataframe: pd.DataFrame, indice_atual: int):
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, '')

    if indice_atual > 0:
        caminhos_percorridos = [[dataframe.iloc[i]["LATITUDE"], dataframe.iloc[i]["LONGITUDE"]] for i in range(indice_atual)]
        if len(caminhos_percorridos) > 1:
            folium.PolyLine(caminhos_percorridos, color='blue', weight=2.5, opacity=0.8).add_to(mapa)

    if indice_atual > 0:
        caminho_animado = [
            [dataframe.iloc[indice_atual-1]["LATITUDE"], dataframe.iloc[indice_atual-1]["LONGITUDE"]],
            [dataframe.iloc[indice_atual]["LATITUDE"], dataframe.iloc[indice_atual]["LONGITUDE"]],
        ]
        AntPath(caminho_animado, color='red', weight=3, delay=800, dash_array=[10, 20]).add_to(mapa)

    for i in range(len(dataframe)):
        try:
            incidente = dataframe.iloc[i]
            lat = float(incidente["LATITUDE"])
            lon = float(incidente["LONGITUDE"])
            data_fmt = incidente["DATA_FATO"].strftime('%d/%m/%Y') if pd.notna(incidente["DATA_FATO"]) else 'N/A'

            cor_marcador_fill = "red" if i == indice_atual else "blue"
            cor_marcador_text = "white"
            tamanho_marcador = 30 if i == indice_atual else 20
            numero_marcador = str(i + 1)

            popup_text = (
                f"Ponto atual: {incidente.get('DESCR_NATUREZA_PRINCIPAL','N/A')} ({data_fmt})"
                if i == indice_atual else
                f"Incidente passado: {incidente.get('DESCR_NATUREZA_PRINCIPAL','N/A')} ({data_fmt})"
            )

            marker = folium.Marker(
                [lat, lon],
                popup=popup_text,
                icon=DivIcon(
                    icon_size=(tamanho_marcador, tamanho_marcador),
                    icon_anchor=(tamanho_marcador // 2, tamanho_marcador // 2),
                    html=f'<div style="font-size: 12px; font-weight: bold; color: {cor_marcador_text}; background-color: {cor_marcador_fill}; border-radius: 50%; width: {tamanho_marcador}px; height: {tamanho_marcador}px; text-align: center; line-height: {tamanho_marcador}px;">{numero_marcador}</div>'
                )
            )
            marker.add_to(mapa)
            marker.id = f'marker_{i}'
        except Exception as e:
            st.warning(f"Erro ao renderizar o incidente no índice {i + 1}: {e}. O ponto será pulado.")
            continue

# =======================
# 4) App principal
# =======================
conteudos_app = [
    'mapa',
]

if 'indice_atual' not in st.session_state:
    st.session_state['indice_atual'] = 0

conteudo_atual = conteudos_app[st.session_state.indice_atual]

if conteudo_atual.endswith('.JPG'):
    st.image(conteudo_atual, use_container_width=True)

elif conteudo_atual == 'mapa':
    ss = st.session_state
    ss.setdefault("map_indice", 0)
    ss.setdefault("base_zoom", 10)

    unique_naturezas = sorted(df_raw['DESCR_NATUREZA_PRINCIPAL'].unique())
    unique_municipios = sorted(df_raw['MUNICIPIO'].unique())

    with st.sidebar:
        st.markdown("### Filtros de visualização")

        selected_naturezas = st.multiselect(
            "Natureza do Crime",
            options=unique_naturezas,
            default=unique_naturezas,
            key="natureza_multiselect"
        )

        selected_municipios = st.multiselect(
            "Município",
            options=unique_municipios,
            default=unique_municipios,
            key="municipio_multiselect"
        )

        # --- Novo seletor de períodos pré-definidos
        st.markdown("### Período de análise")
        periodo_opcao = st.radio(
            label="Período:",
            options=["Últimos 7 dias", "Últimos 14 dias", "Últimos 31 dias", "Selecionar intervalo manual"],
            key="radio_periodo"
        )

        hoje = pd.Timestamp.today().normalize()

        if periodo_opcao == "Selecionar intervalo manual":
            start_date = st.date_input(
                "Data inicial",
                value=df_raw["DATA_FATO"].min().date(),
                key="start_date_input"
            )
            end_date = st.date_input(
                "Data final",
                value=df_raw["DATA_FATO"].max().date(),
                key="end_date_input"
            )
            # Validação para não passar de 31 dias
            if (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days > 31:
                st.error("Selecione um intervalo de no máximo 31 dias.")
        else:
            if periodo_opcao == "Últimos 7 dias":
                start_date = (hoje - pd.Timedelta(days=7)).date()
            elif periodo_opcao == "Últimos 14 dias":
                start_date = (hoje - pd.Timedelta(days=14)).date()
            else:
                start_date = (hoje - pd.Timedelta(days=31)).date()
            end_date = hoje.date()

    # --- Aplicação dos filtros
    df = df_raw[
        (df_raw['DESCR_NATUREZA_PRINCIPAL'].isin(selected_naturezas)) &
        (df_raw['MUNICIPIO'].isin(selected_municipios)) &
        (df_raw['DATA_FATO'].dt.date >= start_date) &
        (df_raw['DATA_FATO'].dt.date <= end_date)
    ].reset_index(drop=True)

    with st.container():
        st.markdown(
            '<div class="header-content"><h1>GDO - 1º SEMESTRE 2025</h1>'
            '<h3 class="centered-text">Análise do indíce de Morte Violenta - 43º BPM</h3></div>',
            unsafe_allow_html=True
        )

    if not df.empty:
        if ss.map_indice >= len(df):
            ss.map_indice = 0

        col_mapa, col_info = st.columns([8, 4])

        with col_mapa:
            with st.spinner('Atualizando mapa...'):
                center_lat = df['LATITUDE'].mean()
                center_lon = df['LONGITUDE'].mean()

                m = folium.Map(location=[center_lat, center_lon], zoom_start=ss.base_zoom,
                               tiles="OpenStreetMap", width="100%", height="100%")
                add_limites(m)
                renderizar_mapa_completo(m, df, ss.map_indice)

                map_data = st_folium(m, height=380, use_container_width=True)

                clicked_object = map_data.get("last_object_clicked")
                if clicked_object and 'id' in clicked_object:
                    clicked_marker_id = clicked_object["id"]
                    if clicked_marker_id.startswith('marker_'):
                        clicked_index = int(clicked_marker_id.split('_')[1])
                        if clicked_index != ss.map_indice:
                            ss.map_indice = clicked_index
                            st.rerun()

        with col_info:
            incidente = df.iloc[ss.map_indice]
            data_fmt_incidente = incidente["DATA_FATO"].strftime('%d/%m/%Y') if pd.notna(incidente["DATA_FATO"]) else 'N/A'
            if ss.map_indice == 0:
                string_intervalo_painel = "Primeira MV 2025"
            elif pd.notna(df.iloc[ss.map_indice]["DATA_FATO"]) and pd.notna(df.iloc[ss.map_indice-1]["DATA_FATO"]):
                diferenca_dias_painel = (df.iloc[ss.map_indice]["DATA_FATO"] - df.iloc[ss.map_indice-1]["DATA_FATO"]).days
                string_intervalo_painel = f'{diferenca_dias_painel} DIAS'
            else:
                string_intervalo_painel = 'N/A'

            st.markdown(f"""
            ### 🔹 {incidente.get('DESCR_NATUREZA_PRINCIPAL', 'N/A')}
            - **Município:** {incidente.get('MUNICIPIO', 'N/A')}
            - **Data:** {data_fmt_incidente}
            - **Intervalo:** {string_intervalo_painel}
            - **Causa Presumida:** {incidente.get('CAUSA_PRESUMIDA', 'N/A')}
            - **Local:** {incidente.get('DESCRICAO_LOCAL_IMEDIATO', 'N/A')}
            - **Síntese do fato:** {incidente.get('SINTESE', 'N/A')}
            """)

            bcols = st.columns(2)
            with bcols[0]:
                st.button("⬅️ Voltar",
                          on_click=lambda: ss.update({"map_indice": ss.map_indice - 1}),
                          disabled=ss.map_indice == 0,
                          key="voltar_button_mapa")
            with bcols[1]:
                st.button("➡️ Avançar",
                          on_click=lambda: ss.update({"map_indice": ss.map_indice + 1}),
                          disabled=ss.map_indice >= len(df) - 1,
                          key="avancar_button_mapa")
    else:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")

# -----------------------
# Botões de navegação da apresentação
# -----------------------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    bcols = st.columns(2)
    with bcols[0]:
        if st.button("⬅️ Anterior", disabled=st.session_state.indice_atual == 0, key="main_prev", use_container_width=True):
            st.session_state.indice_atual -= 1
            st.rerun()
    with bcols[1]:
        if st.button("Próximo ➡️", disabled=st.session_state.indice_atual >= len(conteudos_app) - 1, key="main_next", use_container_width=True):
            st.session_state.indice_atual += 1
            st.rerun()

# =======================
# 5) HOTKEYS (sem <script> inline) — usa componente
# =======================
# Tenta com streamlit-keyup; se não existir, tenta streamlit-js-eval
key_pressed = None
_hotkey_note = None

try:
    from streamlit_keyup import st_keyup  # componente simples de keyup
    key_pressed = st_keyup("", key="hotkeys_arrow", debounce=10)
    _hotkey_note = "keyup"
except Exception:
    try:
        from streamlit_js_eval import streamlit_js_eval
        key_pressed = streamlit_js_eval(
            js_expressions="""
            new Promise((resolve)=>{
              function handler(e){
                if (e.key === 'ArrowLeft' || e.key === 'ArrowRight'){
                  document.removeEventListener('keydown', handler, true);
                  resolve(e.key);
                }
              }
              document.addEventListener('keydown', handler, true);
            })
            """,
            key="hotkeys_arrow_component"
        )
        _hotkey_note = "js-eval"
    except Exception:
        st.info("Atalhos de teclado desativados (instale 'streamlit-keyup' ou 'streamlit-js-eval').")

# Aplica navegação quando uma seta for detectada
if key_pressed in ("ArrowLeft", "ArrowRight"):
    if key_pressed == "ArrowLeft" and st.session_state.indice_atual > 0:
        st.session_state.indice_atual -= 1
        st.rerun()
    elif key_pressed == "ArrowRight" and st.session_state.indice_atual < len(conteudos_app) - 1:
        st.session_state.indice_atual += 1
        st.rerun()
# (Opcional) para debug:
# st.caption(f"Hotkeys: {_hotkey_note}, last={key_pressed}")
