import numpy as np
import pandas as pd

def tratamento(file_path_andamento, file_path_finalizada):
    # Lendo os arquivos CSV
    encodings_to_try = ['utf-8', 'latin1', 'ISO-8859-1', 'windows-1252']
    #demanda_and = pd.read_csv(file_path_andamento, encoding= encodig, on_bad_lines='warn', sep=';', header=0, skip_blank_lines=True)
    #demanda_fin = pd.read_csv(file_path_finalizada, encoding= encoding, on_bad_lines='warn', sep=';', header=0, skip_blank_lines=True)

    for encoding in encodings_to_try:
        try:
            demanda_and = pd.read_csv(file_path_andamento, encoding=encoding, on_bad_lines='warn', sep=';', header=0,
                                      skip_blank_lines=True)
            demanda_fin = pd.read_csv(file_path_finalizada, encoding=encoding, on_bad_lines='warn', sep=';', header=0,
                                      skip_blank_lines=True)
            break
        except UnicodeDecodeError:
            continue
    else:
        st.error("Não foi possível ler os arquivos com nenhum dos encodings testados.")
        return None, None

    # Lista de colunas a remover
    colunas_para_remover = ['COD_CONSUMIDOR', 'COD_SITUACAO', 'COD_OCORRENCIA', 'DES_OCORRENCIA', 'DES_RISCO', 'FLG_CONFERIDA']

    # Remove as colunas especificadas se existirem
    demanda_and = demanda_and.drop(columns=[col for col in colunas_para_remover if col in demanda_and.columns])
    demanda_fin = demanda_fin.drop(columns=[col for col in colunas_para_remover if col in demanda_fin.columns])

    # Lista de colunas para atualizar
    colunas_para_atualizar = ['DES_EQUIPE_EXEC', 'DES_ANDAMENTO_EXEC', 'DES_OBSERVACAO_RETAGUARDA','VLR_TOTAL','DAT_INICIO','DAT_ATUALIZACAO']

    # Função auxiliar para substituir valores '<Null>'
    def substituir_nulos(df, colunas, valor_substituto):
        for column in colunas:
            if column in df.columns:
                df[column] = df[column].replace('<Null>', valor_substituto)
        return df

    # Atualizando valores nas colunas para ambos os DataFrames
    demanda_and = substituir_nulos(demanda_and, colunas_para_atualizar, "NÃO INFORMADO")

    demanda_and['DAT_INICIO'] = demanda_and['DAT_INICIO'].replace("NÃO INFORMADO",np.nan)
    demanda_and['DAT_ATUALIZACAO'] = demanda_and['DAT_ATUALIZACAO'].replace("NÃO INFORMADO",np.nan)

    demanda_fin = substituir_nulos(demanda_fin, colunas_para_atualizar, "NÃO INFORMADO")

    demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].replace("NÃO INFORMADO",np.nan)
    demanda_fin['DAT_INICIO'] = demanda_fin['DAT_INICIO'].replace("NÃO INFORMADO",np.nan)
    demanda_fin['DAT_ATUALIZACAO'] = demanda_fin['DAT_ATUALIZACAO'].replace("NÃO INFORMADO",np.nan)

    # limpar as linhas com valores 'NA'')
    demanda_fin = demanda_fin.dropna(subset=['VLR_TOTAL'])


    demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].str.replace(',', '.').astype('float64',errors = 'ignore')
    demanda_fin['VLR_TOTAL'] = pd.to_numeric(demanda_fin['VLR_TOTAL'],errors = 'coerce')

    #demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].str.replace(',', '.').astype('float64')
    demanda_fin['VLR_TOTAL'] = pd.to_numeric(demanda_fin['VLR_TOTAL'],errors = 'coerce')


    # Opcional , retornar os valores para o original
    demanda_fin['VLR_TOTAL'] = demanda_fin['VLR_TOTAL'].astype(float)

    demanda_fin = pd.DataFrame(demanda_fin)
    demanda_and = pd.DataFrame(demanda_and)


    return demanda_fin, demanda_and


