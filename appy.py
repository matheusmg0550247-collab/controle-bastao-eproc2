# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
# REMOVIDOS: import time, import json, import os
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh

# ... (demais constantes)
# REMOVIDAS: LOG_FILE, STATE_FILE, pois usaremos o cache de recurso.

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

# @st.cache_resource: Cria um objeto Python mutável (dicionário) que
# é instanciado apenas uma vez e COMPARTILHADO entre TODAS as sessões/usuários.
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    """Inicializa e retorna o dicionário de estado GLOBAL compartilhado."""
    print("--- Inicializando o Cache de Estado GLOBAL (Executa Apenas 1x) ---")
    return {
        # O estado inicial DEVE ser definido aqui.
        'status_texto': {nome: '' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'rotation_gif_start_time': None,
        # Adiciona uma chave de controle de inicialização
        '_initialized': True
    }

# Ponto 1: `load_state` agora carrega do objeto GLOBAL (Cache)
def load_state():
    """Carrega o estado GLOBAL (Cache) e copia para a sessão LOCAL."""
    global_data = get_global_state_cache()
    
    # É importante fazer uma cópia superficial ou profunda, dependendo do que
    # se quer armazenar na sessão. Aqui fazemos um cast para garantir tipos.
    
    loaded_data = {
        k: v for k, v in global_data.items()
    }
    
    # Converte strings de datetime armazenadas em datetime objects (se necessário)
    # OBS: Se o objeto em cache armazena datetime diretamente, esta conversão não é necessária
    # O Streamlit cache_resource pode lidar com datetime.
    
    # No entanto, a forma mais segura é armazenar os datetimes DENTRO DO CACHE,
    # o que faremos no save_state(). Não precisamos de conversão de string aqui.
    
    return loaded_data


# Ponto 2: `save_state` agora salva no objeto GLOBAL (Cache)
def save_state():
    """Salva o estado da sessão LOCAL (st.session_state) no estado GLOBAL (Cache)."""
    global_data = get_global_state_cache()
    
    try:
        # Transferir apenas as chaves de estado de volta para o objeto global
        # É crucial transferir o objeto datetime diretamente
        global_data['status_texto'] = st.session_state.status_texto
        global_data['bastao_queue'] = st.session_state.bastao_queue
        global_data['skip_flags'] = st.session_state.skip_flags
        global_data['bastao_start_time'] = st.session_state.bastao_start_time
        
        # current_status_starts é um dicionário com valores datetime
        global_data['current_status_starts'] = st.session_state.current_status_starts
        
        global_data['report_last_run_date'] = st.session_state.report_last_run_date
        global_data['bastao_counts'] = st.session_state.bastao_counts
        global_data['priority_return_queue'] = st.session_state.priority_return_queue
        global_data['rotation_gif_start_time'] = st.session_state.get('rotation_gif_start_time')

        print(f'*** Estado GLOBAL Salvo (Cache de Recurso) ***')
    except Exception as e: 
        print(f'Erro ao salvar estado GLOBAL: {e}')
        st.error(f"Erro ao salvar estado global: {e}")
        

def init_session_state():
    """Sincroniza o estado GLOBAL com a sessão LOCAL (st.session_state)."""
    # Carrega o estado global compartilhado (carrega o dicionário inteiro)
    persisted_state = load_state()
    
    defaults = {
        'status_texto': {nome: '' for nome in CONSULTORES}, 'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None, 'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min, 'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [], 'rotation_gif_start_time': None,
        # Variáveis exclusivas da sessão local (se houver)
        'gif_warning': False, 'play_sound': False
    }

    # Sincroniza o GLOBAL (persisted_state) para a sessão LOCAL (st.session_state)
    for key, default in defaults.items():
        # Usa o valor persistido, exceto se a chave for exclusiva da sessão local
        if key not in ['gif_warning', 'play_sound']:
            value = persisted_state.get(key, default)
            # Para o current_status_starts, garante que o datetime seja mantido
            if key == 'current_status_starts' and isinstance(value, dict):
                # Garante que todos os consultores estão presentes
                temp_starts = {nome: value.get(nome, datetime.now()) for nome in CONSULTORES}
                st.session_state[key] = temp_starts
            else:
                st.session_state.setdefault(key, value)
        else:
             st.session_state.setdefault(key, default) # Mantém default para variáveis locais
             
    # Garante que todos os consultores existam nos dicionários internos
    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, persisted_state.get('bastao_counts', {}).get(nome, 0))
        st.session_state.skip_flags.setdefault(nome, persisted_state.get('skip_flags', {}).get(nome, False))
        st.session_state.status_texto.setdefault(nome, persisted_state.get('status_texto', {}).get(nome, ''))
        
        # Configura o checkbox (variável local)
        is_active = nome in st.session_state.bastao_queue or bool(st.session_state.status_texto.get(nome))
        st.session_state.setdefault(f'check_{nome}', is_active)

    # Lógica de reconstrução de fila ao carregar (Mantida)
    checked_on = {c for c in CONSULTORES if st.session_state.get(f'check_{c}')}
    if not st.session_state.bastao_queue and checked_on:
        print('!!! Fila vazia na carga, reconstruindo !!!')
        st.session_state.bastao_queue = sorted(list(checked_on)) # Reconstroi
        
    print('--- Estado Sincronizado (GLOBAL -> LOCAL) ---')
    # Não salva aqui, pois o salvamento só deve ocorrer após uma ação do usuário.

# ... (Resto do código é o mesmo, exceto pelo ajuste no st_autorefresh e a remoção de imports e variáveis obsoletas)
