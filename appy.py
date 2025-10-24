# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh

# --- Constantes de Consultores ---
CONSULTORES = sorted([
    "Alex Paulo da Silva",
    "Dirceu Gonçalves Siqueira Neto",
    "Douglas de Souza Gonçalves",
    "Farley Leandro de Oliveira Juliano", 
    "Gleis da Silva Rodrigues",
    "Hugo Leonardo Murta",
    "Igor Dayrell Gonçalves Correa",
    "Jerry Marcos dos Santos Neto",
    "Jonatas Gomes Saraiva",
    "Leandro Victor Catharino",
    "Luiz Henrique Barros Oliveira",
    "Marcelo dos Santos Dutra",
    "Marina Silva Marques",
    "Marina Torres do Amaral",
    "Vanessa Ligiane Pimenta Santos"

])

# --- FUNÇÃO DE CACHE GLOBAL ---
# @st.cache_resource: Cria um objeto Python mutável (dicionário) que
# é instanciado apenas uma vez e COMPARTILHADO entre TODAS as sessões/usuários.
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    """Inicializa e retorna o dicionário de estado GLOBAL compartilhado."""
    print("--- Inicializando o Cache de Estado GLOBAL (Executa Apenas 1x) ---")
    return {
        # Status inicial agora é 'Indisponível'
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES}, 
        'report_last_run_date': datetime.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'rotation_gif_start_time': None,
        'skip_block': {}, # Variável para controle de bloqueio na primeira tentativa (GLOBAL)
    }

# --- Constantes ---
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = ""
BASTAO_EMOJI = "🌸"
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
STATUS_SAIDA_PRIORIDADE = ['Saída Temporária']
STATUSES_DE_SAIDA = ['Atividade', 'Almoço', 'Saída Temporária', 'Ausente', 'Sessão'] 
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX3ie9nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_LUNCH_ALERT = 'https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExMjBjN2l5eG52ejN6cW1sYjZobXRsdDd0NjZ6aXV0aGg5aXA5N2EyZCZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/wmGUXuhdoL9TFhDDet/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/refs/heads/main/doorbell-223669.mp3"

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

def date_serializer(obj):
    if isinstance(obj, datetime): return obj.isoformat()
    return str(obj)

# --- FUNÇÃO `save_state` (GLOBAL) ---
def save_state():
    """Salva o estado da sessão LOCAL (st.session_state) no estado GLOBAL (Cache)."""
    global_data = get_global_state_cache()
    
    try:
        global_data['status_texto'] = st.session_state.status_texto.copy()
        global_data['bastao_queue'] = st.session_state.bastao_queue.copy()
        global_data['skip_flags'] = st.session_state.skip_flags.copy()
        global_data['current_status_starts'] = st.session_state.current_status_starts.copy()
        global_data['bastao_counts'] = st.session_state.bastao_counts.copy()
        global_data['priority_return_queue'] = st.session_state.priority_return_queue.copy()

        global_data['bastao_start_time'] = st.session_state.bastao_start_time
        global_data['report_last_run_date'] = st.session_state.report_last_run_date
        global_data['rotation_gif_start_time'] = st.session_state.get('rotation_gif_start_time')
        global_data['skip_block'] = st.session_state.skip_block.copy() 

        print(f'*** Estado GLOBAL Salvo (Cache de Recurso) ***')
    except Exception as e: 
        print(f'Erro ao salvar estado GLOBAL: {e}')

# --- FUNÇÃO `load_state` (GLOBAL) ---
def load_state():
    """Carrega o estado GLOBAL (Cache) e retorna para a sessão LOCAL."""
    global_data = get_global_state_cache()
    loaded_data = {k: v for k, v in global_data.items()}
    return loaded_data
# --- FIM DAS MUDANÇAS DE PERSISTÊNCIA ---

def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        message_template = "🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo Responsável:** {consultor}\n- **Acesse o Painel:** {app_url}"
        message_text = message_template.format(consultor=consultor, app_url=APP_URL_CLOUD) 
        chat_message = {"text": message_text}
        try:
            response = requests.post(CHAT_WEBHOOK_BASTAO, json=chat_message)
            response.raise_for_status()
            print(f"Notificação de bastão enviada para {consultor}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar notificação de bastão: {e}")
            return False
    return False

def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'
def load_logs(): return [] # Implementação omitida
def save_logs(l): pass # Implementação omitida

def log_status_change(consultor, old_status, new_status, duration):
    print(f'LOG: {consultor} de "{old_status or "-"}" para "{new_status or "-"}" após {duration}')
    if not isinstance(duration, timedelta): duration = timedelta(0)
    st.session_state.current_status_starts[consultor] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def send_daily_report(): 
    print("Tentando enviar backup diário...")
    logs = load_logs() 
    today_str = datetime.now().date().isoformat()
    report_data = [{'consultor': 'Exemplo', 'old_status': 'Bastão', 'duration_s': 3600}] 

    if not report_data or not GOOGLE_CHAT_WEBHOOK_BACKUP:
        print(f"Backup não enviado. Dados: {bool(report_data)}, Webhook: {bool(GOOGLE_CHAT_WEBHOOK_BACKUP)}")
        st.session_state['report_last_run_date'] = datetime.now()
        save_state()
        return

    report_text = f"📊 **Backup Diário de Status - {today_str}**\n\n(Detalhes do processamento de logs omitidos)"
    chat_message = {'text': report_text}
    print(f"Enviando backup para: {GOOGLE_CHAT_WEBHOOK_BACKUP}")
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_BACKUP, json=chat_message)
        response.raise_for_status()
        st.session_state['report_last_run_date'] = datetime.now()
        print("Backup diário enviado com sucesso.")
        save_state()
    except requests.exceptions.RequestException as e:
        print(f'Erro ao enviar backup diário: {e}')
        if e.response is not None:
            print(f'Status: {e.response.status_code}, Resposta: {e.response.text}')

# --- LÓGICA DE BASTÃO E FILA ---

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    num_consultores = len(queue)
    if num_consultores == 0: return -1
    if current_index >= num_consultores or current_index < -1: current_index = -1

    next_idx = (current_index + 1) % num_consultores
    attempts = 0
    while attempts < num_consultores:
        consultor = queue[next_idx]
        if not skips.get(consultor, False) and st.session_state.get(f'check_{consultor}'):
            return next_idx
        next_idx = (next_idx + 1) % num_consultores
        attempts += 1
    print("AVISO: find_next_holder_index não encontrou ninguém elegível.")
    return -1

def check_and_assume_baton():
    print('--- VERIFICA E ASSUME BASTÃO ---')
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder_status = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    is_current_valid = (current_holder_status
                      and current_holder_status in queue
                      and st.session_state.get(f'check_{current_holder_status}'))

    first_eligible_index = find_next_holder_index(-1, queue, skips)
    first_eligible_holder = queue[first_eligible_index] if first_eligible_index != -1 else None

    print(f'Fila: {queue}, Skips: {skips}, Próximo Elegível: {first_eligible_holder}, Portador Atual (Status): {current_holder_status}, Atual é Válido?: {is_current_valid}')

    should_have_baton = None
    if is_current_valid:
        should_have_baton = current_holder_status
    elif first_eligible_holder:
        should_have_baton = first_eligible_holder

    changed = False
    for c in CONSULTORES:
        if c != should_have_baton and st.session_state.status_texto.get(c) == 'Bastão':
            print(f'Limpando bastão de {c} (não deveria ter)')
            duration = datetime.now() - st.session_state.current_status_starts.get(c, datetime.now())
            log_status_change(c, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[c] = 'Indisponível'
            changed = True

    if should_have_baton and st.session_state.status_texto.get(should_have_baton) != 'Bastão':
        print(f'Atribuindo bastão para {should_have_baton}')
        old_status = st.session_state.status_texto.get(should_have_baton, '')
        duration = datetime.now() - st.session_state.current_status_starts.get(should_have_baton, datetime.now())
        log_status_change(should_have_baton, old_status, 'Bastão', duration)
        st.session_state.status_texto[should_have_baton] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        if current_holder_status != should_have_baton: 
            st.session_state.play_sound += 1 # ATIVA O CONTADOR
            send_chat_notification_internal(should_have_baton, 'Bastão') # Notifica
        if st.session_state.skip_flags.get(should_have_baton):
            print(f' Consumindo skip flag de {should_have_baton} ao assumir.')
            st.session_state.skip_flags[should_have_baton] = False
        changed = True
    elif not should_have_baton:
        if current_holder_status:
            print(f'Ninguém elegível, limpando bastão de {current_holder_status}')
            duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
            log_status_change(current_holder_status, 'Bastão', 'Indisponível', duration) 
            st.session_state.status_texto[current_holder_status] = 'Indisponível' 
            changed = True
        if st.session_state.bastao_start_time is not None: changed = True
        st.session_state.bastao_start_time = None

    if changed: 
        print('Estado do bastão mudou. Salvando GLOBAL.')
        save_state()
    return changed

# --- FIM LÓGICA DE BASTÃO E FILA ---

# --- FUNÇÃO DE LÓGICA DE ALMOÇO ---
def check_lunch_capacity(consultor_tentativa):
    """
    Verifica se a marcação de 'Almoço' pelo consultor_tentativa excede 50%.
    
    Retorna True se DEVE BLOQUEAR, False caso contrário (pode prosseguir).
    """
    status_map = st.session_state.status_texto
    
    # Consultores que não devem contar na base (estão fora do jogo)
    excluded_statuses = ['Sessão', 'Ausente', 'Indisponível']
    
    # Total de consultores considerados ativos/elegíveis (não ignorados)
    total_ativos = sum(1 for c in CONSULTORES if status_map.get(c) not in excluded_statuses)
    
    # Número atual de consultores em Almoço
    num_em_almoco = sum(1 for c, s in status_map.items() if s == 'Almoço')
    
    # Se o consultor_tentativa NÃO está em Almoço e está tentando entrar:
    if status_map.get(consultor_tentativa) != 'Almoço':
        
        # A nova contagem de almoço será: atual + 1 (o consultor_tentativa)
        num_almoco_apos_tentativa = num_em_almoco + 1
        
        # Proteção contra total_ativos ser 0 (caso improvável, mas evita divisão por zero lógico)
        if total_ativos == 0:
            limite_excedido = False
        else:
            limite_excedido = num_almoco_apos_tentativa > (total_ativos / 2)
        
        if limite_excedido:
            # Regra: Se a capacidade exceder, verifique a segunda tentativa
            if st.session_state.skip_block.get(consultor_tentativa) == 'BLOCKED_LUNCH':
                # Já bloqueado uma vez, permite a passagem na segunda tentativa e limpa o bloqueio
                st.session_state.skip_block.pop(consultor_tentativa)
                print(f"ALMOÇO: {consultor_tentativa} permitido após segunda tentativa (limite excedido).")
                return False # Não bloqueia, permite
            else:
                # Bloqueia na primeira tentativa e marca para permitir na próxima
                st.session_state.skip_block[consultor_tentativa] = 'BLOCKED_LUNCH'
                print(f"ALMOÇO: Bloqueado pela primeira vez. Total em Almoço: {num_almoco_apos_tentativa} / {total_ativos}. Limite: {total_ativos/2}")
                return True # Bloqueia

    # Se a tentativa for para sair de Almoço, ou se o limite não foi excedido: permite
    if consultor_tentativa in st.session_state.skip_block:
         st.session_state.skip_block.pop(consultor_tentativa) # Limpa se o status atual não for Almoço
         
    return False # Permite prosseguir
# --- FIM FUNÇÃO DE LÓGICA DE ALMOÇO ---


def init_session_state():
    """Inicializa/sincroniza o st.session_state com o estado GLOBAL do cache."""
    persisted_state = load_state()
    
    defaults = {
        'bastao_start_time': None, 
        'report_last_run_date': datetime.min, 
        'rotation_gif_start_time': None,
        'play_sound': 0, # Usaremos um contador em vez de um booleano para forçar a re-renderização do som.
        'gif_warning': False,
        'lunch_alert_time': None, # Estado para controle de alerta de almoço (LOCAL DE SESSÃO)
    }

    # Sincroniza as variáveis simples
    for key, default in defaults.items():
        st.session_state.setdefault(key, persisted_state.get(key, default))

    # Sincroniza as coleções de estado (listas e dicionários)
    st.session_state['bastao_queue'] = persisted_state.get('bastao_queue', []).copy()
    st.session_state['priority_return_queue'] = persisted_state.get('priority_return_queue', []).copy()
    st.session_state['bastao_counts'] = persisted_state.get('bastao_counts', {}).copy()
    st.session_state['skip_flags'] = persisted_state.get('skip_flags', {}).copy()
    st.session_state['status_texto'] = persisted_state.get('status_texto', {}).copy()
    st.session_state['current_status_starts'] = persisted_state.get('current_status_starts', {}).copy()
    st.session_state['skip_block'] = persisted_state.get('skip_block', {}).copy() # Sincroniza a variável de bloqueio

    # Garante que todos os consultores estão nas listas de controle e sincroniza o checkbox
    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, 0)
        st.session_state.skip_flags.setdefault(nome, False)
        
        current_status = st.session_state.status_texto.get(nome, 'Indisponível') # Fallback
        st.session_state.status_texto.setdefault(nome, current_status)
        
        # Checkbox é TRUE se: status == 'Bastão' ou status == '' (Disponível na fila)
        is_available = (current_status == 'Bastão' or current_status == '') and nome not in st.session_state.priority_return_queue
        
        st.session_state[f'check_{nome}'] = is_available
        
        if nome not in st.session_state.current_status_starts:
               st.session_state.current_status_starts[nome] = datetime.now()


    checked_on = {c for c in CONSULTORES if st.session_state.get(f'check_{c}')}
    # Lógica de reconstrução de fila
    if not st.session_state.bastao_queue and checked_on:
        print('!!! Fila vazia na carga, reconstruindo !!!')
        st.session_state.bastao_queue = sorted(list(checked_on))

    # GARANTE QUE APÓS CARREGAR TUDO, A ATRIBUIÇÃO DO BASTÃO SEJA VERIFICADA
    check_and_assume_baton()
    
    print('--- Estado Sincronizado (GLOBAL -> LOCAL) ---')


# ============================================
# 3. FUNÇÕES DE CALLBACK GLOBAIS
# ============================================

def update_queue(consultor):
    print(f'CALLBACK UPDATE QUEUE: {consultor}')
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    is_checked = st.session_state.get(f'check_{consultor}') 
    old_status_text = st.session_state.status_texto.get(consultor, '')
    was_holder_before = consultor == next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())

    if is_checked: # Tornando-se DISPONÍVEL (Voltando à Fila)
        log_status_change(consultor, old_status_text or 'Indisponível', '', duration)
        st.session_state.status_texto[consultor] = '' # Status de texto limpo (Disponível)
        if consultor not in st.session_state.bastao_queue:
            st.session_state.bastao_queue.append(consultor) # Adiciona ao final da fila
            print(f'Adicionado {consultor} ao fim da fila.')
        st.session_state.skip_flags[consultor] = False # Limpa o skip
        if consultor in st.session_state.priority_return_queue:
            st.session_state.priority_return_queue.remove(consultor)
            
    else: # Tornando-se INDISPONÍVEL (Ação manual de desmarcar)
        # Se já tem um status de Saída ou Bastão, mantenha-o ou mude para Indisponível
        if old_status_text not in STATUSES_DE_SAIDA and old_status_text != 'Bastão':
             log_old_status = old_status_text or ('Bastão' if was_holder_before else 'Disponível')
             log_status_change(consultor, log_old_status , 'Indisponível', duration)
             st.session_state.status_texto[consultor] = 'Indisponível' # Novo status: Indisponível
        
        if consultor in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(consultor)
            print(f'Removido {consultor} da fila.')
        st.session_state.skip_flags.pop(consultor, None) 
        
    baton_changed = check_and_assume_baton()
    if not baton_changed:
        save_state()
    # Retorna o controle. O Streamlit fará o rerun.


def rotate_bastao(): 
    """Ação 'Passar' que lida com a rotação e o reset do ciclo."""
    print('CALLBACK ROTATE BASTAO (PASSAR)')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return # SAÍDA EM ERRO

    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder:
        st.session_state.gif_warning = True
        st.rerun() # MANTIDO: Rerun em caso de erro/aviso
        return

    current_index = -1
    try: current_index = queue.index(current_holder)
    except ValueError:
        st.warning(f'Erro interno: Portador {current_holder} não encontrado na fila. Tentando corrigir.')
        if check_and_assume_baton(): st.rerun() # MANTIDO: Rerun se a correção interna for bem-sucedida
        return

    # --- LÓGICA DE RESET ---
    reset_triggered = False
    
    first_eligible_index_overall = find_next_holder_index(-1, queue, skips) 
    potential_next_index = find_next_holder_index(current_index, queue, skips)

    if potential_next_index != -1 and first_eligible_index_overall != -1:
        first_eligible_holder_overall = queue[first_eligible_index_overall]
        potential_next_holder = queue[potential_next_index]

        # Condição de Reset: O próximo APÓS o atual é o PRIMEIRO elegível da fila (ciclo completo)
        if potential_next_holder == first_eligible_holder_overall and current_holder != first_eligible_holder_overall:
            print("--- RESETANDO CICLO (Detectado ao passar para o primeiro elegível) ---")
            
            # Resetar as flags de pulo para todos os consultores ATIVOS (checados)
            st.session_state.skip_flags = {c: False for c in CONSULTORES if st.session_state.get(f'check_{c}')}
            skips = st.session_state.skip_flags 
            reset_triggered = True
            
            # O índice do próximo é confirmado como o primeiro do novo ciclo
            next_index = first_eligible_index_overall 
        else:
            # Não houve reset, segue normalmente
            next_index = potential_next_index
    else:
        next_index = -1
    # --- FIM LÓGICA DE RESET ---


    if next_index != -1:
        next_holder = queue[next_index]
        print(f'Passando bastão de {current_holder} para {next_holder} (Reset Triggered: {reset_triggered})')
        duration = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        
        # 1. Atualiza status do portador atual para '' (Disponível/Aguardando)
        log_status_change(current_holder, 'Bastão', '', duration)
        st.session_state.status_texto[current_holder] = '' # Volta para Disponível/Aguardando
        
        # 2. Atualiza status do novo portador para Bastão
        log_status_change(next_holder, st.session_state.status_texto.get(next_holder, ''), 'Bastão', timedelta(0))
        st.session_state.status_texto[next_holder] = 'Bastão'
        
        # 3. Atualiza controle
        st.session_state.bastao_start_time = datetime.now()
        st.session_state.skip_flags[next_holder] = False # Consome flag (se houver)
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound += 1 # AUMENTA O CONTADOR PARA FORÇAR A RE-RENDERIZAÇÃO DO SOM
        st.session_state.rotation_gif_start_time = datetime.now()
        
        save_state()
    else:
        # Se não há próximo elegível (fila vazia, todos pulando)
        print('Ninguém elegível. Forçando re-check e mantendo estado atual.')
        st.warning('Não há próximo consultor elegível na fila no momento.')
        check_and_assume_baton() 
        
    st.rerun() # MANTIDO: Para forçar a exibição do GIF de rotação e som.


def toggle_skip(): 
    print('CALLBACK TOGGLE SKIP')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return # SAÍDA EM ERRO

    current_skip_status = st.session_state.skip_flags.get(selected, False)
    # A checagem de disponibilidade deve ser feita no início.
    if not st.session_state.get(f'check_{selected}'): 
        st.warning(f'{selected} não está na fila para marcar/desmarcar pular.'); 
        return # SAÍDA EM ERRO
    
    st.session_state.skip_flags[selected] = not current_skip_status
    new_status_str = 'MARCADO para pular' if not current_skip_status else 'DESMARCADO para pular'
    print(f'{selected} foi {new_status_str}')

    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected == current_holder and st.session_state.skip_flags[selected]:
        print(f'Portador {selected} se marcou para pular. Tentando passar o bastão...')
        save_state() 
        rotate_bastao() # Chamará st.rerun()
        return # SAÍDA APÓS A ROTAÇÃO

    save_state() 
    # Retorna o controle. O Streamlit fará o rerun.


def update_status(status_text, change_to_available): 
    print(f'CALLBACK UPDATE STATUS: {status_text}')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': 
        st.warning('Selecione um consultor.'); return # SAÍDA EM ERRO

    # --- LÓGICA DE BLOQUEIO DE ALMOÇO ---
    if status_text == 'Almoço':
        if check_lunch_capacity(selected):
            # Se a checagem retornar True (deve bloquear), define o alerta
            st.session_state.lunch_alert_time = datetime.now()
            save_state()
            st.rerun() # MANTIDO: Para exibir o alerta imediatamente no topo (ÚNICO CASO CRÍTICO MANTIDO).
            return # Sai da função, bloqueando a marcação

    # Se passou pelo check_lunch_capacity (ou não era Almoço):
    # Garante que o status de bloqueio é limpo caso ele tente outra ação ou consiga o almoço
    if selected in st.session_state.skip_block:
         st.session_state.skip_block.pop(selected)
    # --- FIM LÓGICA DE BLOQUEIO DE ALMOÇO ---
    
    # 1. Marca como indisponível e atualiza status
    st.session_state[f'check_{selected}'] = False # Desmarca o checkbox
    was_holder = next((True for c, s in st.session_state.status_texto.items() if s == 'Bastão' and c == selected), False)
    old_status = st.session_state.status_texto.get(selected, '') or ('Bastão' if was_holder else 'Disponível')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, old_status, status_text, duration)
    st.session_state.status_texto[selected] = status_text # Define o status de Saída

    # 2. Remove da fila e limpa skip flag
    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.skip_flags.pop(selected, None)

    # 3. Gerencia a fila de prioridade
    if status_text == 'Saída Temporária':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)

    # 4. Verifica o bastão se o portador saiu
    print(f'... Fila: {st.session_state.bastao_queue}, Skips: {st.session_state.skip_flags}')
    baton_changed = False
    if was_holder: 
        baton_changed = check_and_assume_baton()
    
    if not baton_changed: save_state()
    # Retorna o controle. O Streamlit fará o rerun.


def manual_rerun():
    print('CALLBACK MANUAL RERUN')
    # Limpa o alerta de almoço ao tentar atualizar manualmente
    if st.session_state.lunch_alert_time:
         st.session_state.lunch_alert_time = None
         
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    save_state() 
    st.rerun() # MANTIDO: O objetivo desta função é forçar um rerun manual.

# ============================================
# 4. EXECUÇÃO PRINCIPAL DO STREAMLIT APP
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")

# O estado é carregado aqui do cache global
init_session_state()

# --- Scroll para o Topo ---
st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
# --- Fim Scroll para o Topo ---

st.title(f'Controle Bastão Cesupe {BASTAO_EMOJI}')
st.markdown("<hr style='border: 1px solid #E75480;'>", unsafe_allow_html=True)

# Auto Refresh & Timed Elements
gif_start_time = st.session_state.get('rotation_gif_start_time')
lunch_alert_time = st.session_state.get('lunch_alert_time')
show_rotation_gif = False 
refresh_interval = 40000 # 40 segundos (40.000 milissegundos)

if gif_start_time:
    try:
        elapsed = (datetime.now() - gif_start_time).total_seconds()
        if elapsed < 20: 
             show_rotation_gif = True; 
             refresh_interval = 2000 # 2 segundos durante a animação
        else: 
             st.session_state.rotation_gif_start_time = None
    except: 
        st.session_state.rotation_gif_start_time = None
        
# --- Lógica de Alerta de Almoço ---
show_lunch_alert = False
if lunch_alert_time:
    try:
        elapsed_lunch = (datetime.now() - lunch_alert_time).total_seconds()
        if elapsed_lunch < 30: # Mensagem desaparece em 30 segundos
            show_lunch_alert = True
            # Força o refresh rápido para desaparecer o alerta no tempo certo
            refresh_interval = min(refresh_interval, 1000) 
        else:
            st.session_state.lunch_alert_time = None # Limpa a mensagem
            
    except:
        st.session_state.lunch_alert_time = None
        
st_autorefresh(interval=refresh_interval, key='auto_rerun_key') 
# --- Fim Lógica de Alerta de Almoço ---

# Layout da Coluna Principal e Disponibilidade
col_principal, col_disponibilidade = st.columns([1.5, 1])

# --- Coluna Principal: Alertas e Responsável ---
with col_principal:
    # --- NOVO: Container para injeção de som fora da UI principal ---
    sound_placeholder = st.empty()
    # --- FIM NOVO CONTAINER DE SOM ---
    
    # --- REPOSICIONAMENTO DO SOM ---
    # O som é injetado no placeholder
    if st.session_state.get('play_sound', 0) > 0:
        # CORREÇÃO FINAL: Injeta o componente diretamente no placeholder com uma chave simples,
        # confiando que o placeholder força a re-renderização.
        sound_placeholder.components.v1.html(play_sound_html(), height=0, width=0, scrolling=False, key="sound_injection_key")
        # DIMINUI O CONTADOR APÓS TENTAR REPRODUZIR (para garantir que só toque 1x por evento)
        st.session_state.play_sound -= 1
    # --- FIM REPOSICIONAMENTO DO SOM ---
    
    # --- CONTAINER PARA ALERTAS (Rotação e Almoço) ---
    alert_container = st.container() 
    
    with alert_container:
        if show_rotation_gif:
            st.image(GIF_URL_ROTATION, width=200, caption='Bastão Passado!')
        
        # Alerta de Almoço (dentro do container e em colunas)
        if show_lunch_alert:
            alert_col_text, alert_col_gif = st.columns([0.7, 0.3]) # Ajuste as proporções conforme necessário
            
            consultor_bloqueado = st.session_state.consultor_selectbox 
            
            with alert_col_text:
                st.error(f'🚫 **{consultor_bloqueado}**, verificar marcação. Mais da metade dos consultores encontra-se em horário de almoço.')
                
            with alert_col_gif:
                st.image(GIF_URL_LUNCH_ALERT, width=150)
        
        # Aviso de Ação Inválida (também pode ir aqui para consistência)
        if st.session_state.get('gif_warning', False):
            st.error('🚫 Ação inválida! Verifique as regras.'); st.image(GIF_URL_WARNING, width=150)

    # --- Fim Container de Alertas ---

    st.header("Responsável pelo Bastão")
    _, col_time = st.columns([0.25, 0.75])
    duration = timedelta()
    responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if responsavel and st.session_state.bastao_start_time:
        try: duration = datetime.now() - st.session_state.bastao_start_time
        except: pass
    col_time.markdown(f'#### 🕒 Tempo: **{format_time_duration(duration)}**')
    if responsavel:
        st.markdown(f'<span style="font-size: 2em; font-weight: bold;">{responsavel}</span>', unsafe_allow_html=True)
    else: st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
    st.markdown("###")

    st.header("Próximos da Fila")
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_index = queue.index(responsavel) if responsavel in queue else -1
    proximo_index = find_next_holder_index(current_index, queue, skips)
    proximo = queue[proximo_index] if proximo_index != -1 else None
    restante = []
    if proximo_index != -1: 
        num_q = len(queue)
        start_check_idx = (proximo_index + 1) % num_q
        current_check_idx = start_check_idx
        checked_count = 0
        while checked_count < num_q:
            if current_check_idx == start_check_idx and checked_count > 0: break
            if 0 <= current_check_idx < num_q:
                consultor = queue[current_check_idx]
                if consultor != responsavel and consultor != proximo and \
                   not skips.get(consultor, False) and \
                   st.session_state.get(f'check_{consultor}'):
                    restante.append(consultor)
            current_check_idx = (current_check_idx + 1) % num_q
            checked_count += 1

    if proximo:
        st.markdown(f'### 1º: **{proximo}**')
    if restante:
        st.markdown(f'#### 2º em diante: {", ".join(restante)}')
    if not proximo and not restante:
        if responsavel: st.markdown('*Apenas o responsável atual é elegível.*')
        elif queue and all(skips.get(c, False) or not st.session_state.get(f'check_{c}') for c in queue) : st.markdown('*Todos disponíveis estão marcados para pular...*')
        else: st.markdown('*Ninguém elegível na fila.*')
    elif not restante and proximo: st.markdown("&nbsp;")


    # --- Seção Pular (Estilo Ajustado) ---
    skipped_consultants = [c for c, is_skipped in skips.items() if is_skipped and st.session_state.get(f'check_{c}')]
    if skipped_consultants:
        skipped_text = ', '.join(sorted(skipped_consultants))
        num_skipped = len(skipped_consultants)
        titulo = '**Consultor Pulou:**' if num_skipped == 1 else '**Consultores Pularam:**'
        verbo_pular = 'pulou' if num_skipped == 1 else 'pularam'
        verbo_retornar = 'Irá retornar' if num_skipped == 1 else 'Irão retornar'
        st.markdown(f'''
        <div style="margin-top: 15px;">
            <span style="color: #FFC107; font-weight: bold;">{titulo}</span><br>
            <span style="color: black; font-weight: normal;">{skipped_text} {verbo_pular} o bastão!</span><br>
            <span style="color: black; font-weight: normal;">{verbo_retornar} no próximo ciclo!</span>
        </div>
        ''', unsafe_allow_html=True)
    # --- Fim Seção Pular ---

    st.markdown("###")
    st.header("**Consultor**")
    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### "); st.markdown("**Ações:**")
    
    # 7 COLUNAS PARA OS BOTÕES
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7) 
    
    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True, help='Passa o bastão para o próximo elegível. Apenas o responsável atual.')
    c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True, help='Marca/Desmarca o consultor selecionado para ser pulado na próxima rotação.')
    c3.button('✏️ Atividade', on_click=update_status, args=('Atividade', False,), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=update_status, args=('Almoço', False,), use_container_width=True)
    c5.button('👤 Ausente', on_click=update_status, args=('Ausente', False,), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=update_status, args=('Sessão', False,), use_container_width=True)
    c7.button('🚶 Saída', on_click=update_status, args=('Saída Temporária', False,), use_container_width=True)
    
    st.markdown("####")
    st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)
    st.markdown("---")

# --- Coluna Disponibilidade ---
with col_disponibilidade:
    st.header('Status dos Consultores')
    st.markdown('Marque/Desmarque para entrar/sair.')
    
    ui_lists = {'fila': [], 'atividade': [], 'almoco': [], 'saida': [], 'ausente': [], 'sessao': [], 'indisponivel': []}
    
    for nome in CONSULTORES:
        is_checked = st.session_state.get(f'check_{nome}', False)
        status = st.session_state.status_texto.get(nome, 'Indisponível')
        
        if status == 'Bastão': 
            ui_lists['fila'].insert(0, nome)
        elif status == '': 
            ui_lists['fila'].append(nome) # Status '' (vazio) significa 'Aguardando'
        elif status == 'Atividade': 
            ui_lists['atividade'].append(nome)
        elif status == 'Almoço': 
            ui_lists['almoco'].append(nome)
        elif status == 'Ausente':
            ui_lists['ausente'].append(nome)
        elif status == 'Sessão':
            ui_lists['sessao'].append(nome)
        elif status == 'Saída Temporária': 
            ui_lists['saida'].append(nome)
        elif status == 'Indisponível': 
            ui_lists['indisponivel'].append(nome)

    st.subheader(f'✅ Na Fila ({len(ui_lists['fila'])})')
    render_order = [c for c in queue if c in ui_lists['fila']] + [c for c in ui_lists['fila'] if c not in queue]
    if not render_order: st.markdown('_Ninguém disponível._')
    else:
        for nome in render_order:
            col_nome, col_check = st.columns([0.8, 0.2])
            key = f'check_{nome}'
            
            col_check.checkbox(' ', key=key, on_change=update_queue, args=(nome,), label_visibility='collapsed')
            
            skip_flag = skips.get(nome, False)
            if nome == responsavel:
                display = f'<span style="background-color: #E75480; color: white; padding: 2px 6px; border-radius: 5px; font-weight: bold;">🔥 {nome}</span>'
            elif skip_flag:
                display = f'**{nome}** :orange-background[Pulando ⏭️]'
            else:
                 display = f'**{nome}** :blue-background[Aguardando]'
            col_nome.markdown(display, unsafe_allow_html=True)
    st.markdown('---')

    def render_section(title, icon, names, tag_color):
        st.subheader(f'{icon} {title} ({len(names)})')
        if not names: st.markdown(f'_Ninguém em {title.lower()}._')
        else:
            for nome in sorted(names):
                col_nome, col_check = st.columns([0.8, 0.2])
                key = f'check_{nome}'
                
                col_check.checkbox(' ', key=key, value=False, on_change=update_queue, args=(nome,), label_visibility='collapsed')
                
                col_nome.markdown(f'**{nome}** :{tag_color}-background[{title}]', unsafe_allow_html=True)
        st.markdown('---')

    render_section('Atividade', '✏️', ui_lists['atividade'], 'yellow')
    render_section('Almoço', '🍽️', ui_lists['almoco'], 'blue')
    render_section('Ausente', '👤', ui_lists['ausente'], 'violet') 
    render_section('Sessão', '🎙️', ui_lists['sessao'], 'green')   
    render_section('Saída', '🚶', ui_lists['saida'], 'red')
    render_section('Indisponível', '❌', ui_lists['indisponivel'], 'grey')

    if datetime.now().hour >= 20 and datetime.now().date() > (st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()):
        send_daily_report()

print('--- FIM DO RENDER ---')
