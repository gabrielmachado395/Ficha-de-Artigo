import io
import math
from pprint import pprint
import pyodbc
import pandas as pd
import customtkinter as ctk
from tkinter import Text, messagebox, ttk
from tkinter import Toplevel, Label, Entry
from datetime import datetime, timedelta
import pytz
import re
import os
import qrcode
import json
from PIL import Image, ImageWin
import tkinter as tk
import threading
import unicodedata
from escpos.printer import Usb
import win32print
import win32ui
import requests
import sqlite3
import time #  Importa time
import sys
import subprocess

# URL da sua API (ajustada para o endpoint de check)
UPDATE_URL = "http://168.190.90.2:5000/update/check?platform=windows&app=interface_pc"


def check_for_updates():
    try:
        # 1. Consulta a API
        response = requests.get(UPDATE_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            remote_version = data.get("version_name") 
            # Certifique-se que na API a chave é 'apk_url' ou altere aqui para 'download_url'
            download_url = data.get("apk_url") 

            # 2. Comparação segura de versão (Opcional, mas recomendado)
            # Transforma "2.0.0" em [2, 0, 0] para comparar números reais
            remote_v_list = [int(x) for x in remote_version.split('.')]
            local_v_list = [int(x) for x in APP_VERSION.split('.')]

            if remote_v_list > local_v_list:
                if messagebox.askyesno("Atualização Disponível", 
                                      f"Uma nova versão ({remote_version}) está disponível.\n"
                                      f"O sistema será reiniciado. Deseja atualizar agora?"):
                    perform_update(download_url)
    except Exception as e:
        print(f"Falha ao verificar atualizações: {e}")

def perform_update(url):
    """
    Realiza o download e instalação da atualização com tratamento robusto de processos.
    """
    try:
        import tempfile
        
        # 1. Identifica o executável atual
        current_exe_path = sys.executable
        current_exe_name = os.path.basename(current_exe_path)
        current_dir = os.path.dirname(current_exe_path)

        # Verifica se está rodando via Python (não compilado)
        if "python" in current_exe_name.lower():
            messagebox.showwarning(
                "Aviso", 
                "Você está rodando via Python/VSCode. O update só funcionará no modo Executável (.exe)"
            )
            return

        # 2. Download do novo arquivo para pasta temporária
        print("Baixando atualização...")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Usa pasta temporária do Windows
        temp_dir = tempfile.gettempdir()
        temp_update_file = os.path.join(temp_dir, "temp_update_new.exe")
        
        with open(temp_update_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Download concluído: {temp_update_file}")
        
        # 3. Cria script batch MELHORADO com mais tempo de espera
        batch_path = os.path.join(current_dir, "update_installer.bat")
        
        batch_script = f"""@echo off
title Instalador de Atualizacao
color 0A
echo.
echo ========================================
echo    INSTALADOR DE ATUALIZACAO
echo ========================================
echo.
echo Aguardando fechamento do sistema...
timeout /t 3 /nobreak > nul

REM Força o encerramento do processo
taskkill /F /IM "{current_exe_name}" > nul 2>&1

REM Aguarda o processo terminar completamente
echo Encerrando processos...
timeout /t 5 /nobreak > nul

REM Loop para garantir que o arquivo pode ser deletado
:delete_loop
echo Removendo versao antiga...
del /F /Q "{current_exe_name}" > nul 2>&1
if exist "{current_exe_name}" (
    timeout /t 2 /nobreak > nul
    goto delete_loop
)

REM Copia o novo executável
echo Instalando nova versao...
copy /Y "{temp_update_file}" "{current_exe_name}" > nul

REM Remove o arquivo temporário
del /F /Q "{temp_update_file}" > nul 2>&1

REM Aguarda para garantir que o arquivo foi copiado
timeout /t 2 /nobreak > nul

REM Inicia o novo executável
echo Iniciando aplicacao atualizada...
start "" "{current_exe_name}"

REM Aguarda um pouco antes de auto-deletar
timeout /t 3 /nobreak > nul

REM Auto-deleta o script batch
del "%~f0"
"""
        
        with open(batch_path, "w", encoding="utf-8") as f:
            f.write(batch_script)
        
        print(f"Script de instalação criado: {batch_path}")
        
        # 4. Informa o usuário
        messagebox.showinfo(
            "Atualização Iniciada",
            "O sistema será reiniciado para aplicar a atualização.\n\n"
            "Aguarde alguns segundos..."
        )
        
        # 5. Executa o instalador e encerra imediatamente
        subprocess.Popen(
            batch_path, 
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW  # Executa sem mostrar janela do CMD
        )
        
        # 6. Força o encerramento imediato do aplicativo atual
        time.sleep(1)  # Pequeno delay para o batch iniciar
        os._exit(0)
        
    except requests.exceptions.RequestException as req_err:
        messagebox.showerror(
            "Erro de Download", 
            f"Falha ao baixar a atualização:\n{req_err}\n\n"
            "Verifique sua conexão com a internet."
        )
        print(f"Erro de requisição: {req_err}")
        
    except Exception as e:
        messagebox.showerror(
            "Erro Crítico", 
            f"Falha ao aplicar atualização:\n{e}\n\n"
            "Tente novamente mais tarde ou contate o suporte."
        )
        print(f"Erro inesperado: {e}")
        import traceback
        traceback.print_exc()

PESO_LABEL      = "Peso (KG)"
TAMBORES_LABEL  = "Tambores"

# icon = "C:/FichaArtigo/icon_form.ico"
APP_VERSION = "2.0.0"

data_atual = datetime.now()
data_formatada = data_atual.strftime("%d/%m/%Y")

#  Constantes do SQLite 
DATABASE_NAME = "cache.db"
# Horários de atualização dos dados do sqlite
SCHEDULED_HOURS = [6, 14, 22]

def check_and_print_cache_status(nome_tabela, num_samples=5):
    """Conecta-se ao cache.db, imprime o status e os primeiros N registros de uma tabela."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # 1. Obter a contagem total
        cursor.execute(f"SELECT COUNT(*) FROM {nome_tabela}")
        count = cursor.fetchone()[0]

        # 2. Obter os N primeiros registros
        cursor.execute(f"SELECT * FROM {nome_tabela} LIMIT {num_samples}")
        registros = cursor.fetchall()
        
        if count > 0:
            print(f"\n=======================================================")
            print(f"✅ CACHE DE DADOS (SQLite) - Tabela '{nome_tabela.upper()}'")
            print(f"   Status: {count} registros salvos com sucesso.")
            
            # Pega os nomes das colunas
            cursor.execute(f"PRAGMA table_info({nome_tabela})")
            colunas = [info[1] for info in cursor.fetchall()]
            print(f"   Colunas: {colunas}")
            
            print(f"   Amostra dos primeiros {num_samples} registros (Ordem, Qtd, SKU...):")
            for linha in registros:
                # Imprime apenas os 4 primeiros campos para brevidade
                print(f"   > {linha[:4]}...") 
            
            if count > num_samples:
                print(f"   ... e mais {count - num_samples} registros.")
            print(f"=======================================================")
        else:
            print(f"\n=======================================================")
            print(f"⚠️ CACHE DE DADOS (SQLite) - Tabela '{nome_tabela.upper()}'")
            print("   Status: Tabela vazia. O cache será populado pela thread de atualização periódica.")
            print(f"=======================================================")
            
        conn.close()
        
    except sqlite3.OperationalError as e:
        print(f"❌ Erro ao inspecionar a tabela '{nome_tabela}' no cache: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado ao verificar cache: {e}")

# --- Funções de Gerenciamento do SQLite ---
def init_db():
    """Cria o banco de dados e as tabelas se não existirem."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Tabela para Dados Principais (ordens)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ordens (
            NrOrdem TEXT PRIMARY KEY,
            Qtd REAL,
            SKU TEXT,
            DtPedido TEXT,
            Cliente TEXT,
            Maquina TEXT,
            PedidoEspecial TEXT,
            MetrosEstimados REAL,
            Caixa TEXT
        )
    """)

    # Tabela para Gramatura (gramaturaByArtigo) - Usada para cache de Gramatura
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gramaturas (
            ArtigoCompleto TEXT PRIMARY KEY,
            Gramatura REAL,
            CdMae INTEGER
        )
    """)

    # Tabela para Operador (operador)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operadores (
            Matricula TEXT PRIMARY KEY,
            Operador TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Banco de dados SQLite inicializado.")

def _calculate_sleep_time_to_next_schedule(scheduled_hours):
    """
    Calcula o tempo de espera em segundos até a próxima hora agendada (em Brasília/São Paulo).
    Retorna a duração do sleep (em segundos) e o horário da próxima execução (str).
    """
    brasilia_tz = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(brasilia_tz)
    
    next_run_time = None
    
    # Tenta encontrar a próxima hora agendada no dia de hoje
    for hour in sorted(scheduled_hours):
        # Cria um objeto datetime para a hora agendada de hoje
        scheduled_time_today = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        
        # Se o horário agendado de hoje for no futuro (damos 1 segundo de margem para o passado)
        if scheduled_time_today > now + timedelta(seconds=1):
             next_run_time = scheduled_time_today
             break

    # Se não encontrou hora hoje, usa a primeira hora agendada do dia seguinte
    if next_run_time is None:
        next_run_hour = min(scheduled_hours)
        next_run_time = now.replace(hour=next_run_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)

    # Garante que a data/hora encontrada seja no futuro
    if next_run_time <= now: 
        # Isso só deve acontecer se a thread iniciar exatamente no segundo 0 da hora agendada
        # ou se a lógica não encontrou a hora correta. Força para o dia seguinte.
        next_run_time += timedelta(days=1) 
        
    sleep_duration = (next_run_time - now).total_seconds()
        
    return sleep_duration, next_run_time.strftime("%H:%M:%S")

# Função Auxiliar para salvar ordens no DB  >>>
def _save_ordens_data(data):
    """Salva a lista de ordens (data) na tabela 'ordens'."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        for item in data:
            metros_estimados = item.get("MetrosEstimados")
            try:
                # Usa .replace(',', '.') para garantir que a API data (se vier com vírgula) seja float
                metros_estimados = float(str(metros_estimados).replace(',', '.'))
            except (ValueError, TypeError):
                metros_estimados = 0.0 # Define 0.0 se for inválido/nulo
                
            cursor.execute("""
                REPLACE INTO ordens (NrOrdem, Qtd, SKU, DtPedido, Cliente, Maquina, PedidoEspecial, MetrosEstimados, Caixa)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("NrOrdem"), 
                item.get("Qtd"), 
                item.get("SKU"), 
                item.get("DtPedido"), 
                item.get("Cliente"), 
                item.get("Maquina"), 
                item.get("PedidoEspecial"), 
                metros_estimados, 
                item.get("Caixa")
            ))
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao salvar dados de ordens no cache: {e}")



# <<< NOVO: FUNÇÃO DE BUSCA/ATUALIZAÇÃO PERIÓDICA DE ORDEM >>>
def fetch_and_update_ordens_cache():
    """Busca dados da API (tinturariaDados) e atualiza a tabela 'ordens'."""
    try:
        base_url = "http://168.190.90.2:5000//consulta/tinturariaDados"
        response = requests.get(base_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list):
                _save_ordens_data(data)
                print("✅ ATUALIZAÇÃO PERIÓDICA: Cache de ordens atualizado com sucesso.")
                return True
            else:
                print("⚠️ ATUALIZAÇÃO PERIÓDICA: API de ordens retornou dados vazios ou inválidos.")
        else:
            print(f"❌ ATUALIZAÇÃO PERIÓDICA: Erro HTTP {response.status_code} ao buscar dados de ordens.")
    except requests.exceptions.RequestException as e:
        print(f"❌ ATUALIZAÇÃO PERIÓDICA: Erro de conexão com a API de Ordens: {e}")
    except Exception as e:
        print(f"❌ ATUALIZAÇÃO PERIÓDICA: Erro inesperado ao atualizar cache de ordens: {e}")
    return False

def run_periodic_ordens_update():
    """Função que roda em loop infinito para manter o cache de ordens atualizado, nos horários agendados.""" # MODIFICADO
    time.sleep(10) # Aguarda 10s para a aplicação iniciar
    print(f"\n[CACHE MANAGER] Início da atualização periódica do cache de ORDEM (agendado para {SCHEDULED_HOURS}:00).") # MODIFICADO
    
    # Executa a primeira vez imediatamente, antes de entrar no loop de espera
    fetch_and_update_ordens_cache() 
    
    while True:
        try:
            # Calcula o tempo de espera até a próxima hora agendada
            sleep_duration, next_run_time_str = _calculate_sleep_time_to_next_schedule(SCHEDULED_HOURS) # MODIFICADO
            
            print(f"\n[CACHE MANAGER] Próxima atualização de ORDEM agendada para: {next_run_time_str} (Duração de espera: {int(sleep_duration)}s).") # MODIFICADO
            
            # Espera a duração calculada
            time.sleep(sleep_duration) # MODIFICADO
            
            # Atualiza
            fetch_and_update_ordens_cache()
            
        except Exception as e:
            print(f"❌ ERRO GRAVE no loop periódico de ORDEM: {e}. Tentando novamente em 30s.")
            time.sleep(30)


#  FUNÇÃO DE BUSCA/ATUALIZAÇÃO PERIÓDICA DE OPERADORES >>>
def fetch_and_update_operadores_cache():
    """Busca todos os operadores da API e atualiza a tabela 'operadores'."""
    try:
        base_url = "http://168.190.90.2:5000//consulta/operador"
        response = requests.get(base_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and data:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                
                # Otimização: Limpa a tabela antes de inserir todos os novos dados
                cursor.execute("DELETE FROM operadores")
                
                for item in data:
                    matricula = str(item.get("Matricula")).strip()
                    nome_operador = item.get("Operador")
                    
                    if matricula and nome_operador:
                        cursor.execute("""
                            REPLACE INTO operadores (Matricula, Operador)
                            VALUES (?, ?)
                        """, (matricula, nome_operador))
                
                conn.commit()
                conn.close()
                print("✅ ATUALIZAÇÃO PERIÓDICA: Cache de operadores atualizado com sucesso.")
                return True
            else:
                print("⚠️ ATUALIZAÇÃO PERIÓDICA: API de Operadores retornou dados vazios ou inválidos.")
                
        else:
            print(f"❌ ATUALIZAÇÃO PERIÓDICA: Erro HTTP {response.status_code} ao buscar lista de operadores.")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ATUALIZAÇÃO PERIÓDICA: Erro de conexão com a API de Operadores: {e}")
    except Exception as e:
        print(f"❌ ATUALIZAÇÃO PERIÓDICA: Erro inesperado ao atualizar cache de operadores: {e}")
    return False

def run_periodic_operadores_update():
    """Função que roda em loop infinito para manter o cache de operadores atualizado."""
    time.sleep(20) # Aguarda 20s para a aplicação iniciar
    print(f"[CACHE MANAGER] Início da atualização periódica do cache de OPERADORES.")
    
    # Executa a primeira vez imediatamente, depois entra no loop
    fetch_and_update_operadores_cache()
    
    while True:
        try:
            # Calcula o tempo de espera até a próxima execução agendada
            sleep_duration, next_run_time_str = _calculate_sleep_time_to_next_schedule(SCHEDULED_HOURS)
            print(f"[CACHE MANAGER] Próxima atualização de OPERADORES agendada para: {next_run_time_str} (Duração de espera: {int(sleep_duration)}s).")
            
            # Espera o intervalo
            time.sleep(sleep_duration)
            # Atualiza
            fetch_and_update_operadores_cache()
            
        except Exception as e:
            print(f"❌ ERRO GRAVE no loop periódico de OPERADOR: {e}. Tentando novamente em 30s.")
            time.sleep(30)
# --- Fim das Funções de Atualização Periódica ---


# --- Função para dividir Artigo e Cor ---
# ... (Função dividir_artigo_cor permanece inalterada) ...
def dividir_artigo_cor(texto_completo):
    # ... (código) ...
    if not texto_completo:
        return "", ""
    
    # Lista de cores comuns para identificar
    cores = [
        'preto', 'branco', 'azul', 'vermelho', 'verde', 'amarelo', 
        'cinza', 'rosa', 'roxo', 'laranja', 'marrom', 'bege',
        'nude', 'cru', 'natural', 'colorido', 'estampado'
    ]
    
    texto_lower = texto_completo.lower()
    

    padrao_medida = r'(.*?)\s*(\d*\s*(?:mm|cm))\s+(.+)'
    match_medida = re.search(padrao_medida, texto_completo, re.IGNORECASE)
    
    if match_medida:
        # Artigo = Grupo 1 + Grupo 2 (tudo até a medida)
        artigo = f"{match_medida.group(1).strip()} {match_medida.group(2).strip()}"
        # Cor = Grupo 3 (tudo depois da medida)
        cor = match_medida.group(3).strip()
        
        return artigo.strip(), cor.strip()
    
    # Padrão 2: Procura por cores conhecidas
    for cor_palavra in cores:
        if cor_palavra in texto_lower:
            pos = texto_lower.find(cor_palavra)
            artigo = texto_completo[:pos].strip()
            cor = texto_completo[pos:].strip()
            return artigo, cor
    
    # Padrão 3: Se tiver "c/" ou "com", divide ali
    for separador in [' c/', ' com ']:
        if separador in texto_lower:
            pos = texto_lower.find(separador)
            # Volta um pouco para pegar a palavra anterior
            palavras_antes = texto_completo[:pos].strip().split()
            if len(palavras_antes) > 0:
                # Pega a última palavra antes do separador como início da cor
                ultima_palavra_pos = texto_completo[:pos].rfind(palavras_antes[-1])
                artigo = texto_completo[:ultima_palavra_pos].strip()
                cor = texto_completo[ultima_palavra_pos:].strip()
                return artigo, cor
    
    # Se não encontrou nenhum padrão, retorna tudo como artigo
    return texto_completo, ""
# ...

#  Busca Gramatura pelo Artigo + Cor (COM CACHE - AINDA SOB DEMANDA) >>>
# ... (fetch_gramatura_by_artigo permanece inalterada, pois é sob demanda) ...
def fetch_gramatura_by_artigo(artigo_nome_completo):
    """
    Busca a gramatura de um artigo completo (Artigo + Cor) na API.
    Se falhar, tenta o cache SQLite.
    Sempre atualiza o cache SQLite se a API estiver disponível.
    """
    # 1. TENTATIVA DE BUSCA DA API
    try:
        base_url = "http://168.190.90.2:5000/consulta/allArtigos"
        params = {"artigo_nome": artigo_nome_completo} 
        response = requests.get(base_url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, dict):
                gramatura_str = str(data.get("Gramatura", "0.00")).replace(',', '.')
                cd_mae = data.get("CdMae")
                
                # ATUALIZA O CACHE
                try:
                    conn = sqlite3.connect(DATABASE_NAME)
                    cursor = conn.cursor()
                    cursor.execute("""
                        REPLACE INTO gramaturas (ArtigoCompleto, Gramatura, CdMae)
                        VALUES (?, ?, ?)
                    """, (artigo_nome_completo, gramatura_str, cd_mae))
                    conn.commit()
                    conn.close()
                    print(f"✅ Gramatura para {artigo_nome_completo} salva no cache (sob demanda).")
                except Exception as e:
                    print(f"❌ Erro ao atualizar cache de gramatura: {e}")
                    
                return gramatura_str
            else:
                return "0.00"
            
        elif response.status_code == 404:
            print(f"❌ Gramatura não encontrada na API para {artigo_nome_completo}. Tentando cache...")
        else:
            print(f"❌ Erro HTTP {response.status_code} ao buscar gramatura: {response.text}. Tentando cache...")

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão com a API de Gramatura: {e}. Tentando cache...")
    except Exception as e:
        print(f"❌ Erro inesperado ao tentar API de Gramatura: {e}. Tentando cache...")
        
    # 2. BUSCA DO CACHE SQLite
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT Gramatura FROM gramaturas WHERE ArtigoCompleto = ?", (artigo_nome_completo,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            gramatura_cache = str(result[0]).replace(',', '.') 
            print(f"✅ Gramatura {gramatura_cache} carregada do cache para {artigo_nome_completo}.")
            return gramatura_cache
    except Exception as e:
        print(f"❌ Erro ao ler cache de gramatura: {e}")
        
    return "0.00"


# --- Função de Busca de Dados Principal Atualizada (COM CACHE - API-FIRST) ---
def fetch_data_from_db(search_term=None, peso=None):
    """
    Busca dados da API (para garantir o dado mais atual na inicialização/refresh). 
    Se falhar, carrega do cache SQLite.
    
    Args:
        search_term: Termo de busca opcional
        peso: Peso em KG para calcular a Caixa (opcional)
    """
    data = None
    
    # 1. TENTATIVA DE BUSCA DA API (API-FIRST para tela inicial/refresh)
    try:                
        base_url = "http://168.190.90.2:5000//consulta/tinturariaDados"
        
        # Adiciona o parâmetro peso se fornecido
        params = {}
        if peso is not None:
            params['peso'] = peso
            
        response = requests.get(base_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Sucesso: Dados principais obtidos da API.")
            # Salva o dado mais atual imediatamente no cache.
            _save_ordens_data(data) 
        else:
            print(f"❌ Erro HTTP {response.status_code}: {response.text}. Tentando cache...")

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão com a API: {e}. Tentando cache...")
    except Exception as e:
        print(f"❌ Erro inesperado ao tentar API: {e}. Tentando cache...")

    # 2. BUSCA DO CACHE SQLite SE A API FALHAR OU RETORNAR DADOS VAZIOS/INVÁLIDOS
    if data is None or not isinstance(data, list) or not data:
        print("⏳ Carregando dados do cache SQLite...")
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            df_cache = pd.read_sql_query(
                """SELECT NrOrdem, Qtd, SKU, DtPedido, Cliente, Maquina, PedidoEspecial, MetrosEstimados, Caixa, Peso 
                FROM ordens ORDER BY NrOrdem DESC""", 
                conn
            )
            conn.close()
            
            data = df_cache.to_dict('records')
            if not data:
                print("⚠️ Cache SQLite de ordens vazio. Retornando None.")
                return None
            else:
                print(f"✅ Sucesso: {len(data)} registros carregados do cache SQLite.")
        except Exception as e:
            print(f"❌ Erro ao ler dados do cache SQLite: {e}")
            return None

    # 3. PROCESSAMENTO E FILTRAGEM (O restante do código permanece igual)
    try:
        df = pd.DataFrame(data)

        # Normaliza nomes de colunas
        rename_map = {
            "NrOrdem": "Ordem",
            "Qtd": "Quantity",
            "SKU": "ArtigoCompleto",
            "DtPedido": "DtOrdem",
            "Cliente": "Cliente",
            "Maquina": "Maquina",
            "PedidoEspecial": "PedidoEspecial",
            "MetrosEstimados": "Gramatura", 
            "Caixa": "Caixa",
            "Peso": "Peso"  # Adiciona o mapeamento do Peso
        }

        df.rename(columns=rename_map, inplace=True)

        # Converte Cliente para maiúsculas
        if "Cliente" in df.columns:
            df['Cliente'] = df['Cliente'].str.upper()

        if "ArtigoCompleto" in df.columns:
            df['ArtigoCompleto'] = df['ArtigoCompleto'].astype(str).str.upper()
        
        # Divide ArtigoCompleto em Artigo e Cor
        if "ArtigoCompleto" in df.columns:
            df[['Artigo', 'Cor']] = df['ArtigoCompleto'].apply(
                lambda x: pd.Series(dividir_artigo_cor(x))
            )
        else:
            df['Artigo'] = ""
            df['Cor'] = ""

        if "Artigo" in df.columns:
            df['Artigo'] = df['Artigo'].astype(str).str.upper()
        if "Cor" in df.columns:
            df['Cor'] = df['Cor'].astype(str).str.upper()

        # Formatação do Volume Programado (Quantity) para o display
        if "Quantity" in df.columns:
            df['Quantity_Raw'] = pd.to_numeric(df['Quantity'], errors='coerce') 
            
            def formatar_volume_display(valor):
                if pd.isna(valor):
                    return "0,00"
                if valor == int(valor):
                    return f"{int(valor):,.0f}".replace(",", "_TEMP_").replace(".", ",").replace("_TEMP_", ".")
                else:
                    return f"{valor:,.2f}".replace(",", "_TEMP_").replace(".", ",").replace("_TEMP_", ".")

            df['Quantity_Display'] = df['Quantity_Raw'].apply(formatar_volume_display)
            df['Quantity'] = df['Quantity_Raw'].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "0.0000")
        else:
            df['Quantity_Display'] = "0.00"

        # Garante todas as colunas na ordem correta (incluindo Peso)
        expected_cols = ["Ordem", "Quantity_Display", "Artigo", "Cor", "DtOrdem", "Cliente", "Maquina", "PedidoEspecial", "Gramatura", "Caixa", "Peso", "Quantity"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""

        df = df[expected_cols]

        # Formata datas
        if "DtOrdem" in df.columns:
            df["DtOrdem"] = pd.to_datetime(df["DtOrdem"], errors="coerce", dayfirst=True).dt.strftime("%d/%m/%Y")

        # 4. APLICA O FILTRO DE PESQUISA (se houver)
        if search_term:
            search_value = str(search_term)
            if 'Ordem' in df.columns:
                df['Ordem'] = df['Ordem'].astype(str)
                df = df[
                    df['Ordem'].str.contains(search_value, case=False, na=False)
                ]
            
        return df

    except Exception as e:
        print(f"❌ Erro ao processar ou buscar dados (API/Cache): {e}")
        return None


def split_text(text, max_width, hdc, font=None):
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        size = hdc.GetTextExtent(test_line)
        if size[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def populate_treeview(tree, dataframe):
    # A Treeview exibirá as colunas visíveis, mas todas as colunas do DF (incluindo Gramatura, Caixa e Quantity_Raw)
    for row in tree.get_children():
        tree.delete(row)

    if dataframe is not None:
        for index, row in dataframe.iterrows():
            # A Treeview usará todas as colunas do DF para o valor (inclusive Gramatura, Caixa e Quantity)
            tree.insert("", "end", values=list(row)) 


def mascara_data(event):
    texto = event.widget.get()
    texto = re.sub(r'\D', '', texto)

    if len(texto) > 2:
        texto = f"{texto[:2]}/{texto[2:]}"
    if len(texto) > 5:
        texto = f"{texto[:5]}/{texto[5:]}"

    texto = texto[:10]

    if len(texto) == 10:
        try:
            datetime.strptime(texto, '%d/%m/%Y')
        except ValueError:
            texto = texto[:6]

    event.widget.delete(0, tk.END)
    event.widget.insert(0, texto)

def apply_button_style(button):
    button.configure(
        fg_color="#A31D1D",
        text_color="white",
        hover_color="#D3D3D3",
        font=("Arial", 12, "bold"),
        width=150,
    )

def on_enter(event, button):
    button.configure(
        fg_color="#D3D3D3",
        text_color="black"
    )

def on_leave(event, button):
    button.configure(
        fg_color="#A31D1D",
        text_color="white"
    )

def get_turno():
    brasilia_time = datetime.now(pytz.timezone("America/Sao_Paulo"))
    hour = brasilia_time.hour

    if 6 <= hour < 14:
        return "A"
    elif 14 <= hour < 22:
        return "B"
    else:
        return "C"

#  Busca nome do Operador (CACHE-FIRST) >>>
def fetch_operator_name(matricula):
    """
    Busca o nome do operador no cache SQLite. 
    Se não for encontrado, retorna 'Operador não encontrado'.
    """
    matricula_str = str(matricula).strip()
    
    # 1. BUSCA DO CACHE SQLite (Prioridade)
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT Operador FROM operadores WHERE Matricula = ?", (matricula_str,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print(f"✅ Operador '{result[0]} (via cache)' carregado para matrícula {matricula_str}.")
            return result[0]
        
        # 2. SE NÃO ESTIVER NO CACHE
        print(f"⚠️ Matrícula {matricula_str} não encontrada no cache de operadores.")
        
    except Exception as e:
        print(f"❌ Erro ao ler cache de operador: {e}")

    return "Operador não encontrado" # Retorno final se não encontrar no cache ou erro.
    

def update_operator_name(event, entry):
    # 1. Obtém o valor e remove espaços em branco (se houver) para verificar se está vazio
    matricula = entry.get().strip()

    # ADIÇÃO DA VERIFICAÇÃO: Se a matrícula estiver vazia, encerra a função
    if not matricula:
        # Adicionalmente, se o campo contiver um texto de erro indesejado, limpa o campo
        current_text = entry.get()
        if current_text in ["Operador não encontrado", "Matrícula inválida ou não numérica"]:
             entry.delete(0, "end")
        return # Sai da função se estiver vazio

    # Se chegou até aqui, a matrícula não está vazia, e a busca é realizada.
    nome = fetch_operator_name(matricula)

    if nome and nome not in ["Erro ao buscar operador", "Operador não encontrado", "Matrícula inválida ou não numérica"]:
        entry.delete(0, "end")
        entry.insert(0, nome)
    elif nome in ["Matrícula inválida ou não numérica", "Operador não encontrado"]:
        entry.delete(0, "end")
        entry.insert(0, nome)
        entry.focus_set()
        entry.selection_range(0, tk.END)

def remover_acentos(texto):
    if texto is None:
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    position_top = int(screen_height / 2 - height / 2)
    position_right = int(screen_width / 2 - width / 2)
    window.geometry(f"{width}x{height}+{position_right}+{position_top}")

# Formatação de Entradas Decimais (Peso e Gramatura) - AGORA USAPONTO
def formatar_decimal_input(event, entrada):
    """Formata a entrada para um número decimal, permitindo ponto/vírgula, usando PONTO para display."""
    texto = entrada.get()
    
    # 1. Normalizar para ponto (para validação interna)
    texto = texto.replace(",", ".")
    
    # 2. Remover caracteres não numéricos exceto o primeiro ponto
    limpo = ""
    ponto_encontrado = False
    for char in texto:
        if char.isdigit():
            limpo += char
        elif char == "." and not ponto_encontrado:
            limpo += char
            ponto_encontrado = True
    texto_limpo_ponto = limpo
            
    # 3. Limitar a 3 casas decimais (Ajustado de 2 para 3)
    if "." in texto_limpo_ponto:
        partes = texto_limpo_ponto.split(".")
        
        # Garante que, se houver mais de um ponto (o que não deve acontecer após o filtro, mas por segurança)
        if len(partes) > 2:
            texto_limpo_ponto = partes[0] + "." + "".join(partes[1:])
        
        # Limita a parte decimal a 3 dígitos
        if len(partes) > 1 and len(partes[1]) > 3:
            texto_limpo_ponto = partes[0] + "." + partes[1][:3] 
        
    # 4. Atualizar a entrada (mantém o PONTO no display)
    entrada.delete(0, tk.END)
    entrada.insert(0, texto_limpo_ponto)

# Formatação de Saída do Peso (X.XXX) - AGORA USA PONTO
def formatar_peso_output(event, entrada):
    """Formata o valor do Peso (KG) para o padrão X.XXX ao perder o foco."""
    texto = entrada.get()
    
    try:
        # 1. Substituir vírgula por ponto e converter para float
        valor_float = float(str(texto).replace(",", "."))
        
        # 2. Formatar para 3 casas decimais com ponto (o que transforma 8.2 em 8.200)
        texto_formatado_ponto = "{:.3f}".format(valor_float)
        
        # 3. Substituir o ponto por vírgula para a saída na interface (REMOVIDO: USAR PONTO)
        texto_final = texto_formatado_ponto
        
    except ValueError:
        # Se a conversão falhar (vazio ou texto inválido), define como "0.000"
        texto_final = "0.000"
        
    # 4. Atualizar a entrada
    entrada.delete(0, tk.END)
    entrada.insert(0, texto_final)
    
# Formatação de Inteiro para Quantidade de Cópias
def formatar_inteiro(event, entrada):
    texto = entrada.get()
    texto = re.sub(r'\D', '', texto) # Remove caracteres não numéricos

    if not texto:
        # Permite ficar vazio temporariamente, mas será validado antes de imprimir
        return
    
    if texto.startswith('0') and len(texto) > 1:
        texto = texto.lstrip('0')
    
    if len(texto) > 2: # Limita a 2 dígitos (máx. 99 cópias)
        texto = texto[:2]
        
    entrada.delete(0, tk.END)
    entrada.insert(0, texto)

# LÓGICA DE CÁLCULO DE METROS ROBUSTA - AGORA USA PONTO NO RETORNO
def calcular_metros(peso_str, gramatura_valor):
    """Calcula os metros estimados (Peso * 1000) / Gramatura. Retorna com PONTO."""
    # 1. Obter Peso
    try:
        # Tenta obter o peso, convertendo ',' para '.' e garantindo que é string
        peso = float(str(peso_str).replace(",", "."))
    except (ValueError, TypeError):
        peso = 0.0

    # 2. Obter Gramatura
    try:
        # Tenta converter a gramatura. Se falhar (vazio, texto), usa 0.0.
        gramatura_val = float(str(gramatura_valor).replace(",", "."))
    except (ValueError, TypeError):
        gramatura_val = 0.0 # Se gramatura inválida/vazia, usa 0.0

    # 3. Realizar Cálculo e Formatação
    if peso > 0 and gramatura_val > 0:
        try:
            metros_float = (peso * 1000) / gramatura_val
            
            # 🟢 NOVO CÓDIGO DE FORMATAÇÃO
            
            # 1. Converte para inteiro (remove casas decimais: 15000.75 -> 15000)
            metros_int = int(metros_float) 
            
            # 2. Formata o inteiro: f'{int:,}' adiciona vírgula como separador de milhar (15,000)
            # 3. Substitui a vírgula por ponto (padrão brasileiro para milhar: 15.000)
            metros_formatado = f"{metros_int:,}".replace(",", ".")
            
            return metros_formatado
            
        except ZeroDivisionError:
            # Não deve ocorrer, mas é uma segurança
            return "0"
    else:
        # Se o peso é 0, ou se a gramatura é 0/inválida (com peso > 0)
        return "0.00" 

# NOVO: LÓGICA DE CÁLCULO DE DISTRIBUIÇÃO ROBUSTA
def calcular_distribuicao(metros_str, caixa_str):
    # 1. Obter Metros (espera PONTO como separador)
    try:
        metros = float(str(metros_str).replace(",", "."))
    except (ValueError, TypeError):
        metros = 0.0

    # 2. Obter Caixa (espera um inteiro)
    try:
        caixa = int(str(caixa_str).strip())
    except (ValueError, TypeError):
        caixa = 0 

    # 3. Realizar Cálculo
    if metros > 0 and caixa > 0:
        try:
            distribuicao = metros / caixa
            return f"{distribuicao:.2f}"
        except ZeroDivisionError:
            return "0.00"
    else:
        return "0.00" 



																			
def formatar_volume_para_exibicao(volume_str):
    """
    Recebe o volume como string (ex: '1500.0000') e 
    retorna no formato com ponto decimal (ex: '1500.00').
    """
    try:
        # 1. Limpa a string de entrada, garantindo que use ponto para a conversão
        volume_limpo = str(volume_str).replace(',', '.').replace('.', '', volume_str.count('.') - 1)
								  
        
        # 2. Converte para float
        volume_float = float(volume_limpo)

        # 3. Formata o float para string com 2 casas decimais e PONTO DECIMAL
        # O f-string padrão do Python usa '.' como separador decimal.
        return f"{volume_float:.3f}" 

    except (ValueError, TypeError):
        # Retorna o valor zerado no formato com ponto
        return "0.00"


    except ValueError:
        # Retorna 0,00 se a conversão falhar
        return "0,00"
# ------------------------------------------------------------------------------------

# ====================================================================
# FUNÇÃO OPEN_ORDER_DETAILS AJUSTADA PARA AUTOCOMPLETE E GRAMATURA E CAIXA
# ====================================================================
def open_order_details(order_number=None, artigo=None, cor=None, machine=None, client=None, order_date=None, quantity=None, pedido_especial=None, gramatura=None, caixa=None, autocomplete_data=None, peso=None, metros=None):
    
    # Lista de dados de Artigo e Cor (Artigo, Cor) para o autocomplete
    if autocomplete_data is None:
        autocomplete_data = []

    form_window = Toplevel()
    form_window.title("Ficha do Artigo")
    
    # Determina se é uma nova ordem (order_number vazio)
    is_new_order = not order_number
    
    # Título ajustado para Nova Ordem
    if is_new_order: 
        form_window.title("Adicionar Nova Ordem")

    window_width = 350
    window_height = 630 # Ajustado a altura

    form_window.resizable(False, False)

    center_window(form_window, window_width, window_height)

    # Armazena o valor da Gramatura em uma lista mutável 
    # AJUSTADO: Normaliza o valor inicial da gramatura para PONTO para o estado interno
    initial_gramatura_value = gramatura.replace(',', '.') if gramatura else "0.00"
    gramatura_state = [initial_gramatura_value]
    
    # NOVO: Estado para gerenciar o debounce do autocomplete (ID da função agendada)
    after_id_state = [None] 


    # NOVO: Inclusão dos campos Gramatura, Caixa e Distribuição na tabela_infos
    tabela_infos = [
        #["Pedido Especial", "PedidoEspecial"],
        ["Ordem", "Ordem"],
        ["Artigo", "Artigo"],
        ["Cor", "Cor"],
        ["Volume Prog", "Quantity"],
        ["Data Tingimento", "data_tingimento"],
        ["Elasticidade Acab", "elasticidade_acab"],
        ["Largura Acab", "largura_acab"],
        ["Cliente", "Cliente"],
        ["MTF", "mtf"],
        ["Nº Cortes", "num_cortes"],
        ["Operador", "operador"],
        ["Turno", "turno"],
        ["Tambores", "num_tambores"],
        ["Caixa", "Caixa"], # << ADICIONADO
        ["Peso (KG)", "peso"],
        ["Metros", "metros"],
        ["Observações", "obs"]
    ]

    entries = {}
    order_details = {}

    # Campos que SÃO SEMPRE readonly (bloqueados na nova ordem e na existente):
    readonly_always = ["Volume Prog", "Turno", "Metros"]
    
    # Campos que SÃO readonly SE for uma ordem existente (double-click):
    readonly_if_existing = [ 
        "Ordem", "Artigo", "Cor", "Cliente", "Volume Prog" 
    ]
    
    # Campos que devem ser readonly em qualquer situação (Gramatura, Cor, Caixa)
    readonly_fixed = ["Cor", "Gramatura (g/m²)", "Caixa", "Distribuição"] # <<< MODIFICADO: Distribuição é readonly
    
    # Variável que será a Listbox (precisa ser acessível pelas funções internas)
    autocomplete_listbox = None

    # <<< FUNÇÃO PARA ATUALIZAR O CAMPO DISTRIBUIÇÃO >>>
    def atualizar_distribuicao(event=None):
        """Função chamada para atualizar o campo Distribuição."""
        if "Metros" not in entries or "Distribuição" not in entries or "Caixa" not in entries:
            return
            
        # Metros está com PONTO no seu valor de Entry (calculado por calcular_metros)
        metros_str = entries["Metros"].get()
        # Caixa está com o valor digitado (inteiro)
        caixa_str = entries["Caixa"].get() 

        distribuicao_calculada = calcular_distribuicao(metros_str, caixa_str)

        entries["Distribuição"].config(state="normal")
        entries["Distribuição"].delete(0, tk.END)
        entries["Distribuição"].insert(0, distribuicao_calculada)
        entries["Distribuição"].config(state="readonly")


    def calcular_e_atualizar_caixa(peso_str, nr_ordem):
        """
        Chama o endpoint do Flask para calcular a Caixa com base no peso 
        e atualiza o campo. Executado em uma thread separada.
        """
        try:
            # 💡 AJUSTE ESTA URL/PORTA PARA ONDE SEU FLASK ESTÁ RODANDO
            API_BASE_URL = "http://168.190.90.2:5000" 
            url = f"{API_BASE_URL}/consulta/tinturariaDados"
            
            # Remove vírgula e garante que o peso é um número válido para a URL
            peso_limpo = peso_str.replace(',', '.').strip()
            
            if not peso_limpo or float(peso_limpo) == 0:
                caixa_calculada = "0"
            else:
                params = {
                    'ordem': nr_ordem, # Busca apenas por esta ordem
                    'peso': peso_limpo  # Aplica o novo peso ao cálculo
                }
                
                # Timeout para evitar que a thread bloqueie indefinidamente
                response = requests.get(url, params=params, timeout=5) 
                response.raise_for_status() 
                
                data = response.json()
                
                # O Flask retorna uma lista de registros, precisamos do primeiro
                if data and isinstance(data, list) and len(data) > 0:
                    registro = data[0]
                    # Caixa é o campo retornado pelo SQL
                    caixa_calculada = str(registro.get('Caixa', '0'))
                else:
                    caixa_calculada = "Sem padrão de caixa"

            # 💡 Atualiza o campo 'Caixa' na UI usando form_window.after()
            # É obrigatório atualizar a UI na thread principal do Tkinter
            def update_ui():
                entries["Caixa"].config(state="normal")
                entries["Caixa"].delete(0, tk.END)
                entries["Caixa"].insert(0, caixa_calculada)
                entries["Caixa"].config(state="readonly")
                
                # Após a Caixa ser atualizada, chama a distribuição novamente
                atualizar_distribuicao()


            form_window.after(0, update_ui)
            
        except requests.exceptions.RequestException as req_err:
            print(f"❌ Erro de conexão/API ao calcular caixa: {req_err}")
            form_window.after(0, lambda: messagebox.showerror("Erro API", "Falha ao calcular Caixa. Verifique o servidor."))
        except Exception as e:
            print(f"❌ Erro inesperado no cálculo da caixa: {e}")

    # <<< FUNÇÃO PARA ATUALIZAR O CAMPO METROS (usando a função externa robusta) >>>
    def atualizar_metros(event=None):
        """Função chamada no KeyRelease do Peso para atualizar Metros, Distribuição E Caixa."""
        
        # Verifica se os campos necessários estão presentes no dicionário entries
        if "Metros" not in entries or PESO_LABEL not in entries:
            return
            
        peso_str = entries[PESO_LABEL].get()
        
        # CHAVE: Usa o valor de Gramatura armazenado no estado mutável
        gramatura_entry_str = gramatura_state[0]

        # Chama a função robusta para calcular metros 
        metros_calculado = calcular_metros(peso_str, gramatura_entry_str) # Retorna PONTO

        # O campo 'Metros' precisa ser temporariamente habilitado para ter seu valor atualizado.
        entries["Metros"].config(state="normal")
        entries["Metros"].delete(0, tk.END)
        entries["Metros"].insert(0, metros_calculado)
        entries["Metros"].config(state="readonly")
        
        # 🟢 NOVO: Dispara a atualização da Caixa (requer servidor/Flask)
        nr_ordem = entries["Ordem"].get()
        
        # Se for uma ordem existente (tem número) e o peso não está vazio, chama a API
        if nr_ordem and order_number and peso_str.strip(): 
            # Executa a chamada de rede em uma thread separada para não travar a UI
            threading.Thread(target=calcular_e_atualizar_caixa, args=(peso_str, nr_ordem)).start()
        else:
            # Se for nova ordem ou sem número, zera o campo Caixa e atualiza Distribuição localmente
            entries["Caixa"].config(state="normal")
            entries["Caixa"].delete(0, tk.END)
            entries["Caixa"].insert(0, "0")
            entries["Caixa"].config(state="readonly")
            atualizar_distribuicao() # Chama distribuição localmente


    # ====================================================================
    # LÓGICA DE AUTOCOMPLETE (Artigo) - CORRIGIDA COM DEBOUNCE
    # ====================================================================
    
    def on_key_release_artigo(event):
        """Filtra as sugestões conforme a digitação no campo Artigo, com debounce e filtro inteligente."""
        nonlocal autocomplete_listbox, after_id_state

        if not is_new_order or autocomplete_listbox is None:
            return
            
        # Não faz nada se for setas ou teclas de controle (exceto Backspace)
        if event.keysym in ('Up', 'Down', 'Return', 'Left', 'Right', 'Tab', 'Shift_L', 'Shift_R'):
            return

        # 1. Cancela a chamada anterior
        if after_id_state[0]:
            form_window.after_cancel(after_id_state[0])

        # 2. Agenda a nova função de filtragem
        # Definir a função de fato que faz o filtro e a atualização da UI
        def run_filter():
            text = entries["Artigo"].get().strip().upper()
            
            autocomplete_listbox.delete(0, tk.END)
            
            if not text:
                autocomplete_listbox.pack_forget() 
                return
                
            sugestoes_filtradas = []
            # Itera sobre (Artigo_Base, Cor)
            for artigo_base, cor in autocomplete_data:
                artigo_base_upper = str(artigo_base).strip().upper()
                cor_upper = str(cor).strip().upper()
                texto_completo = f"{artigo_base_upper} {cor_upper}".strip()
                
                # 1. Filtro PRINCIPAL: Busca substring (qualquer posição)
                # Busca onde o texto digitado está contido em qualquer parte do artigo+cor
                match_found = False
                
                # Tenta encontrar correspondência flexible:
                # a) Match direto no texto completo (ex: "nillo 14" encontra "nillo 14 mm")
                if text in artigo_base_upper or text in cor_upper or text in texto_completo:
                    match_found = True
                # b) Match com palavras separadas (ex: "14" encontra "nillo 14 mm")
                else:
                    palavras_artigo = artigo_base_upper.split()
                    for palavra in palavras_artigo:
                        if text in palavra:  # "14" está em "14"
                            match_found = True
                            break
                
                if match_found:
                    # Adiciona o valor que será exibido na listbox: "ARTIGO BASE (COR)"
                    sugestao_display = f"{artigo_base.strip()} ({cor.strip()})" 
                    sugestoes_filtradas.append(sugestao_display)

            if sugestoes_filtradas:
                for item in sugestoes_filtradas[:1000]: # Limita a 1000 sugestões
                    autocomplete_listbox.insert(tk.END, item)
                
                autocomplete_listbox.pack(fill="x", expand=True)
                
            else:
                autocomplete_listbox.pack_forget()

        # Agenda a execução em 150ms
        after_id_state[0] = form_window.after(150, run_filter)


    def on_select_artigo(event):
        """Preenche Artigo e Cor ao selecionar uma sugestão E busca a Gramatura."""
        nonlocal autocomplete_listbox
        nonlocal gramatura_state # <--- Acessa o estado mutável da gramatura
        if autocomplete_listbox is None or not autocomplete_listbox.curselection():
            return
            
        # O valor selecionado é "ARTIGO BASE (COR)"
        selected_index = autocomplete_listbox.curselection()[0]
        selected_value = autocomplete_listbox.get(selected_index)
        
        # Extrai Artigo e Cor da string (ex: "NYLON 16 MM CRU (CRU)")
        match = re.search(r'(.+)\s+\((.+)\)', selected_value)
        if match:
            artigo_sugerido = match.group(1).strip()
            cor_sugerida = match.group(2).strip()
        else:
            # Se falhar, assume que é tudo Artigo e Cor é vazia
            artigo_sugerido = selected_value
            cor_sugerida = ""
            
        # 1. Preenche o campo Artigo
        artigo_entry = entries["Artigo"]
        artigo_entry.delete(0, tk.END)
        artigo_entry.insert(0, artigo_sugerido)
        
        # 2. Preenche o campo Cor
        cor_entry = entries["Cor"]
        # O estado precisa ser temporariamente mudado para 'normal' para inserção.
        cor_entry.config(state="normal") # <--- Habilita temporariamente
        cor_entry.delete(0, tk.END)
        cor_entry.insert(0, cor_sugerida)
        cor_entry.config(state="readonly") # <--- Bloqueia novamente
        
        # 3. BUSCA A GRAMATURA CORRESPONDENTE NA API (COM CACHE)
        if cor_sugerida:
            artigo_completo_para_api = f"{artigo_sugerido} {cor_sugerida}"
        else:
            artigo_completo_para_api = artigo_sugerido
        gramatura_api = fetch_gramatura_by_artigo(artigo_completo_para_api)
        
        # 4. ATUALIZA O ESTADO DA GRAMATURA (com ponto)
        gramatura_state[0] = gramatura_api
        
        # 5. ATUALIZA O CAMPO METROS (que agora chama atualizar_distribuicao)
        atualizar_metros() 
        
        # Esconde a listbox
        autocomplete_listbox.pack_forget()
        cor_entry.focus_set()

    # ====================================================================

    pedido_especial_valor = pedido_especial
    row_index = 0
    for label, value in tabela_infos:
        
        if label == "Pedido Especial":
            continue

        entry_value = ""

        if label == "Volume Prog":
																									 
            if is_new_order:
                    entry_value = "0.00"
            else:
                # 1. Garante que 'quantity' (o quantity_raw) seja uma string e substitui vírgula por ponto.
                raw_value_str = str(quantity).replace(',', '.') if quantity is not None else "0.00"
                
                # 2. Tenta formatar o valor bruto (ex: '120.5000') para o formato de exibição (ex: '120,50').
                try:
                    # Se a string for vazia após strip, forçar '0.00'
                    if not raw_value_str.strip():
                            raw_value_str = '0.00'
                            
                    # A função 'formatar_volume_para_exibicao' deve receber o valor com PONTO.
                    entry_value = formatar_volume_para_exibicao(raw_value_str)
                    
                except Exception:
                    # Em caso de qualquer falha na formatação, força o valor a ser '0,00' para a entry.
                    entry_value = "0,00"
                
        elif value == "Artigo":
            entry_value = artigo
        elif value == "Cor":
            entry_value = cor
        elif value == "Cliente":
            entry_value = client
        elif label == "Gramatura (g/m²)": 
            entry_value = gramatura_state[0].replace('.', ',')
        elif label == "Caixa": # <<< INICIALIZAÇÃO DA CAIXA
            entry_value = str(caixa or "")
        elif value == "mtf":
            entry_value = machine
        elif value == "turno":
            entry_value = get_turno()
        elif value == "data_tingimento":
            entry_value = data_formatada
        elif value == "Ordem":
            entry_value = order_number if order_number else ""
        elif label == "Metros":
            # Valor inicial é calculado com o peso (vazio) e a gramatura inicial
            entry_value = calcular_metros("", gramatura_state[0]) # <--- Usa o estado mutável
        
        #  Inicialização da Distribuição >>>
        elif label == "Distribuição": 
            # Metros inicial (com PONTO)
            metros_inicial = calcular_metros("", gramatura_state[0])
            # Caixa inicial (string, pode ser vazia ou None do banco)
            caixa_inicial = str(caixa or "0") 
            entry_value = calcular_distribuicao(metros_inicial, caixa_inicial) # Retorna VÍRGULA
            
        elif label == PESO_LABEL:
            #  Valor inicial do Peso
            entry_value = "0.000" if is_new_order else "" # AJUSTADO: Inicializa com PONTO
        elif label == "Observações":
            entry_value = order_details.get('Observacoes', '')
        elif label == "Quant. Cópias": #  Valor inicial para Cópias
            entry_value = "1"
        else:
            entry_value = ""

        # ====================================================================
        # CORREÇÃO PARA AUTOCOMPLETE: Usa Frame e Pack para o campo "Artigo"
        # ====================================================================
        if label == "Artigo":
            Label(form_window, text=label).grid(row=row_index, column=0, padx=10, pady=5, sticky="w")
            
            # 1. Cria um Frame que ocupará a célula (row_index, 1) do grid
            autocomplete_frame = tk.Frame(form_window)
            autocomplete_frame.grid(row=row_index, column=1, padx=10, pady=5, sticky="ew")
            
            # 2. Cria a Entry DENTRO do Frame
            entry = Entry(autocomplete_frame, width=30)
            entry.insert(0, entry_value)
            entry.pack(fill="x", expand=True) # Usa pack para gerenciar a Entry dentro do Frame
            entries[label] = entry
            
            # 3. Cria a Listbox DENTRO do Frame (IMPORTANTE: Garante o Frame como pai)
            autocomplete_listbox = tk.Listbox(autocomplete_frame, height=6, width=30)
            autocomplete_listbox.pack(fill="x", expand=True)
            autocomplete_listbox.pack_forget() # Esconde inicialmente

            # Re-bind o evento de seleção
            autocomplete_listbox.bind("<<ListboxSelect>>", on_select_artigo)
            
            # 4. Bindings de Autocomplete
            if is_new_order:
                # BIND ALTERADO PARA USAR O DEBOUNCE
                entry.bind("<KeyRelease>", on_key_release_artigo)
                
                # Bind para esconder a listbox ao perder o foco
                def hide_listbox(event):
                    # Se o foco for para a listbox (clique), não esconde
                    if form_window.focus_get() != autocomplete_listbox:
                        autocomplete_listbox.pack_forget()
                
                entry.bind("<FocusOut>", hide_listbox)
                autocomplete_listbox.bind("<FocusOut>", hide_listbox)

            # Define o estado de readonly (se não for nova ordem)
            if not is_new_order and label in readonly_if_existing:
                entry.config(state="readonly")
            
            row_index += 1
            continue # Pula o processamento geral abaixo e continua o loop

        # ====================================================================
        
        # Cria o tk.Entry para todos os outros campos
        Label(form_window, text=label).grid(row=row_index, column=0, padx=10, pady=5, sticky="w")
        entry = Entry(form_window, width=30)
        entry.insert(0, entry_value)
        entry.grid(row=row_index, column=1, padx=10, pady=5)
        entries[label] = entry

        # --- Lógica para definir campos readonly ---
        is_readonly = False
        
        # 1. Campos sempre readonly (turno, metros, cor, gramatura, caixa, distribuição)
        if label in readonly_always or label in readonly_fixed:
            is_readonly = True
        
        # 2. Campos readonly se a ordem existe
        elif not is_new_order and label in readonly_if_existing:
            is_readonly = True

        if is_readonly:
            entry.config(state="readonly")
        # ------------------------------------------

        # --- BINDINGS ESPECÍFICOS ---

        # Bindings existentes
        if label == PESO_LABEL:
            # 1. BINDING KeyRelease: Limpeza de entrada, formatação de display (com ponto) e Cálculo de Metros E Distribuição
            # ATUALIZAR_METROS JÁ CHAMA ATUALIZar_DISTRIBUICAO AGORA
            entry.bind("<KeyRelease>", lambda ev, en=entry: [formatar_decimal_input(ev, en), atualizar_metros(ev)])
            
            # 2. BINDING FocusOut: Formatação final para X.XXX
            entry.bind("<FocusOut>", lambda ev, en=entry: formatar_peso_output(ev, en))

        if label == "Data Tingimento" and not is_readonly:
            entry.bind("<KeyRelease>", mascara_data)

        if label == "Quant. Cópias" and not is_readonly:
            entry.bind("<KeyRelease>", lambda ev, en=entry: formatar_inteiro(ev, en))

        #  Bindings para "Tambores" (força inteiro, pois é editável) >>>
        if label == TAMBORES_LABEL and not is_readonly:
            entry.bind("<KeyRelease>", lambda event, e=entry: formatar_inteiro(event, e))

        # <<< NOVO BINDING: Caixa deve atualizar a Distribuição >>>
        if label == "Caixa" and not is_readonly: 
            # O campo Caixa deve ser formatado para inteiro e, em seguida, atualizar a Distribuição
            entry.bind("<KeyRelease>", lambda ev, en=entry: [formatar_inteiro(ev, en), atualizar_distribuicao(ev)])
            
        if label == "Operador" and not is_readonly:
            # Vincula a busca do nome do operador apenas se o campo for editável
            entry.bind("<FocusOut>", lambda event, entry=entry: update_operator_name(event, entry))
            
        # -----------------------------
        row_index += 1

    # Chamada inicial para preencher 'Metros' e 'Distribuição'
    atualizar_metros()

    def print_order():
        """
        Função principal que valida os campos, coleta os dados e inicia a impressão.
        Ajustada para SÓ permitir a impressão se os campos obrigatórios estiverem preenchidos/válidos.
        O campo 'Caixa' recebe "Sem padrão de caixa" se estiver vazio.
        """
        from tkinter import messagebox
        
        # 1. Coleta de todos os valores de entrada
        order_data = {}
        for label, widget in entries.items():
            if isinstance(widget, Text):
                value = widget.get("1.0", "end-1c").strip()
            else:
                value = widget.get().strip()
            order_data[label] = value

        # ====================================================================
        # 🟢 AJUSTE DE REQUISITO: Se a caixa for vazia, atribui o valor padrão
        # ====================================================================
        if not order_data.get("Caixa", "").strip():
            order_data["Caixa"] = "Sem padrão de caixa" 
            
        # ====================================================================
        # 🟢 INÍCIO: VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS
        # ====================================================================
        
        # 2. Definição dos campos obrigatórios (Caixa removida pois tem valor padrão)
        required_field_keys = [
            "Ordem", 
            "Artigo",
            "Cor",
            PESO_LABEL, 
            TAMBORES_LABEL, 
            "Operador", 
            "Data Tingimento", 
        ]
        
        missing_fields = []
        
        for key in required_field_keys:
            # Pega o valor, que já foi coletado e limpo (trim)
            value_str = order_data.get(key, "").strip()
            
            # Checagem 1: Valor vazio
            if not value_str:
                missing_fields.append(key)
                continue
                
            # Checagem 2: Operador Inválido
            if key == "Operador" and ("não encontrado" in value_str.lower() or "inválida" in value_str.lower()):
                missing_fields.append("Operador (Inválido)")
                continue
                
            # Checagem 3: Valores numéricos obrigatórios (> 0)
            # Note que 'Caixa' foi removida desta checagem
            if key in [PESO_LABEL, TAMBORES_LABEL, "Quant. Cópias"]:
                try:
                    # Normaliza para ponto para conversão (ex: 1,5 -> 1.5)
                    numeric_value = float(value_str.replace(",", "."))
                    
                    # Deve ser > 0
                    if numeric_value <= 0.0:
                        missing_fields.append(f"{key} (> 0)")
                except ValueError:
                    # Falha na conversão para número
                    missing_fields.append(f"{key} (Inválido/Não Numérico)")

													

        if missing_fields:
            messagebox.showerror(
                "Erro de Impressão", 
                "Não é possível imprimir. Os seguintes campos obrigatórios não estão preenchidos ou são inválidos:\n\n" + 
                "\n".join(f"- {campo}" for campo in sorted(set(missing_fields)))
            )
            return # Impressão interrompida
            
        # ====================================================================
        # 🟢 FIM: VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS
        # ====================================================================

        order_number = order_data.get("Ordem", None)
        pedido_especial = order_data.get("Pedido Especial", "") # Fallback
        
        printer_name = r'ELGIN i8'

        try:
            printer_handle = win32print.OpenPrinter(printer_name)
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)

            if pedido_especial and pedido_especial.upper() == 'SIM': 
                titulo = "Ficha de Artigo     *** Pedido Especial ***"
            else:
                titulo = "Ficha do Artigo"

            hdc.StartDoc(titulo)
            hdc.StartPage()

            # Configuração de Layout

            pos_inicial_x = 30
            pos_inicial_y = 50
            largura_celula_nome = 250
            largura_celula_valor = 290
            altura_celula = 50
            
            # Imprime o Título e ajusta a posição
            hdc.TextOut(pos_inicial_x, pos_inicial_y, titulo)
            pos_inicial_y += 50 

            for label, value in order_data.items():
                
                # Desenha a caixa do Nome (Label)
                hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula)
                hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
                hdc.LineTo(pos_inicial_x, pos_inicial_y)

                # Desenha a caixa do Valor
                hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y)
                hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y + altura_celula)
                hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula)

                # Imprime o Label
                hdc.TextOut(pos_inicial_x + 10, pos_inicial_y + 15, label)

                # TRATAMENTO PARA COR
                if label == "Cor":
                    # 1. Lógica especial para "enfestado" ou "enfraldado"
                    if any(x in value.lower() for x in ["enfestado", "enfraldado"]):
                        palavra_especial = None
                        for termo in ["enfestado", "enfraldado"]:
                            if termo in value.lower():
                                palavra_especial = termo
                                break

                        if palavra_especial:
                            index = value.lower().find(palavra_especial)
                            texto_antes = value[:index].rstrip()
                            texto_depois = value[index:].lstrip()

                            hdc.TextOut(pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, texto_antes)
                            pos_inicial_y += altura_celula

                            # Redesenha a linha divisória e célula para a segunda parte da palavra
                            hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula)
                            hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
                            hdc.LineTo(pos_inicial_x, pos_inicial_y)

                            hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y + altura_celula)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula)

                            hdc.TextOut(pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, texto_depois)
                            pos_inicial_y += altura_celula
                            continue 

                    # 2. Aplica a quebra de linha padrão para Cor
                    linhas_texto = split_text(value, largura_celula_valor - 20, hdc)
                    if linhas_texto:
                        hdc.TextOut(pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, linhas_texto[0])
                        pos_inicial_y += altura_celula

                        for linha in linhas_texto[1:]:
                            # Redesenha a linha divisória e célula para linhas adicionais
                            hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula)
                            hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
                            hdc.LineTo(pos_inicial_x, pos_inicial_y)

                            hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y + altura_celula)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula)

                            hdc.TextOut(pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, linha)
                            pos_inicial_y += altura_celula
                        
                    # Linha de separação
                    hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                    hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y)
                    pos_inicial_y += 5
                    
                    continue 

                elif label == "Cliente":
                    # Lógica de quebra de linha para Cliente
                    linhas_texto = split_text(value, largura_celula_valor - 20, hdc)
                    if linhas_texto:
                        hdc.TextOut(pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, linhas_texto[0])
                        pos_inicial_y += altura_celula

                        for linha in linhas_texto[1:]:
                            # Redesenha a linha divisória e célula para linhas adicionais
                            hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula)
                            hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
                            hdc.LineTo(pos_inicial_x, pos_inicial_y)

                            hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y + altura_celula)
                            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula)

                            hdc.TextOut(pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, linha)
                            pos_inicial_y += altura_celula

                    # Linha de separação
                    hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                    hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y)
                    pos_inicial_y += 5

                    continue 

                else:
                    # Impressão padrão para outros campos
                    hdc.TextOut(pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, value)
                    pos_inicial_y += altura_celula

            # --- Geração e Impressão do QR Code ---
            qr_data = {
                "Ordem":remover_acentos(order_data.get("Ordem")),
                "VolumeProg": remover_acentos(order_data.get("Quantity") or order_data.get("Volume Prog", "")),
                "Artigo":remover_acentos(order_data.get("Artigo")),
                "Cor":remover_acentos(order_data.get("Cor")),
                "Tambores":remover_acentos(order_data.get(TAMBORES_LABEL)),
                "Caixa": remover_acentos(order_data.get("Caixa")), # Usará "Sem padrão de caixa" se estava vazio
                "Peso": remover_acentos(order_data.get(PESO_LABEL)),
                "Metros":remover_acentos(order_data.get("Metros")), 
                "Distribuicao": remover_acentos(order_data.get("Distribuição")), 
                "DataTingimento": order_data.get("Data Tingimento", ""),
                "NumCorte": order_data.get("Nº Cortes", ""),
            }

            cor_original = order_data.get("Cor")
            cor_sem_acentos = remover_acentos(cor_original)
            qr_json = json.dumps(qr_data)

            print("Conteúdo do JSON para o QR Code:")
            print(qr_json)

            pasta_qr = "qrcodes"
            if not os.path.exists(pasta_qr):
                os.makedirs(pasta_qr)

            caminho_qr = os.path.join(pasta_qr, f"qrcode.png")
            caminho_json = os.path.join(pasta_qr, f"dados.json")

            with open(caminho_json, "w") as f_json:
                f_json.write(qr_json)

            qr_imagem = qrcode.make(qr_json)
            qr_imagem.save(caminho_qr)

            page_width = hdc.GetDeviceCaps(110)
            tamanho_qr = 400
            pos_qr_x = (page_width - tamanho_qr) // 2
            pos_qr_y = pos_inicial_y + 20

            imagem_qr = Image.open(caminho_qr)
            dib = ImageWin.Dib(imagem_qr)
            dib.draw(hdc.GetHandleOutput(), (pos_qr_x, pos_qr_y, pos_qr_x + tamanho_qr, pos_qr_y + tamanho_qr))

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()

            print("Impressão realizada com sucesso!")
            print("DADOS PARA IMPRESSÃO:")
            pprint(order_data)
            
        except Exception as e:
            messagebox.showerror("Erro de Impressão", f"Ocorreu um erro ao imprimir. Verifique a impressora '{printer_name}'. Detalhes: {e}")
            print(f"Erro ao imprimir: {e}")
            
        finally:
            if 'printer_handle' in locals():
                win32print.ClosePrinter(printer_handle)

    print_button = ctk.CTkButton(form_window, text="Imprimir", command=print_order)
    apply_button_style(print_button)
    print_button.bind("<Enter>", lambda event: on_enter(event, print_button))
    print_button.bind("<Leave>", lambda event: on_leave(event, print_button))
    print_button.grid(row=len(tabela_infos), columnspan=2, pady=20)

# FUNÇÃO PARA REPROCESSO (SIMILAR A open_order_details)
# ====================================================================
def open_reprocesso_details(artigo=None, cor=None, machine=None, client=None, order_date=None, quantity=None, gramatura=None, caixa=None, autocomplete_data=None, peso=None):
    """Abre a janela de reprocesso com autocomplete como Adicionar Ordem."""
    
    if autocomplete_data is None:
        autocomplete_data = []

    form_window = Toplevel()
    form_window.title("Adicionar Retingimento")

    window_width = 350
    window_height = 700

    form_window.resizable(False, False)
    center_window(form_window, window_width, window_height)

    # Estado da Gramatura
    initial_gramatura_value = gramatura.replace(',', '.') if gramatura else "0.00"
    gramatura_state = [initial_gramatura_value]
    
    # Estado para debounce do autocomplete
    after_id_state = [None]

    # Tabela de campos (SEM Ordem e Observações)
    tabela_infos = [
        ["Artigo", "Artigo"],
        ["Cor", "Cor"],
        ["Volume Prog", "Quantity"],
        ["Data Tingimento", "data_tingimento"],
        ["Elasticidade Acab", "elasticidade_acab"],
        ["Largura Acab", "largura_acab"],
        ["Cliente", "Cliente"],
        ["MTF", "mtf"],
        ["Nº Cortes", "num_cortes"],
        ["Operador", "operador"],
        ["Turno", "turno"],
        ["Tambores", "num_tambores"],
        ["Caixa", "Caixa"],
        ["Peso (KG)", "peso"],
        ["Metros", "metros"],
        # Campos específicos de Reprocesso
        ["Defeito", "defeito"],
        ["Data Retingimento", "data_reprocesso"],
        ["Vistoria", "vistoria"]
						
    ]

    entries = {}
    readonly_always = ["Volume Prog", "Turno", "Metros", "Cliente"]
    readonly_fixed = ["Cor", "Caixa"]
    autocomplete_listbox = None
    


    def atualizar_distribuicao(event=None):
        """Atualiza o campo Distribuição."""
        if "Metros" not in entries or "Distribuição" not in entries or "Caixa" not in entries:
            return
        metros_str = entries["Metros"].get()
        caixa_str = entries["Caixa"].get()
        distribuicao_calculada = calcular_distribuicao(metros_str, caixa_str)
        entries["Distribuição"].config(state="normal")
        entries["Distribuição"].delete(0, tk.END)
        entries["Distribuição"].insert(0, distribuicao_calculada)
        entries["Distribuição"].config(state="readonly")

    def atualizar_metros(event=None):
        """Atualiza o campo Metros."""
        if "Metros" not in entries or PESO_LABEL not in entries:
            return
        peso_str = entries[PESO_LABEL].get()
        gramatura_entry_str = gramatura_state[0]
        metros_calculado = calcular_metros(peso_str, gramatura_entry_str)
        entries["Metros"].config(state="normal")
        entries["Metros"].delete(0, tk.END)
        entries["Metros"].insert(0, metros_calculado)
        entries["Metros"].config(state="readonly")
        atualizar_distribuicao()

    def on_key_release_artigo(event):
        """Filtro de autocomplete com debounce."""
        nonlocal autocomplete_listbox, after_id_state

        if autocomplete_listbox is None:
            return
        
        if event.keysym in ('Up', 'Down', 'Return', 'Left', 'Right', 'Tab', 'Shift_L', 'Shift_R'):
            return

        if after_id_state[0]:
            form_window.after_cancel(after_id_state[0])

        def run_filter():
            text = entries["Artigo"].get().strip().upper()
            autocomplete_listbox.delete(0, tk.END)
            
            if not text:
                autocomplete_listbox.pack_forget()
                return
            
            sugestoes_filtradas = []
            for artigo_base, cor in autocomplete_data:
                artigo_base_upper = str(artigo_base).strip().upper()
                cor_upper = str(cor).strip().upper()
                texto_completo = f"{artigo_base_upper} {cor_upper}".strip()
                
                match_found = False
                if text in artigo_base_upper or text in cor_upper or text in texto_completo:
                    match_found = True
                else:
                    palavras_artigo = artigo_base_upper.split()
                    for palavra in palavras_artigo:
                        if text in palavra:
                            match_found = True
                            break
                
                if match_found:
                    sugestao_display = f"{artigo_base.strip()} ({cor.strip()})"
                    sugestoes_filtradas.append(sugestao_display)

            if sugestoes_filtradas:
                for item in sugestoes_filtradas[:1000]:
                    autocomplete_listbox.insert(tk.END, item)
                autocomplete_listbox.pack(fill="x", expand=True)
            else:
                autocomplete_listbox.pack_forget()

        after_id_state[0] = form_window.after(150, run_filter)
																								 
																												 
																		  

    def on_select_artigo(event):
        """Seleciona artigo do autocomplete."""
        nonlocal autocomplete_listbox, gramatura_state
        
        if autocomplete_listbox is None or not autocomplete_listbox.curselection():
            return
        
        selected_index = autocomplete_listbox.curselection()[0]
        selected_value = autocomplete_listbox.get(selected_index)
        
        match = re.search(r'(.+)\s+\((.+)\)', selected_value)
        if match:
            artigo_sugerido = match.group(1).strip()
            cor_sugerida = match.group(2).strip()
        else:
            artigo_sugerido = selected_value
            cor_sugerida = ""
        
        artigo_entry = entries["Artigo"]
        artigo_entry.delete(0, tk.END)
        artigo_entry.insert(0, artigo_sugerido)
        
        cor_entry = entries["Cor"]
        cor_entry.config(state="normal")
        cor_entry.delete(0, tk.END)
        cor_entry.insert(0, cor_sugerida)
        cor_entry.config(state="readonly")
        
        if cor_sugerida:
            artigo_completo_para_api = f"{artigo_sugerido} {cor_sugerida}"
        else:
            artigo_completo_para_api = artigo_sugerido
        
        gramatura_api = fetch_gramatura_by_artigo(artigo_completo_para_api)
        gramatura_state[0] = gramatura_api
        atualizar_metros()
        
        autocomplete_listbox.pack_forget()
        cor_entry.focus_set()

    row_index = 0
    for label, value in tabela_infos:
        entry_value = ""

        if label == "Volume Prog":
            entry_value = "0.00"
        elif value == "Artigo":
            entry_value = artigo or ""
        elif value == "Cor":
            entry_value = cor or ""
        # --- ALTERAÇÃO AQUI ---
        elif value == "Cliente":
            entry_value = "RETINGIMENTO"
        elif label == "Caixa":
            entry_value = str(caixa or "")
        elif value == "mtf":
            entry_value = machine or ""
        elif value == "turno":
            entry_value = get_turno()
        elif value == "data_tingimento":
            entry_value = order_date if order_date else data_formatada
        elif label == "Metros":
            entry_value = calcular_metros("", gramatura_state[0])
        elif label == PESO_LABEL:
            entry_value = "0.000"
        else:
            entry_value = ""

        # CAMPO ARTIGO COM AUTOCOMPLETE
        if label == "Artigo":
            Label(form_window, text=label).grid(row=row_index, column=0, padx=10, pady=5, sticky="w")
            
            autocomplete_frame = tk.Frame(form_window)
            autocomplete_frame.grid(row=row_index, column=1, padx=10, pady=5, sticky="ew")
            
            entry = Entry(autocomplete_frame, width=30)
            entry.insert(0, entry_value)
            entry.pack(fill="x", expand=True)
            entries[label] = entry
            
            autocomplete_listbox = tk.Listbox(autocomplete_frame, height=6, width=30)
            autocomplete_listbox.pack(fill="x", expand=True)
            autocomplete_listbox.pack_forget()
            autocomplete_listbox.bind("<<ListboxSelect>>", on_select_artigo)
            
            entry.bind("<KeyRelease>", on_key_release_artigo)
            
            def hide_listbox(event):
                if form_window.focus_get() != autocomplete_listbox:
                    autocomplete_listbox.pack_forget()
            
            entry.bind("<FocusOut>", hide_listbox)
            autocomplete_listbox.bind("<FocusOut>", hide_listbox)
            
            row_index += 1
            continue

        # OUTROS CAMPOS
        Label(form_window, text=label).grid(row=row_index, column=0, padx=10, pady=5, sticky="w")
        entry = Entry(form_window, width=30)
        entry.insert(0, entry_value)
        entry.grid(row=row_index, column=1, padx=10, pady=5)
        entries[label] = entry

        is_readonly = False
        if label in readonly_always or label in readonly_fixed:
            is_readonly = True

        if is_readonly:
            entry.config(state="readonly")

        # BINDINGS
        if label == PESO_LABEL:
            entry.bind("<KeyRelease>", lambda ev, en=entry: [formatar_decimal_input(ev, en), atualizar_metros(ev)])
            entry.bind("<FocusOut>", lambda ev, en=entry: formatar_peso_output(ev, en))

        if label == "Data Tingimento" and not is_readonly:
            entry.bind("<KeyRelease>", mascara_data)

        if label == "Data Retingimento" and not is_readonly:
            entry.bind("<KeyRelease>", mascara_data)

        if label == TAMBORES_LABEL and not is_readonly:
            entry.bind("<KeyRelease>", lambda event, e=entry: formatar_inteiro(event, e))

        if label == "Caixa" and not is_readonly:
            entry.bind("<KeyRelease>", lambda ev, en=entry: [formatar_inteiro(ev, en), atualizar_distribuicao(ev)])

        if label == "Operador" and not is_readonly:
            entry.bind("<FocusOut>", lambda event, entry=entry: update_operator_name(event, entry))
        
        row_index += 1

    atualizar_metros()

    def print_reprocesso():
        order_data = {}
        for label, widget in entries.items():
            if isinstance(widget, Text):
                value = widget.get("1.0", "end-1c")
            else:
                value = widget.get()
            order_data[label] = value

        printer_name = r'ELGIN i8'

        try:
            printer_handle = win32print.OpenPrinter(printer_name)
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)

            titulo = "Retingimento - Ficha do Artigo"

            hdc.StartDoc(titulo)
            hdc.StartPage()

            hdc.TextOut(10, 10, titulo)

            pos_inicial_x = 30
            pos_inicial_y = 50
            largura_celula_nome = 250
            largura_celula_valor = 290
            altura_celula = 50

            for label, value in order_data.items():
                hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula)
                hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
                hdc.LineTo(pos_inicial_x, pos_inicial_y)

                hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y)
                hdc.LineTo(pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y + altura_celula)
                hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)

                hdc.TextOut(pos_inicial_x + 10, pos_inicial_y + 15, label)
                hdc.TextOut(pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, value)

                pos_inicial_y += altura_celula

            qr_data = {
                "VolumeProg": remover_acentos(order_data.get("Quantity") or order_data.get("Volume Prog", "")),
                "Artigo":remover_acentos(order_data.get("Artigo")),
                "Cor":remover_acentos(order_data.get("Cor")),
                "Tambores":remover_acentos(order_data.get(TAMBORES_LABEL)),
                "Caixa": remover_acentos(order_data.get("Caixa")), # Usará "Sem padrão de caixa" se estava vazio
                "Peso": remover_acentos(order_data.get(PESO_LABEL)),
                "Metros":remover_acentos(order_data.get("Metros")), 
                "Distribuicao": remover_acentos(order_data.get("Distribuição")), 
                "DataTingimento": order_data.get("Data Tingimento", ""),
                "NumCorte": order_data.get("Nº Cortes", ""),
            }

            qr_json = json.dumps(qr_data)

            print("Conteúdo do JSON para o QR Code (Reprocesso):")
            print(qr_json)

            pasta_qr = "qrcodes"
            if not os.path.exists(pasta_qr):
                os.makedirs(pasta_qr)

            caminho_qr = os.path.join(pasta_qr, f"qrcode_reprocesso.png")
            caminho_json = os.path.join(pasta_qr, f"dados_reprocesso.json")

            with open(caminho_json, "w") as f_json:
                f_json.write(qr_json)

            qr_imagem = qrcode.make(qr_json)
            qr_imagem.save(caminho_qr)

            page_width = hdc.GetDeviceCaps(110)
            tamanho_qr = 200
            pos_qr_x = (page_width - tamanho_qr) // 2
            pos_qr_y = pos_inicial_y + 20

            imagem_qr = Image.open(caminho_qr)
            dib = ImageWin.Dib(imagem_qr)
            dib.draw(hdc.GetHandleOutput(), (pos_qr_x, pos_qr_y, pos_qr_x + tamanho_qr, pos_qr_y + tamanho_qr))

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()

            print("Impressão de reprocesso realizada com sucesso!")
            print("DADOS PARA IMPRESSÃO:")
            pprint(order_data)
        except Exception as e:
            print(f"Erro ao imprimir reprocesso: {e}")
        finally:
            if 'printer_handle' in locals():
                win32print.ClosePrinter(printer_handle)

    print_button = ctk.CTkButton(form_window, text="Imprimir", command=print_reprocesso)
    apply_button_style(print_button)
    print_button.bind("<Enter>", lambda event: on_enter(event, print_button))
    print_button.bind("<Leave>", lambda event: on_leave(event, print_button))
    print_button.grid(row=row_index, columnspan=2, pady=20)
# Interface principal
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Programação Ordem de Produção")
        # icon_path = os.path.abspath("C:/FichaArtigo/icon_form.ico")
        # self.iconbitmap(icon_path)
        
        #  Dados de Autocomplete >>>
        self.autocomplete_data = []
        self.load_autocomplete_data()

        # Tamanho da Tela
        window_width = 1200
        window_height = 600

        # Centraliza a janela
        center_window(self, window_width, window_height)

        # Cria estilo personalizado para as abas
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "TNotebook.Tab",
            background="white",  # Cor de fundo das abas
            foreground="black",  # Cor do texto
            font=("Arial", 16, "bold"),
            padding=[10, 5],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#A31D1D")],  # Cor da aba selecionada
            foreground=[("selected", "white")],  # Cor do texto na aba selecionada
        )

        # Cria o Notebook para as abas
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Aba Tingimento
        self.tingimento_frame = ctk.CTkFrame(self.notebook, fg_color="#9AA6B2")
        self.notebook.add(self.tingimento_frame, text="Tingimento")
        self.create_tingimento_tab()

        # Aba Retingimento
        self.retingimento_frame = ctk.CTkFrame(self.notebook, fg_color="#9AA6B2")
        self.notebook.add(self.retingimento_frame, text="Retingimento")
        self.create_retingimento_tab()

        version_label = ctk.CTkLabel(self, text=f"Versão {APP_VERSION}", font=("Arial", 12), fg_color="#9AA6B2")
        version_label.pack(side="bottom", pady=5)

    def load_autocomplete_data(self):
        """Busca TODOS os artigos do banco de dados para popular o autocomplete."""
        print("DEBUG: Iniciando busca de TODOS os artigos para autocomplete...")
        
        try:
            # 1. Chamar o novo endpoint que retorna TODOS os artigos
            base_url = "http://168.190.90.2:5000/consulta/allArtigos"
            response = requests.get(base_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list) and data:
                    artigos = []
                    # 2. Processar os dados retornados
                    for item in data:
                        artigo_nome = str(item.get("Artigo", "")).strip()
                        
                        if artigo_nome and artigo_nome.upper() != 'NAN':
                            # O endpoint retorna apenas o nome do artigo, sem cor separada
                            # Mas o nome já contém tudo (ex: "NILLO 14 MM PRETO")
                            # Vamos dividir em Artigo base e Cor
                            artigo_base, cor = dividir_artigo_cor(artigo_nome)
                            artigos.append((artigo_base, cor))
                    
                    # 3. Remoção de duplicatas e ordenação
                    self.autocomplete_data = sorted(list(set(artigos)))
                    print(f"✅ {len(self.autocomplete_data)} artigos carregados do banco para o autocomplete.")
                    
                    # Debug: Mostra alguns dos artigos carregados
                    if self.autocomplete_data:
                        print("📋 Amostra dos primeiros 10 artigos carregados:")
                        for i, (art, cor) in enumerate(self.autocomplete_data[:10], 1):
                            print(f"   {i}. {art} ({cor})")
                    return
                else:
                    print("⚠️ API retornou dados vazios ou inválidos.")
            else:
                print(f"❌ Erro HTTP {response.status_code} ao buscar todos os artigos.")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão com a API de artigos: {e}")
        except Exception as e:
            print(f"❌ Erro inesperado ao buscar artigos: {e}")
        
        # FALLBACK: Se o endpoint /allArtigos falhar, tenta o método antigo (ordens ativas)
        print("⚠️ Usando fallback: carregando artigos das ordens ativas...")
        df = fetch_data_from_db(search_term=None)
        
        if df is None or df.empty:
            print("❌ Não foi possível carregar artigos (API e Cache vazios).")
            self.autocomplete_data = []
            return
            
																					  
        if 'Artigo' not in df.columns or 'Cor' not in df.columns:
            print("❌ Colunas 'Artigo' ou 'Cor' não encontradas no DataFrame.")
            self.autocomplete_data = []
            return

        artigos = []
						  
        for _, row in df.iterrows():
											
            artigo_base = str(row['Artigo']).strip()
            cor = str(row['Cor']).strip()
            
            if artigo_base and artigo_base != 'NAN':
                 artigos.append((artigo_base, cor))

												  
        self.autocomplete_data = sorted(list(set(artigos)))
        print(f"✅ {len(self.autocomplete_data)} artigos carregados do fallback (ordens ativas).")

    def manual_update_check(self):
        """Função chamada pelo botão para testar a conexão com a API"""
        try:
            # Importante: certifique-se que o requests foi importado no topo do arquivo
            response = requests.get(UPDATE_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                remote_version = data.get("version_name")
                
                print(f"Versão Local: {APP_VERSION}")
                print(f"Versão Remota: {remote_version}")

                # Lógica de comparação
                if remote_version > APP_VERSION:
                    if messagebox.askyesno("Atualização Disponível", 
                                          f"Nova versão {remote_version} encontrada!\nDeseja atualizar agora?"):
                        # Chama a função global perform_update que definimos antes
                        perform_update(data.get("download_url")) 
                else:
                    messagebox.showinfo("Atualização", f"Você já está na versão mais recente ({APP_VERSION}).")
            else:
                messagebox.showerror("Erro", f"A API respondeu com erro: {response.status_code}")
                
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

            
    def create_tingimento_tab(self):

        # Frame para agrupar entrada de texto e botões
        search_frame = ctk.CTkFrame(self.tingimento_frame, fg_color="#9AA6B2")
        search_frame.pack(fill="x", padx=10, pady=5)

        # Campo de entrada para pesquisa
        self.search_entry = ctk.CTkEntry(search_frame, width=300)
        self.search_entry.pack(side="left", padx=(0, 10), pady=5)

        # Botão de pesquisa
        self.search_button = ctk.CTkButton(
            search_frame,
            text="Pesquisar",
            command=self.search_data,
            fg_color="#A31D1D",
            text_color="white",
            font=("Arial", 16, "bold"),
            width=150,
        )

        apply_button_style(self.search_button)

        self.search_button.bind("<Enter>", lambda event: on_enter(event, self.search_button))
        self.search_button.bind("<Leave>", lambda event: on_leave(event, self.search_button))

        self.search_button.pack(side="left", padx=(0, 10), pady=5)

        # Botão Atualizar
        self.refresh_button = ctk.CTkButton(
            search_frame,
            text="Atualizar",
            command=self.refresh_data,
            fg_color="#A31D1D",
            text_color="white",
            font=("Arial", 16, "bold"),
            width=150,
        )

        self.btn_update = ctk.CTkButton(
            search_frame, 
            text="Verificar Atualização", 
            command=self.manual_update_check, # Chama o método da classe
            fg_color="gray",
            text_color="white",
            font=("Arial", 16, "bold"),
            width=150
        )
        
        # 2. Aplica o estilo (se quiser o efeito hover igual aos outros)
        apply_button_style(self.btn_update)
        
        # 3. EMPACOTAMENTO (Onde o botão realmente aparece na tela)
        self.btn_update.pack(side="left", padx=(10, 0), pady=5)


        apply_button_style(self.refresh_button)

        # Adicionando eventos de hover
        self.refresh_button.bind("<Enter>", lambda event: on_enter(event, self.refresh_button))
        self.refresh_button.bind("<Leave>", lambda event: on_leave(event, self.refresh_button))

        self.refresh_button.pack(side="left", pady=5)
        
        #  Botão Adicionar Ordem ---
        self.add_order_button = ctk.CTkButton(
            search_frame,
            text="Adicionar Ordem",
            command=self.add_new_order,  # Chamará a nova função
            fg_color="#A31D1D",
            text_color="white",
            font=("Arial", 16, "bold"),
            width=150,
        )
        apply_button_style(self.add_order_button)
        self.add_order_button.bind("<Enter>", lambda event: on_enter(event, self.add_order_button))
        self.add_order_button.bind("<Leave>", lambda event: on_leave(event, self.add_order_button))
        self.add_order_button.pack(side="left", padx=(10, 0), pady=5)
        # -----------------------------------

        # Frame e Treeview
        self.frame = ctk.CTkFrame(self.tingimento_frame, fg_color="#9AA6B2")
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Estilo personalizado para o cabeçalho da Treeview
        style = ttk.Style()
        style.configure("Treeview.Heading",
                        background="#A31D1D",
                        foreground="white",
                        font=("Arial", 16, "bold"))

        style.map("Treeview.Heading",
                  background=[("active", "#D3D3D3")],
                  foreground=[("active", "black")])

        # Estilo das células
        style.configure("Treeview",
                        font=("Arial", 14))

        # Criando a Treeview
        self.tree = ttk.Treeview(self.frame, columns=("Ordem", "Quantity_Display", "Artigo", "Cor", "DtOrdem", "Cliente", "Maquina", "PedidoEspecial", "Gramatura", "Caixa", "Quantity"), show="headings") # <<< ALTERADO

        # DEFINIÇÃO DOS CABEÇALHOS NA ORDEM CORRETA
        self.tree.heading("Ordem", text="Ordem")
        self.tree.heading("Quantity_Display", text="Volume Prog") # 
        self.tree.heading("Artigo", text="Artigo")
        self.tree.heading("Cor", text="Cor")
        # self.tree.heading("Quantity", text="Volume Prog") # REMOVIDO
        self.tree.heading("DtOrdem", text="Data Ordem")
        self.tree.heading("Cliente", text="Cliente")
        self.tree.heading("Maquina", text="Máquina")
        
        # Colunas Ocultas (usadas apenas para passar dados para a próxima tela)
        self.tree.column("PedidoEspecial", width=0, stretch=tk.NO) 
        self.tree.column("Gramatura", width=0, stretch=tk.NO) 
        self.tree.column("Caixa", width=0, stretch=tk.NO) #  Oculta a Caixa (índice 9)
        self.tree.column("Quantity_Display", width=120, stretch=tk.NO) # Exibe Quantity_Display
        self.tree.column("Quantity", width=0, stretch=tk.NO) # Oculta o valor bruto (índice 10)

        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Evento de duplo clique
        self.tree.bind("<Double-1>", self.on_treeview_item_double_click)

        # Carregar dados
        self.refresh_data()

    def create_retingimento_tab(self):
        # Frame para agrupar botões
        btn_frame = ctk.CTkFrame(self.retingimento_frame, fg_color="#9AA6B2")
        btn_frame.pack(fill="x", padx=10, pady=5)

        # Botão para adicionar novo reprocesso
        self.add_reprocesso_button = ctk.CTkButton(
            btn_frame,
            text="Adicionar Retingimento",
            command=self.add_new_reprocesso,
            fg_color="#A31D1D",
            text_color="white",
            font=("Arial", 16, "bold"),
            width=150,
        )
        apply_button_style(self.add_reprocesso_button)
											 
        self.add_reprocesso_button.bind("<Enter>", lambda event: on_enter(event, self.add_reprocesso_button))
        self.add_reprocesso_button.bind("<Leave>", lambda event: on_leave(event, self.add_reprocesso_button))
        self.add_reprocesso_button.pack(side="left", padx=5, pady=5)

    def add_new_reprocesso(self):
        """Abre a tela de reprocesso com autocomplete como Adicionar Ordem."""
        open_reprocesso_details(
            artigo="",
            cor="",
            machine="",
            client="",
            order_date="",
            quantity="0.0000",
            gramatura="0.00",
            caixa="",
            peso="0.00",
            autocomplete_data=self.autocomplete_data
        )

    def refresh_data(self):
        # O refresh_data ainda chama fetch_data_from_db para garantir o dado mais atual
        df = fetch_data_from_db()
        populate_treeview(self.tree, df)
        # NOVO: Atualiza os dados do autocomplete ao atualizar a tela principal
        self.load_autocomplete_data() 

    def search_data(self):
        # 1. Obter o termo de pesquisa
        search_term = self.search_entry.get().strip()
        
        # 2. Obter TODOS os dados do servidor (via API ou Cache)
        # O argumento é None, forçando a função a retornar todos os dados.
        df_all = fetch_data_from_db(search_term=None) 
        
        if df_all is None:
            messagebox.showerror("Erro de Busca", "Ocorreu um erro ao buscar dados (API ou Cache vazio).")
            return

        # 3. Aplicar o filtro no lado do CLIENTE (Pandas)
        df_filtered = df_all
        
        if search_term:
            # Converte a coluna de busca e o termo para string para garantir a comparação
            search_value = str(search_term)
            
            # Tenta converter a coluna 'Ordem' do DF para string antes de filtrar:
            if 'Ordem' in df_filtered.columns:
                df_filtered['Ordem'] = df_filtered['Ordem'].astype(str)
                df_filtered = df_filtered[
                    df_filtered['Ordem'].str.contains(search_value, case=False, na=False)
                ]
            else:
                # Caso a coluna 'Ordem' não exista (erro de API)
                messagebox.showerror("Erro de Tabela", "Coluna 'Ordem' não encontrada no DataFrame.")
                return


        # 4. Popula a tabela com o resultado FILTRADO
        populate_treeview(self.tree, df_filtered)
        
    # --- NOVO: Função para abrir o formulário de Adicionar Ordem ---
    def add_new_order(self):
        open_order_details(
            order_number="",
            artigo="",
            cor="",
            machine="",
            client="",
            order_date=data_formatada,
            quantity="0.0000",
            gramatura="0.00",
            caixa="",
            peso="0.00", 
            autocomplete_data=self.autocomplete_data
        )

    def on_treeview_item_double_click(self, event):
        item = self.tree.selection()[0]
        values = self.tree.item(item, "values")

        # 🟢 CORREÇÃO: Espera 13 colunas (Ordem, Qtd_Display, Artigo, Cor, DtOrdem, Cliente, Maquina, PedidoEspecial, Gramatura, Caixa, Peso, Qtd_Raw, MetrosEstimados)
        if len(values) < 13: 
            print(f"❌ Número incorreto de colunas ({len(values)}) no item da TreeView. Esperado 13 (incluindo Metros).")
            return
        
        order_number, quantity_display, artigo, cor, order_date, client, machine, pedido_especial, gramatura, caixa, peso_da_consulta, quantity_raw, metros_estimados = values

        try:
            metros_estimados_int = int(float(metros_estimados)) 
            metros_estimados_formatado = f"{metros_estimados_int:,}".replace(",", ".")
        except (ValueError, TypeError):
            # Mantém o valor original se a conversão falhar
            metros_estimados_formatado = metros_estimados

        open_order_details(
            order_number=order_number,
            artigo=artigo,
            cor=cor,
            machine=machine,
            client=client,
            order_date=order_date, # Usando a data extraída
            quantity=quantity_display, # Passa o valor bruto (com ponto)
            pedido_especial=pedido_especial,
            gramatura=gramatura, # Passar gramatura para o formulário
            caixa=caixa, #  Passar o valor da Caixa
            peso=peso_da_consulta, # Passa o peso extraído
            metros=metros_estimados, # Passando Metros Estimados
            autocomplete_data=self.autocomplete_data # Passa os dados de Artigo/Cor
        )

if __name__ == "__main__":
    entry_quant_kg = None
    entry_defeito = None
    entry_data = None
    entry_vistoria = None
    entry_ordem = None
    
    init_db()
    
    # 1. Thread de atualização contínua de ORDEM
    threading.Thread(target=run_periodic_ordens_update, daemon=True).start()
    
    # 2. Thread de atualização contínua de OPERADORES
    threading.Thread(target=run_periodic_operadores_update, daemon=True).start()
    
    # Chama a função principal do CustomTkinter
    app = App()
    app.mainloop()