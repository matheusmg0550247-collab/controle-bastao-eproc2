# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh

# --- Constantes ---
GOOGLE_CHAT_WEBHOOK_RELATORIO = ""
CHAT_WEBHOOK_BASTAO = ""
BASTAO_EMOJI = "🌸"
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
CONSULTORES = sorted([
    "Barbara", "Bruno", "Claudia", "Douglas", "Fábio", "Glayce", "Isac",
    "Isabela", "Ivana", "Leonardo", "Morôni", "Michael", "Pablo", "Ranyer",
    "Victoria"
])
LOG_FILE = 'status_log.json'
STATE_FILE = 'app_state.json'
STATUS_SAIDA_PRIORIDADE = ['Saída Temporária']
STATUSES_DE_SAIDA = ['Atividade', 'Almoço', 'Saída Temporária']
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/refs/heads/main/doorbell-223669.mp3"

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

def date_serializer(obj):
    if isinstance(obj, datetime): return obj.isoformat()
    return str(obj)

def save_state():
    state_to_save = {
        'status_texto': st.session_state.status_texto,
        'bastao_queue': st.session_state.bastao_queue,
        'skip_flags': st.session_state.skip_flags,
        'bastao_start_time': st.session_state.bastao_start_time,
        'current_status_starts': st.session_state.current_status_starts,
        'report_last_run_date': st.session_state.report_last_run_date,
        'bastao_counts': st.session_state.bastao_counts,
        'priority_return_queue': st.session_state.priority_return_queue,
        'rotation_gif_start_time': st.session_state.get('rotation_gif_start_time'),
    }
    try:
        with open(STATE_FILE, 'w') as f: json.dump(state_to_save, f, indent=4, default=date_serializer)
        print(f'*** Estado Salvo ***')
    except Exception as e: print(f'Erro ao salvar estado: {e}')

def load_state():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, 'r') as f: data = json.load(f)
        for key in ['bastao_start_time', 'report_last_run_date', 'rotation_gif_start_time']:
            if data.get(key) and isinstance(data[key], str):
                try: data[key] = datetime.fromisoformat(data[key])
                except ValueError: data[key] = None
        if 'current_status_starts' in data and isinstance(data['current_status_starts'], dict):
             temp_starts = {}
             for c, ts in data['current_status_starts'].items():
                 if c in CONSULTORES:
                     if ts and isinstance(ts, str):
                         try: temp_starts[c] = datetime.fromisoformat(ts)
                         except ValueError: temp_starts[c] = datetime.now()
                     elif isinstance(ts, datetime): temp_starts[c] = ts
                     else: temp_starts[c] = datetime.now()
             data['current_status_starts'] = temp_starts
        else: data['current_status_starts'] = {}
        data['bastao_queue'] = [c for c in data.get('bastao_queue', []) if c in CONSULTORES]
        data.setdefault('status_texto', {})
        data.setdefault('bastao_counts', {})
        data.setdefault('priority_return_queue', [])
        data.setdefault('skip_flags', {})
        return data
    except Exception as e: print(f'Erro ao carregar estado: {e}. Resetando.'); return {}

def send_chat_notification_internal(c, s): pass
def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'
def load_logs(): return []
def save_logs(l): pass

def log_status_change(consultor, old_status, new_status, duration):
    print(f'LOG: {consultor} de "{old_status or '-'}" para "{new_status or '-'}" após {duration}')
    if not isinstance(duration, timedelta): duration = timedelta(0)
    # Ensure consultor key exists before updating
    if consultor not in st.session_state.current_status_starts:
        st.session_state.current_status_starts[consultor] = datetime.now() # Initialize if missing
    # Always update the start time for the *new* status
    st.session_state.current_status_starts[consultor] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def send_daily_report(): pass

def init_session_state():
    persisted_state = load_state()
    defaults = {
        'status_texto': {nome: '' for nome in CONSULTORES}, 'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None, 'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min, 'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [], 'rotation_gif_start_time': None,
    }
    for key, default in defaults.items():
        st.session_state.setdefault(key, persisted_state.get(key, default))
        # Type safety after load
        if key == 'bastao_queue' and not isinstance(st.session_state.bastao_queue, list): st.session_state.bastao_queue = []
        if key == 'skip_flags' and not isinstance(st.session_state.skip_flags, dict): st.session_state.skip_flags = {}

    loaded_starts = persisted_state.get('current_status_starts', {})
    for nome in CONSULTORES:
        st.session_state.current_status_starts.setdefault(nome, loaded_starts.get(nome, datetime.now()))

    st.session_state.bastao_queue = [c for c in st.session_state.bastao_queue if c in CONSULTORES]
    st.session_state.skip_flags = {c: v for c, v in st.session_state.skip_flags.items() if c in CONSULTORES}

    # Align checkboxes based only on bastao_queue and status_texto now
    for nome in CONSULTORES:
        is_active = nome in st.session_state.bastao_queue or bool(st.session_state.status_texto.get(nome))
        st.session_state.setdefault(f'check_{nome}', is_active)

    # Rebuild queue if empty but people are checked
    checked_on = {c for c in CONSULTORES if st.session_state.get(f'check_{c}')}
    if not st.session_state.bastao_queue and checked_on:
        print('!!! Fila vazia na carga, reconstruindo !!!')
        # Maintain order if possible, add new ones at the end
        master_order_from_state = persisted_state.get('master_order', []) # Load temp master if available
        master_order_from_state = [c for c in master_order_from_state if c in CONSULTORES]
        st.session_state.bastao_queue = [c for c in master_order_from_state if c in checked_on]
        for c in checked_on:
            if c not in st.session_state.bastao_queue:
                st.session_state.bastao_queue.append(c)

    print('--- Estado Inicializado ---')
    print(f' Fila: {st.session_state.bastao_queue}, Skip Flags: {st.session_state.skip_flags}')

def find_next_holder_index(current_index, queue, skips):
    # ... (implementação como antes) ...
    if not queue: return -1
    num_consultores = len(queue)
    if current_index >= num_consultores: current_index = -1 # Handle invalid index

    next_idx = (current_index + 1) % num_consultores
    attempts = 0
    while attempts < num_consultores:
        consultor = queue[next_idx]
        # Checkbox must be ON and skip flag must be FALSE
        if not skips.get(consultor, False) and st.session_state.get(f'check_{consultor}'):
            return next_idx # Found the next valid one
        next_idx = (next_idx + 1) % num_consultores
        attempts += 1
    print("WARN: find_next_holder_index não encontrou ninguém elegível.")
    return -1 # Didn't find anyone


def check_and_assume_baton():
    # ... (implementação como antes, com prints em PT-BR) ...
    print('--- VERIFICA E ASSUME BASTÃO ---')
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder_status = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)

    # 1. Is current holder still valid? (In queue, checked ON)
    is_current_valid = (current_holder_status
                      and current_holder_status in queue
                      and st.session_state.get(f'check_{current_holder_status}'))

    # 2. Find the first eligible person (from start if current invalid, else doesn't matter)
    first_eligible_index = find_next_holder_index(-1, queue, skips) # Always search from start
    next_holder = queue[first_eligible_index] if first_eligible_index != -1 else None

    print(f'Fila: {queue}, Skips: {skips}, Próximo Elegível: {next_holder}, Portador Atual (Status): {current_holder_status}, Atual é Válido?: {is_current_valid}')

    # 3. Determine who *should* have the baton now
    should_have_baton = None
    if is_current_valid:
        should_have_baton = current_holder_status # Keep current if valid
    elif next_holder:
        should_have_baton = next_holder # Assign to first eligible if current is invalid
    # Else: No one is eligible, should_have_baton remains None

    # 4. Update statuses if needed
    changed = False
    # Clear baton from anyone who shouldn't have it
    for c in CONSULTORES:
        if c != should_have_baton and st.session_state.status_texto.get(c) == 'Bastão':
            print(f'Limpando bastão de {c} (não deveria ter)')
            duration = datetime.now() - st.session_state.current_status_starts.get(c, datetime.now())
            log_status_change(c, 'Bastão', '', duration)
            st.session_state.status_texto[c] = ''
            changed = True

    # Assign baton if someone should have it and doesn't
    if should_have_baton and st.session_state.status_texto.get(should_have_baton) != 'Bastão':
        print(f'Atribuindo bastão para {should_have_baton}')
        old_status = st.session_state.status_texto.get(should_have_baton, '')
        duration = datetime.now() - st.session_state.current_status_starts.get(should_have_baton, datetime.now())
        log_status_change(should_have_baton, old_status, 'Bastão', duration)
        st.session_state.status_texto[should_have_baton] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        # Play sound only if it changed from someone else or no one
        if current_holder_status != should_have_baton:
            st.session_state.play_sound = True
        # Clear the skip flag for the person assuming the baton
        if st.session_state.skip_flags.get(should_have_baton):
             print(f' Consumindo skip flag de {should_have_baton} ao assumir.')
             st.session_state.skip_flags[should_have_baton] = False
        changed = True
    # Ensure start time is None if no one has the baton
    elif not should_have_baton and st.session_state.bastao_start_time is not None:
         st.session_state.bastao_start_time = None
         changed = True # Considered a change if time was cleared

    if changed:
        print('Estado do bastão mudou.')
        save_state()
    return changed


# ============================================
# 3. FUNÇÕES DE CALLBACK GLOBAIS
# ============================================

def update_queue(consultor):
    # ... (implementação como antes, com prints em PT-BR) ...
    print(f'CALLBACK UPDATE QUEUE: {consultor}')
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    is_checked = st.session_state.get(f'check_{consultor}') # New state
    old_status_text = st.session_state.status_texto.get(consultor, '')
    was_holder_before = consultor == next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())

    # Update queue BEFORE logging/checking baton
    if is_checked:
        if consultor not in st.session_state.bastao_queue:
             st.session_state.bastao_queue.append(consultor) # Add to end
        st.session_state.skip_flags[consultor] = False # Ensure not skipped
        st.session_state.status_texto[consultor] = '' # Clear specific status
        log_status_change(consultor, old_status_text or 'Indisponível', '', duration)
    else: # Becoming unavailable
        if consultor in st.session_state.bastao_queue:
             st.session_state.bastao_queue.remove(consultor)
        st.session_state.skip_flags.pop(consultor, None) # Remove flag
        st.session_state.status_texto[consultor] = '' # Clear specific status
        log_old_status = old_status_text or ('Bastão' if was_holder_before else 'Disponível')
        log_status_change(consultor, log_old_status , 'Indisponível', duration)

    print(f'... Fila: {st.session_state.bastao_queue}, Skips: {st.session_state.skip_flags}')
    baton_changed = check_and_assume_baton()
    if not baton_changed: save_state() # Save if check_assume didn't
    st.rerun()


def rotate_bastao(): # Action 'Passar'
    # ... (implementação como antes, com prints em PT-BR) ...
    print('CALLBACK ROTATE BASTAO (PASSAR)')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder: st.session_state.gif_warning = True; st.rerun(); return

    try: current_index = queue.index(current_holder)
    except ValueError: print('ERRO: Portador não está na fila?'); return

    next_index = find_next_holder_index(current_index, queue, skips)

    if next_index != -1:
        next_holder = queue[next_index]
        print(f'Passando bastão de {current_holder} para {next_holder}')
        duration = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        log_status_change(current_holder, 'Bastão', '', duration)
        st.session_state.status_texto[current_holder] = ''
        log_status_change(next_holder, st.session_state.status_texto.get(next_holder, ''), 'Bastão', timedelta(0))
        st.session_state.status_texto[next_holder] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        st.session_state.skip_flags[next_holder] = False # Consume skip flag
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound = True
        st.session_state.rotation_gif_start_time = datetime.now()
        save_state()
    else:
        print('Não foi encontrado próximo elegível. Bastão permanece.')
        st.warning('Não há próximo consultor elegível na fila.')
        # Don't save state if nothing changed, prevents unnecessary saves

    st.rerun()


def toggle_skip(): # Action 'Pular'
    # ... (implementação como antes, com prints em PT-BR) ...
    print('CALLBACK TOGGLE SKIP')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    if selected not in st.session_state.bastao_queue: st.warning(f'{selected} não está na fila.'); return

    current_skip_status = st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = not current_skip_status
    new_status_str = 'MARCADO para pular' if not current_skip_status else 'DESMARCADO para pular'
    print(f'{selected} foi {new_status_str}')

    # If the current holder marks themselves to be skipped, immediately try to rotate
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected == current_holder and st.session_state.skip_flags[selected]:
        print(f'Portador {selected} se marcou para pular. Tentando passar o bastão...')
        # Call rotate_bastao directly, it will find the next valid person
        save_state() # Save the skip flag change first
        rotate_bastao() # This function handles rerun and saving state changes from rotation
        return # Avoid double rerun/save

    save_state() # Save the changed skip flag
    st.rerun()

def update_status(status_text, change_to_available): # Unavailable + Status
    # ... (implementação como antes, com prints em PT-BR) ...
    print(f'CALLBACK UPDATE STATUS: {status_text}')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return

    st.session_state[f'check_{selected}'] = False # Mark unavailable
    was_holder = next((True for c, s in st.session_state.status_texto.items() if s == 'Bastão' and c == selected), False)
    old_status = st.session_state.status_texto.get(selected, '') or ('Bastão' if was_holder else 'Disponível')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, old_status, status_text, duration)
    st.session_state.status_texto[selected] = status_text # Set the specific status

    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.skip_flags.pop(selected, None)

    if status_text == 'Saída Temporária':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)

    print(f'... Fila: {st.session_state.bastao_queue}, Skips: {st.session_state.skip_flags}')
    baton_changed = False
    if was_holder: # If holder left, must find next
        baton_changed = check_and_assume_baton()
    if not baton_changed: save_state() # Save state if check_assume didn't
    st.rerun()

def manual_rerun():
    # ... (implementação como antes, com prints em PT-BR) ...
    print('CALLBACK MANUAL RERUN')
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.rerun()


# ============================================
# 4. EXECUÇÃO PRINCIPAL DO STREAMLIT APP
# ============================================

# --- Configuração Inicial ---
st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")
st.markdown('<style>div.stAlert { display: none !important; }</style>', unsafe_allow_html=True)
init_session_state() # Load/Initialize state AFTER page config

st.title(f'Controle Bastão Cesupe {BASTAO_EMOJI}')
st.markdown("<hr style='border: 1px solid #E75480;'>", unsafe_allow_html=True)

# --- Auto Refresh & Timed Elements ---
gif_start_time = st.session_state.get('rotation_gif_start_time')
show_gif = False; refresh_interval = 30000
if gif_start_time:
    try:
        elapsed = (datetime.now() - gif_start_time).total_seconds()
        if elapsed < 20: show_gif = True; refresh_interval = 5000
        else: st.session_state.rotation_gif_start_time = None
    except: st.session_state.rotation_gif_start_time = None
st_autorefresh(interval=refresh_interval, key='auto_rerun_key')
if st.session_state.get('play_sound', False):
    st.components.v1.html(play_sound_html(), height=0, width=0); st.session_state.play_sound = False
if show_gif: st.image(GIF_URL_ROTATION, width=200, caption='Bastão Passado!')
if st.session_state.get('gif_warning', False):
    st.error('🚫 Ação inválida! Apenas o portador atual pode usar 🎯 Passar.'); st.image(GIF_URL_WARNING, width=150) # Adjusted error msg

# --- Garantir Assunção Inicial/Pós-Reset ---
holder_exists = any(s == 'Bastão' for s in st.session_state.status_texto.values())
# Check if anyone is actually eligible (in queue, checked, not skipped)
eligible_exists = any(c not in st.session_state.skip_flags.get(c, False) for c in st.session_state.bastao_queue if st.session_state.get(f'check_{c}'))
if not holder_exists and st.session_state.bastao_queue and eligible_exists:
    print('!!! FORÇANDO CHECK ASSUME BASTÃO NO RENDER !!!')
    if not st.session_state.get('_assign_attempt', False):
        st.session_state._assign_attempt = True
        if check_and_assume_baton():
            print('--> Bastão reassumido no render, rerunning...')
            st.rerun()
    else:
        print('WARN: Segunda tentativa de assumir bastão no render evitada.')
# Clear the flag after the check
if '_assign_attempt' in st.session_state: del st.session_state['_assign_attempt']


# --- Layout ---
col_principal, col_disponibilidade = st.columns([1.5, 1])
queue = st.session_state.bastao_queue
skips = st.session_state.skip_flags
responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
current_index = queue.index(responsavel) if responsavel in queue else -1
proximo_index = find_next_holder_index(current_index, queue, skips)
proximo = queue[proximo_index] if proximo_index != -1 else None

# Calculate 'restante' more carefully
restante = []
if proximo_index != -1:
    num_q = len(queue)
    start_check = (proximo_index + 1) % num_q
    idx = start_check
    count = 0
    while count < num_q:
        # Stop if we loop back to the current holder or the next one
        if idx == current_index or idx == proximo_index:
            idx = (idx + 1) % num_q
            count += 1
            if idx == start_check: break # Prevent infinite loop if only 1 or 2 people
            continue

        consultor = queue[idx]
        # Must not be skipped and must be checked ON
        if not skips.get(consultor, False) and st.session_state.get(f'check_{consultor}'):
            restante.append(consultor)

        idx = (idx + 1) % num_q
        count += 1
        if idx == start_check: break # Full loop


with col_principal:
    st.header("Responsável pelo Bastão")
    _, col_time = st.columns([0.25, 0.75])
    duration = timedelta()
    if responsavel and st.session_state.bastao_start_time:
        try: duration = datetime.now() - st.session_state.bastao_start_time
        except: pass
    col_time.markdown(f'#### 🕒 Tempo: **{format_time_duration(duration)}**')
    if responsavel:
        st.markdown(f'<span style="background-color: #E75480; color: white; padding: 5px 10px; border-radius: 5px; font-size: 2em; font-weight: bold;">🔥 {responsavel}</span>', unsafe_allow_html=True)
    else: st.markdown('## (Ninguém com o bastão)')
    st.markdown("###")
    st.header("Próximos da Fila")
    if proximo: st.markdown(f'### 1º: **{proximo}**')
    if restante: st.markdown(f'#### 2º em diante: {", ".join(restante)}')
    if not proximo and not restante:
         if responsavel: st.markdown('*Apenas o responsável atual é elegível.*')
         else: st.markdown('*Ninguém elegível na fila.*')
    elif not restante and proximo: st.markdown(" ") # Space if only 'proximo'
    st.markdown("###")
    st.header("**Consultor**")
    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### "); st.markdown("**Ações:**")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True, help='Passa o bastão para o próximo elegível. Apenas o responsável atual.')
    c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True, help='Marca/Desmarca o consultor selecionado para ser pulado na próxima rotação.') # Changed action
    c3.button('✏️ Atividade', on_click=update_status, args=('Atividade', False,), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=update_status, args=('Almoço', False,), use_container_width=True)
    c5.button('🚶 Saída', on_click=update_status, args=('Saída Temporária', False,), use_container_width=True)
    st.markdown("####")
    st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)
    st.markdown("---")

with col_disponibilidade:
    st.header('Status dos Consultores')
    st.markdown('Marque/Desmarque para entrar/sair.')
    ui_lists = {'fila': [], 'atividade': [], 'almoco': [], 'saida': [], 'indisponivel': []}
    for nome in CONSULTORES:
        is_checked = st.session_state.get(f'check_{nome}', False)
        status = st.session_state.status_texto.get(nome, '')
        if is_checked: ui_lists['fila'].append(nome)
        elif status == 'Atividade': ui_lists['atividade'].append(nome)
        elif status == 'Almoço': ui_lists['almoco'].append(nome)
        elif status == 'Saída Temporária': ui_lists['saida'].append(nome)
        else: ui_lists['indisponivel'].append(nome)

    st.subheader(f'✅ Na Fila ({len(ui_lists['fila'])})')
    # Render based on the current bastao_queue order
    render_order = [c for c in queue if c in ui_lists['fila']] + [c for c in ui_lists['fila'] if c not in queue] # Maintain queue order + new entries
    if not render_order: st.markdown('_Ninguém disponível._')
    else:
        for nome in render_order:
            col_nome, col_check = st.columns([0.8, 0.2])
            key = f'check_{nome}'
            col_check.checkbox(' ', key=key, on_change=update_queue, args=(nome,), label_visibility='collapsed') # on_change is safer
            skip_flag = skips.get(nome, False)
            if nome == responsavel:
                display = f'<span style="background-color: #E75480; color: white; padding: 2px 6px; border-radius: 5px; font-weight: bold;">🔥 {nome}</span>'
            elif skip_flag:
                display = f'**{nome}** :orange-background[Pulando ⏭️]' # Marked to be skipped
            else:
                 display = f'**{nome}** :blue-background[Aguardando]' # In queue, waiting
            col_nome.markdown(display, unsafe_allow_html=True)
    st.markdown('---')

    def render_section(title, icon, names, tag_color):
        st.subheader(f'{icon} {title} ({len(names)})')
        if not names: st.markdown(f'_Ninguém em {title.lower()}._')
        else:
            for nome in sorted(names):
                col_nome, col_check = st.columns([0.8, 0.2])
                key = f'check_{nome}'
                col_check.checkbox(' ', key=key, on_change=update_queue, args=(nome,), label_visibility='collapsed') # on_change
                col_nome.markdown(f'**{nome}** :{tag_color}-background[{title}]', unsafe_allow_html=True)
        st.markdown('---')
    render_section('Atividade', '✏️', ui_lists['atividade'], 'yellow')
    render_section('Almoço', '🍽️', ui_lists['almoco'], 'blue')
    render_section('Saída', '🚶', ui_lists['saida'], 'red')
    render_section('Indisponível', '❌', ui_lists['indisponivel'], 'grey')

    # Daily report check...
    print('--- FIM DO RENDER ---')
