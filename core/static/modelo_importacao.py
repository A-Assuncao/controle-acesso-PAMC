import pandas as pd
import os
from pathlib import Path

# Obter o diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent

# Criar DataFrame com as colunas necessárias
df = pd.DataFrame(columns=[
    'NOME',
    'DOCUMENTO',
    'VEÍCULO',
    'SETOR'
])

# Adicionar uma linha de exemplo
df.loc[0] = [
    'João da Silva',
    '12.345.678-9',
    'ABC-1234',
    'Administrativo'
]

# Definir o caminho completo do arquivo
arquivo_path = os.path.join(BASE_DIR, 'modelo_importacao.xlsx')

# Salvar o arquivo
df.to_excel(arquivo_path, index=False, engine='openpyxl') 