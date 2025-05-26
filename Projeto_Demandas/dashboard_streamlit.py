import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import locale
import re
from collections import Counter
from wordcloud import WordCloud
import plotly.express as px

# Configura o locale para Português Brasil
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')


@st.cache_data
def format_currency(value):
    """Formata valores como moeda brasileira"""
    return locale.currency(value, grouping=True, symbol=True)


st.set_page_config(layout="wide")
PATH_ANDAMENTO = r'F:\GOM-A\Eletromecânica\1 - MECÂNICA\ArcGIS\VIEWS_DEMANDA\ABERTAS.xls'
PATH_FINALIZADA = r'F:\GOM-A\Eletromecânica\1 - MECÂNICA\ArcGIS\VIEWS_DEMANDA\FECHADAS.xls'

def search_demand(df_and, df_fin):
    st.sidebar.header("🔍 Pesquisar Demanda")

    # Verifica se a coluna 'DEMANDA' existe
    if 'DEMANDA' not in df_and.columns or 'DEMANDA' not in df_fin.columns:
        st.sidebar.warning("Coluna 'DEMANDA' não encontrada nos dados")
        return

    search_term = st.sidebar.text_input("Digite o número da demanda:")

    if search_term:
        try:
            # Converte para string e remove espaços
            search_term = int(search_term)

            # Pesquisa exata (para números de demanda)
            result_and = df_and[df_and['DEMANDA'].astype(int) == search_term]
            result_fin = df_fin[df_fin['DEMANDA'].astype(int) == search_term]

            if not result_and.empty or not result_fin.empty:
                st.subheader(f"Resultados para demanda: {search_term}")

                if not result_and.empty:
                    with st.expander("Demandas em Andamento", expanded=True):
                        st.dataframe(
                            result_and[['DEMANDA', 'DES_SOLICITACAO', 'DES_INSTRUCAO', 'DAT_INICIO']]
                            .style.format({'DAT_INICIO': lambda x: x.strftime('%d/%m/%Y')})
                        )

                if not result_fin.empty:
                    with st.expander("Demandas Finalizadas", expanded=True):
                        df_display = result_fin[
                            ['DEMANDA', 'DES_SOLICITACAO', 'VLR_TOTAL', 'DAT_INICIO', 'DES_INSTRUCAO']].copy()

                        # 1. Converter valores para datetime primeiro
                        df_display['DAT_INICIO'] = pd.to_datetime(
                            df_display['DAT_INICIO'],
                            format='%d/%m/%Y %H:%M',
                            errors='coerce'
                        )

                        # 2. Formatar valores monetários
                        df_display['VLR_TOTAL'] = df_display['VLR_TOTAL'].apply(format_currency)

                        # 3. Exibir dataframe com formatação segura
                        st.dataframe(
                            df_display.style.format({
                                'DAT_INICIO': lambda x: x.strftime('%d/%m/%Y') if not pd.isna(x) else 'N/A'
                            })
                        )
            else:
                st.warning(f"Nenhuma demanda encontrada com o número: {search_term}")
        except Exception as e:
            st.error(f"Erro na pesquisa: {str(e)}")


@st.cache_data
def tratamento(file_path_andamento, file_path_finalizada):
    # Lendo os arquivos XLS
    demanda_and = pd.read_excel(file_path_andamento, sheet_name=0)
    demanda_fin = pd.read_excel(file_path_finalizada, sheet_name=0)

    # Lista de colunas a remover
    colunas_para_remover = ['COD_CONSUMIDOR', 'COD_SITUACAO', 'COD_OCORRENCIA', 'DES_OCORRENCIA', 'DES_RISCO',
                            'FLG_CONFERIDA']

    demanda_and = demanda_and.drop(columns=[col for col in colunas_para_remover if col in demanda_and.columns])
    demanda_fin = demanda_fin.drop(columns=[col for col in colunas_para_remover if col in demanda_fin.columns])

    colunas_para_atualizar = ['DES_EQUIPE_EXEC', 'DES_ANDAMENTO_EXEC', 'DES_OBSERVACAO_RETAGUARDA', 'VLR_TOTAL',
                              'DAT_INICIO', 'DAT_ATUALIZACAO']

    def substituir_nulos(df, colunas, valor_substituto):
        for column in colunas:
            if column in df.columns:
                df[column] = df[column].replace('<Null>', valor_substituto)
        return df

    demanda_and = substituir_nulos(demanda_and, colunas_para_atualizar, "NÃO INFORMADO")
    demanda_and['DAT_INICIO'] = demanda_and['DAT_INICIO'].replace("NÃO INFORMADO", np.nan)
    demanda_and['DAT_ATUALIZACAO'] = demanda_and['DAT_ATUALIZACAO'].replace("NÃO INFORMADO", np.nan)

    demanda_fin = substituir_nulos(demanda_fin, colunas_para_atualizar, "NÃO INFORMADO")
    demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].replace("NÃO INFORMADO", np.nan)
    demanda_fin['DAT_INICIO'] = demanda_fin['DAT_INICIO'].replace("NÃO INFORMADO", np.nan)
    demanda_fin['DAT_ATUALIZACAO'] = demanda_fin['DAT_ATUALIZACAO'].replace("NÃO INFORMADO", np.nan)

    demanda_and['DAT_INICIO'] = pd.to_datetime(demanda_and['DAT_INICIO'], format='%d/%m/%Y %H:%M', errors='coerce')
    demanda_and['DAT_ATUALIZACAO'] = pd.to_datetime(demanda_and['DAT_ATUALIZACAO'], format='%d/%m/%Y %H:%M', errors='coerce')

    demanda_fin = demanda_fin.dropna(subset=['VLR_TOTAL'])

    # Substitui vírgula por ponto e converte para float
    #demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].astype(str).str.replace(',', '.')
    #demanda_fin['VLR_TOTAL'] = pd.to_numeric(demanda_fin['VLR_TOTAL'], errors='coerce')

    return demanda_fin, demanda_and

def show_team_analysis(df_and, df_fin):
    st.subheader("Demandas por Filtros")

    # 1. Pré-processamento dos dados
    df_and['DAT_INICIO'] = pd.to_datetime(df_and['DAT_INICIO'], dayfirst=True, errors='coerce')
    df_fin['DAT_INICIO'] = pd.to_datetime(df_fin['DAT_INICIO'], dayfirst=True, errors='coerce')
    #df_fin['VLR_TOTAL'] = pd.to_numeric(df_fin['VLR_TOTAL'], errors='coerce').fillna(0)

    # 2. Criar opções para os filtros com "TODOS"
    def get_filter_options(column, df):
        options = df[column].unique().tolist()
        options.insert(0, "TODOS")
        return options

    # 3. Filtros interativos
    col1, col2, col3, col4, col5,col6 = st.columns(6)
    with col1:
        abrangencia_options = get_filter_options('DES_ABRANGENCIA', df_and)
        abrangencia = st.selectbox("Abrangência", abrangencia_options)

    with col2:
        #if
        elemento_options = get_filter_options('DES_ELEMENTO', df_and)
        elemento = st.selectbox("Elemento", elemento_options)

    with col3:
        equipe_options = get_filter_options('DES_EQUIPE', df_and)
        equipe = st.selectbox("Equipe", equipe_options)

    with col4:
        # Novo filtro por palavra-chave na instrução
        keyword = st.text_input("Palavra-chave na Instrução")

    with col5:
        # Novo filtro por palavra-chave na instrução
        situacao_options = get_filter_options('DES_SITUACAO', df_and)
        situacao_options.insert(0, "CONCLUIDO")
        situacao_options.insert(0, "CANCELADO")
        situacao = st.selectbox("SITUAÃÇO", situacao_options)

    with col6:
        # Novo filtro por palavra-chave na instrução
        ret_keyword = st.text_input("Palavra-chave na Retaguarda")



    # 4. Seleção de período
    st.write("Selecione o período de análise:")
    col7, col8 = st.columns(2)
    with col7:
        start_date = st.date_input("Data inicial", value=df_and['DAT_INICIO'].min().date())
    with col8:
        end_date = st.date_input("Data final", value=df_and['DAT_INICIO'].max().date())

    end_date_plus_1 = pd.to_datetime(end_date) + pd.Timedelta(days=1)

    # 5. Aplicar filtros
    mask_and = (
            (df_and['DAT_INICIO'] >= pd.to_datetime(start_date)) &
            (df_and['DAT_INICIO'] < end_date_plus_1)
    )
    mask_fin = (
            (df_fin['DAT_INICIO'] >= pd.to_datetime(start_date)) &
            (df_fin['DAT_INICIO'] < end_date_plus_1)
    )

    # Aplicar filtros adicionais se não for "TODOS"
    if abrangencia != "TODOS":
        mask_and &= (df_and['DES_ABRANGENCIA'] == abrangencia)
        mask_fin &= (df_fin['DES_ABRANGENCIA'] == abrangencia)

    if elemento != "TODOS":
        mask_and &= (df_and['DES_ELEMENTO'] == elemento)
        mask_fin &= (df_fin['DES_ELEMENTO'] == elemento)

    if equipe != "TODOS":
        mask_and &= (df_and['DES_EQUIPE'] == equipe)
        mask_fin &= (df_fin['DES_EQUIPE'] == equipe)

    if situacao != "TODOS":
        mask_and &= (df_and['DES_SITUACAO'] == situacao)
        mask_fin &= (df_fin['DES_SITUACAO'] == situacao)


    # Aplicar filtro por palavra-chave se foi informado
    if keyword:
        mask_and &= (df_and['DES_INSTRUCAO'].str.contains(keyword, case=False, na=False))
        mask_fin &= (df_fin['DES_INSTRUCAO'].str.contains(keyword, case=False, na=False))

    #filtered_and = df_and[mask_and]
    #filtered_fin = df_fin[mask_fin]

    # Aplicar filtro por palavra-chave se foi informado
    if keyword:
        mask_and &= (df_and['DES_OBSERVACAO_RETAGUARDA'].str.contains(ret_keyword, case=False, na=False))
        mask_fin &= (df_fin['DES_OBSERVACAO_RETAGUARDA'].str.contains(ret_keyword, case=False, na=False))

    filtered_and = df_and[mask_and]
    filtered_fin = df_fin[mask_fin]


    # 6. Exibir resultados
    st.subheader(f"Resultados para o período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}")
    if keyword:
        st.caption(f"Filtrado por palavra-chave: '{keyword}'")

    # Métricas resumidas
    col_met1, col_met2, col_met3 = st.columns(3)
    with col_met1:
        st.metric("Demandas Abertas", len(filtered_and))
    with col_met2:
        st.metric("Demandas Encerradas", len(filtered_fin))
    with col_met3:
        total = filtered_fin['VLR_TOTAL'].sum()
        st.metric("Custo Total (R$)", format_currency(total))

    # Tabelas detalhadas
    tab1, tab2 = st.tabs(["Demandas Abertas", "Demandas Encerradas"])

    with tab1:
        if not filtered_and.empty:
            st.dataframe(
                filtered_and[
                    ['DEMANDA', 'DES_ABRANGENCIA', 'DES_ELEMENTO', 'DES_EQUIPE', 'DAT_INICIO', 'DES_INSTRUCAO','DES_OBSERVACAO_RETAGUARDA']]
                .style.format({'DAT_INICIO': lambda x: x.strftime('%d/%m/%Y %H:%M') if pd.notnull(x) else ''})
            )
        else:
            st.warning("Nenhuma demanda aberta encontrada com os filtros selecionados")

    with tab2:
        if not filtered_fin.empty:
            st.dataframe(
                filtered_fin[['DEMANDA', 'DES_ABRANGENCIA', 'DES_ELEMENTO', 'DES_EQUIPE', 'DAT_INICIO', 'VLR_TOTAL',
                              'DES_INSTRUCAO','DES_OBSERVACAO_RETAGUARDA']]
                #.assign(VLR_TOTAL=filtered_fin['VLR_TOTAL'].apply(format_currency))
                .style.format({'DAT_INICIO': lambda x: x.strftime('%d/%m/%Y %H:%M') if pd.notnull(x) else ''})
            )
        else:
            st.warning("Nenhuma demanda encerrada encontrada com os filtros selecionados")

#analisee temporal
# def show_temporal_analysis(df_and, df_fin):
#     st.subheader("Análise temporal")
#
#     # Convert dates
#     df_and['DAT_INICIO'] = pd.to_datetime(
#         df_and['DAT_INICIO'],
#         format='%d/%m/%Y %H:%M',
#         errors='coerce',
#         dayfirst=True
#     )
#
#     df_fin['DAT_INICIO'] = pd.to_datetime(
#         df_fin['DAT_INICIO'],
#         format='%d/%m/%Y %H:%M',
#         errors='coerce',
#         dayfirst=True
#     )
#
#     # Drop rows with invalid dates
#     df_and = df_and.dropna(subset=['DAT_INICIO'])
#     df_fin = df_fin.dropna(subset=['DAT_INICIO'])
#
#     # Time period selection
#     time_range = st.slider(
#         "Select Date Range",
#         min_value=df_and['DAT_INICIO'].min().to_pydatetime(),
#         max_value=df_and['DAT_INICIO'].max().to_pydatetime(),
#         value=(df_and['DAT_INICIO'].min().to_pydatetime(), df_and['DAT_INICIO'].max().to_pydatetime())
#     )
#
#     # Filter data
#     mask_and = (df_and['DAT_INICIO'] >= time_range[0]) & (df_and['DAT_INICIO'] <= time_range[1])
#     mask_fin = (df_fin['DAT_INICIO'] >= time_range[0]) & (df_fin['DAT_INICIO'] <= time_range[1])
#
#     # Plot
#     fig, ax = plt.subplots()
#     df_and[mask_and].set_index('DAT_INICIO').resample('W').size().plot(
#         label='Em Progresso', ax=ax)
#     df_fin[mask_fin].set_index('DAT_INICIO').resample('W').size().plot(
#         label='Completas', ax=ax)
#     ax.set_ylabel('Número de demandas')
#     ax.legend()
#     st.pyplot(fig)


#Função Análise de problemas

# def show_recurring_issues_analysis(df_and, df_fin):
#     st.header("🔍 Análise de Problemas Recorrentes")
#
#     # 1. Configurações na sidebar
#     st.sidebar.header("Configurações de Análise")
#     min_word_length = st.sidebar.slider("Tamanho mínimo das palavras", 3, 7, 4)
#     top_n = st.sidebar.slider("Número de termos principais", 5, 30, 15)
#     mostrar_nuvem = st.sidebar.checkbox("Mostrar Nuvem de Palavras", True)  # Nome consistente em português
#
#     # 2. Unificar e preparar os dados
#     all_instructions = pd.concat([df_and['DES_INSTRUCAO'], df_fin['DES_INSTRUCAO']]).dropna()
#
#     # 3. Função de pré-processamento
#     def preprocess_text(text):
#         if not isinstance(text, str):
#             return []
#         text = text.lower()
#         text = re.sub(r'[^\w\s]', '', text)  # Remove pontuação
#         text = re.sub(r'\d+', '', text)  # Remove números
#         return [word for word in text.split() if len(word) >= min_word_length]
#
#     # 4. Processamento das palavras
#     all_words = []
#     for instruction in all_instructions:
#         all_words.extend(preprocess_text(instruction))
#
#     # 5. Análise de frequência
#     if not all_words:
#         st.warning("Nenhum texto válido encontrado para análise.")
#         return
#
#     word_counts = Counter(all_words)
#     common_words = word_counts.most_common(top_n)
#
#     # 6. Visualização dos resultados
#     st.subheader(f"Top {top_n} Termos Mais Frequentes")
#     df_common_words = pd.DataFrame(common_words, columns=['Termo', 'Frequência'])
#
#     fig = px.bar(df_common_words,
#                  x='Frequência',
#                  y='Termo',
#                  orientation='h',
#                  color='Frequência',
#                  color_continuous_scale='Blues')
#     st.plotly_chart(fig, use_container_width=True)
#
#     # 7. Nuvem de palavras (usando a variável correta)
#     if mostrar_nuvem:  # Agora usando o nome correto da variável
#         st.subheader("Nuvem de Palavras")
#         try:
#             wordcloud = WordCloud(width=800,
#                                   height=400,
#                                   background_color='white',
#                                   colormap='tab20c').generate(' '.join(all_words))
#
#             plt.figure(figsize=(10, 5))
#             plt.imshow(wordcloud, interpolation='bilinear')
#             plt.axis("off")
#             st.pyplot(plt)
#         except Exception as e:
#             st.error(f"Erro ao gerar nuvem de palavras: {str(e)}")

    # 8. Análise de combinação de termos (opcional)


# if len(common_words) >= 2:
# st.sub


# --- Main Execution ---
# Process data

def load_data():
    """Carrega os dados fixos uma vez e mantém em cache"""
    return tratamento(PATH_ANDAMENTO, PATH_FINALIZADA)


def main():
    st.title("📊 SEMAE ELETROMECÂNICA")

    # Carrega dados
    demanda_fin, demanda_and = tratamento(PATH_ANDAMENTO, PATH_FINALIZADA)

    # Adiciona pesquisa
    search_demand(demanda_and, demanda_fin)

    # Processamento adicional
    demanda_and['delay_days'] = (
            pd.to_datetime(demanda_and['DAT_ATUALIZACAO']) -
            pd.to_datetime(demanda_and['DAT_INICIO'])
    ).dt.days

    # Abas do dashboard
    tab1, = st.tabs([ "Análise de Demandas",])

    with tab1:
        show_team_analysis(demanda_and, demanda_fin)


if __name__ == "__main__":
    main()
