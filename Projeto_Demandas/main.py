import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import StringIO

st.set_page_config(layout="wide")

# --- Streamlit UI Components ---
st.title("📊 PCM Maintenance Dashboard")
st.sidebar.header("Configuration")

# File upload
uploaded_andamento = st.sidebar.file_uploader("Upload 'Andamento' CSV", type="csv")
uploaded_finalizada = st.sidebar.file_uploader("Upload 'Finalizada' CSV", type="csv")


# --- Data Processing Functions ---
@st.cache_data
def tratamento(file_path_andamento, file_path_finalizada):
        # Lendo os arquivos CSV
        demanda_and = pd.read_csv(file_path_andamento, encoding='utf-8', on_bad_lines='warn', sep=';', header=0,
                                  skip_blank_lines=True)
        demanda_fin = pd.read_csv(file_path_finalizada, encoding='utf-8', on_bad_lines='warn', sep=';', header=0,
                                  skip_blank_lines=True)

        # Lista de colunas a remover
        colunas_para_remover = ['COD_CONSUMIDOR', 'COD_SITUACAO', 'COD_OCORRENCIA', 'DES_OCORRENCIA', 'DES_RISCO',
                                'FLG_CONFERIDA']

        # Remove as colunas especificadas se existirem
        demanda_and = demanda_and.drop(columns=[col for col in colunas_para_remover if col in demanda_and.columns])
        demanda_fin = demanda_fin.drop(columns=[col for col in colunas_para_remover if col in demanda_fin.columns])

        # Lista de colunas para atualizar
        colunas_para_atualizar = ['DES_EQUIPE_EXEC', 'DES_ANDAMENTO_EXEC', 'DES_OBSERVACAO_RETAGUARDA', 'VLR_TOTAL',
                                  'DAT_INICIO', 'DAT_ATUALIZACAO']

        # Função auxiliar para substituir valores '<Null>'
        def substituir_nulos(df, colunas, valor_substituto):
            for column in colunas:
                if column in df.columns:
                    df[column] = df[column].replace('<Null>', valor_substituto)
            return df

        # Atualizando valores nas colunas para ambos os DataFrames
        demanda_and = substituir_nulos(demanda_and, colunas_para_atualizar, "NÃO INFORMADO")

        demanda_and['DAT_INICIO'] = demanda_and['DAT_INICIO'].replace("NÃO INFORMADO", np.nan)
        demanda_and['DAT_ATUALIZACAO'] = demanda_and['DAT_ATUALIZACAO'].replace("NÃO INFORMADO", np.nan)

        demanda_fin = substituir_nulos(demanda_fin, colunas_para_atualizar, "NÃO INFORMADO")

        demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].replace("NÃO INFORMADO", np.nan)
        demanda_fin['DAT_INICIO'] = demanda_fin['DAT_INICIO'].replace("NÃO INFORMADO", np.nan)



        demanda_fin['DAT_ATUALIZACAO'] = demanda_fin['DAT_ATUALIZACAO'].replace("NÃO INFORMADO", np.nan)

        # limpar as linhas com valores 'NA'')
        demanda_fin = demanda_fin.dropna(subset=['VLR_TOTAL'])

        demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].str.replace(',', '.').astype('float64', errors='ignore')
        demanda_fin['VLR_TOTAL'] = pd.to_numeric(demanda_fin['VLR_TOTAL'], errors='coerce')

        # demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].str.replace(',', '.').astype('float64')
        demanda_fin['VLR_TOTAL'] = pd.to_numeric(demanda_fin['VLR_TOTAL'], errors='coerce')

        # Opcional , retornar os valores para o original
        demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].astype(float)

        demanda_fin = pd.DataFrame(demanda_fin)
        demanda_and = pd.DataFrame(demanda_and)

        return demanda_fin, demanda_and


# --- Dashboard Functions ---
def show_cost_analysis(df_fin):
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Cost", f"R${df_fin['VLR_TOTAL'].sum():,.2f}")
    with col2:
        st.metric("Average Cost", f"R${df_fin['VLR_TOTAL'].mean():,.2f}")

    fig, ax = plt.subplots()
    df_fin['VLR_TOTAL'].plot(kind='hist', bins=20, edgecolor='black', ax=ax)
    ax.set_xlabel('Cost (R$)')
    ax.grid(True)
    st.pyplot(fig)


def show_team_analysis(df_and, df_fin):
    st.subheader("Demands by Team")
    team = st.selectbox("Select Team", df_and['COD_EQUIPE'].unique())

    col1, col2 = st.columns(2)
    with col1:
        st.write("**In Progress**")
        st.dataframe(df_and[df_and['COD_EQUIPE'] == team][['DES_SOLICITACAO', 'DAT_INICIO']])
    with col2:
        st.write("**Completed**")
        st.dataframe(df_fin[df_fin['COD_EQUIPE'] == team][['DES_SOLICITACAO', 'VLR_TOTAL']])


def show_temporal_analysis(df_and, df_fin):
    st.subheader("Temporal Analysis")

    # Convert dates
    df_and['DAT_INICIO'] = pd.to_datetime(demanda_and['DAT_INICIO'], format='%Y-%m-%d %H:%M', errors='coerce')

    df_fin['DAT_INICIO'] = pd.to_datetime(df_fin['DAT_INICIO'], format='%Y-%m-%d %H:%M', errors='coerce')

    # Time period selection
    time_range = st.slider(
        "Select Date Range",
        min_value=df_and['DAT_INICIO'].min().to_pydatetime(),
        max_value=df_and['DAT_INICIO'].max().to_pydatetime(),
        value=(df_and['DAT_INICIO'].min().to_pydatetime(), df_and['DAT_INICIO'].max().to_pydatetime())
    )

    # Filter data
    mask_and = (df_and['DAT_INICIO'] >= time_range[0]) & (df_and['DAT_INICIO'] <= time_range[1])
    mask_fin = (df_fin['DAT_INICIO'] >= time_range[0]) & (df_fin['DAT_INICIO'] <= time_range[1])

    # Plot
    fig, ax = plt.subplots()
    df_and[mask_and].set_index('DAT_INICIO').resample('W').size().plot(
        label='In Progress', ax=ax)
    df_fin[mask_fin].set_index('DAT_INICIO').resample('W').size().plot(
        label='Completed', ax=ax)
    ax.set_ylabel('Number of Demands')
    ax.legend()
    st.pyplot(fig)


# --- Main Execution ---
if uploaded_andamento and uploaded_finalizada:
    # Process data
    demanda_fin, demanda_and = tratamento(
        StringIO(uploaded_andamento.getvalue().decode("utf-8")),
        StringIO(uploaded_finalizada.getvalue().decode("utf-8")))

    # Calculate additional metrics
    demanda_and['delay_days'] = (
            pd.to_datetime(demanda_and['DAT_ATUALIZACAO']) -
            pd.to_datetime(demanda_and['DAT_INICIO'])
    ).dt.days

    # Show tabs
    tab1, tab2, tab3 = st.tabs(["Cost Analysis", "Team Analysis", "Temporal Analysis"])

    with tab1:
        show_cost_analysis(demanda_fin)

    with tab2:
        show_team_analysis(demanda_and, demanda_fin)

    with tab3:
        show_temporal_analysis(demanda_and, demanda_fin)

    # Raw data explorer
    st.subheader("Data Explorer")
    dataset = st.radio("Select Dataset", ("In Progress", "Completed"))
    if dataset == "In Progress":
        st.dataframe(demanda_and)
    else:
        st.dataframe(demanda_fin)
 #   else:
  #  st.warning("Please upload both CSV files to proceed")

# How to run:
# streamlit run dashboard_streamlit.py