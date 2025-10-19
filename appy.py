# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS (FORA)
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

# --- Constantes Globais ---
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
# 2. FUNÇÕES AUXILIARES (FORA)
# ============================================

def date_serializer(obj):
    if isinstance(obj, datetime): return obj.isoformat()
    return str(obj)

def save_state():
    state_to_save = {
        'status_texto': st.session_state.status_texto,
        'bastao_queue': st.session_state.bastao_queue,
        'bastao_start_time': st.session_state.bastao_start_time,
        'current_status_starts': st.session_state.current_status_starts,
        'report_last_run_date': st.session_state.report_last_run_date,
        'bastao_counts': st.session_state.bastao_counts,
        'priority_return_queue': st.session_state.priority_return_queue,
        'rotation_gif_start_time': st.session_state.get('rotation_gif_start_time'),
        'master_order': st.session_state.master_order,
    }
    try:
        with open(STATE_FILE, 'w') as f: json.dump(state_to_save, f, indent=4, default=date_serializer)
        print("Estado salvo com sucesso.")
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
                 if ts and isinstance(ts, str):
                     try: temp_starts[c] = datetime.fromisoformat(ts)
                     except ValueError: temp_starts[c] = datetime.now()
                 # If it's already a datetime (from previous load), keep it
                 elif isinstance(ts, datetime):
                     temp_starts[c] = ts
                 else: temp_starts[c] = datetime.now() # Fallback
             data['current_status_starts'] = temp_starts
        else: data['current_status_starts'] = {} # Ensure it exists

        if 'master_order' not in data or not isinstance(data['master_order'], list): data['master_order'] = []
        # Ensure all required keys exist, providing defaults if necessary
        data.setdefault('status_texto', {})
        data.setdefault('bastao_queue', [])
        data.setdefault('bastao_counts', {})
        data.setdefault('priority_return_queue', [])
        return data
    except Exception as e: print(f'Erro ao carregar estado: {e}. Resetando.'); return {}

def send_chat_notification_internal(consultor, status):
    # Implementation omitted
    return False

def play_sound_html():
    return f"""<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>"""

def load_logs():
    try:
        with open(LOG_FILE, 'r') as f: return json.load(f)
    except: return []

def save_logs(logs):
    try:
        with open(LOG_FILE, 'w') as f: json.dump(logs, f, indent=4, default=date_serializer)
    except Exception as e: print(f"Erro ao salvar logs: {e}")


def log_status_change(consultor, old_status, new_status, duration):
    print(f'LOG: {consultor} de "{old_status or 'Disponível'}" para "{new_status or 'Disponível'}" após {duration}')
    if not isinstance(duration, timedelta):
         print(f"WARN: Duração inválida para log: {duration}")
         duration = timedelta(0) # Avoid erroring out
    logs = load_logs()
    start_time = st.session_state.current_status_starts.get(consultor, datetime.now())
    log_entry = {
        'consultor': consultor,
        'old_status': old_status if old_status else 'Disponível',
        'new_status': new_status if new_status else 'Disponível',
        'duration_s': duration.total_seconds(),
        'start_time': start_time.isoformat(),
        'end_time': datetime.now().isoformat()
    }
    logs.append(log_entry)
    save_logs(logs)
    st.session_state.current_status_starts[consultor] = datetime.now()
    # Save state is called by the main action

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds())
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def send_daily_report():
   # Implementation omitted
   pass

def init_session_state():
    persisted_state = load_state()
    defaults = {
        'status_texto': {nome: '' for nome in CONSULTORES},
        'bastao_queue': [],
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'rotation_gif_start_time': None,
        'master_order': [],
        'completed_this_lap': set(), # Always reset on load/refresh
        'skipped_this_lap': set()    # Always reset on load/refresh
    }
    for key, default_value in defaults.items():
        # Load from persisted state if available, otherwise use default
        st.session_state.setdefault(key, persisted_state.get(key, default_value))
        # Ensure correct types after loading (especially for sets which aren't JSON serializable)
        if key in ['completed_this_lap', 'skipped_this_lap']:
             st.session_state[key] = set() # Force reset to empty set

    # Correct current_status_starts from loaded data if necessary
    loaded_starts = persisted_state.get('current_status_starts', {})
    for nome in CONSULTORES:
        st.session_state.current_status_starts.setdefault(nome, loaded_starts.get(nome, datetime.now()))


    # Align checkboxes based on current state (important after load)
    active_people_in_queue = set(st.session_state.bastao_queue)
    for nome in CONSULTORES:
        checkbox_key = f'check_{nome}'
        is_active = nome in active_people_in_queue or nome in st.session_state.skipped_this_lap or bool(st.session_state.status_texto.get(nome))
        st.session_state.setdefault(checkbox_key, is_active)

    # Clean master_order: remove anyone not in CONSULTORES (if list changed)
    st.session_state.master_order = [c for c in st.session_state.master_order if c in CONSULTORES]
    # Clean bastao_queue
    st.session_state.bastao_queue = [c for c in st.session_state.bastao_queue if c in CONSULTORES and st.session_state.get(f'check_{c}')]


    print("--- Estado Inicializado ---")
    print(f" Master Order: {st.session_state.master_order}")
    print(f" Fila Ativa: {st.session_state.bastao_queue}")
    print(f" Skipped: {st.session_state.skipped_this_lap}")
    print(f" Completed: {st.session_state.completed_this_lap}")
    print(f" Status Texto: {st.session_state.status_texto}")
    print(f" Checkboxes: { {c: st.session_state.get(f'check_{c}') for c in CONSULTORES} }")


def check_cycle_reset():
    master = st.session_state.master_order
    skipped = st.session_state.skipped_this_lap
    completed = st.session_state.completed_this_lap
    should_complete = set(c for c in master if c not in skipped and st.session_state.get(f'check_{c}', False))
    print(f'CHECK RESET: Should complete: {should_complete}, Completed: {completed}')
    if should_complete and should_complete.issubset(completed):
        print('--- RESETANDO CICLO ---')
        st.session_state.completed_this_lap = set()
        st.session_state.skipped_this_lap = set()
        st.session_state.bastao_queue = [c for c in master if st.session_state.get(f'check_{c}', False)]
        print(f'Nova Fila Pós-Reset: {st.session_state.bastao_queue}')
        return True
    return False

def check_and_assume_baton():
    print('--- CHECK ASSUME BATON ---')
    queue = st.session_state.bastao_queue
    skipped = st.session_state.skipped_this_lap
    current_holder_status = None
    for c, status in st.session_state.status_texto.items():
        if status == 'Bastão': current_holder_status = c; break

    next_holder = next((c for c in queue if c not in skipped and st.session_state.get(f'check_{c}')), None)
    print(f'Queue: {queue}, Skipped: {skipped}, Found next: {next_holder}, Current status holder: {current_holder_status}')

    if next_holder == current_holder_status:
        print(f'{next_holder} já tem bastão, sem mudanças.'); return False

    changed = False
    # Clear old holder's status
    if current_holder_status and current_holder_status != next_holder:
        print(f'Limpando bastão de {current_holder_status}')
        duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
        log_status_change(current_holder_status, 'Bastão', '', duration)
        st.session_state.status_texto[current_holder_status] = ''
        changed = True

    # Assign to new holder
    if next_holder:
        print(f'Atribuindo bastão para {next_holder}')
        old_status = st.session_state.status_texto.get(next_holder, '')
        duration = datetime.now() - st.session_state.current_status_starts.get(next_holder, datetime.now())
        log_status_change(next_holder, old_status, 'Bastão', duration)
        st.session_state.status_texto[next_holder] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        # Only play sound/notify if it wasn't the same person regaining baton after reset/state inconsistency
        if current_holder_status != next_holder:
             st.session_state.play_sound = True
             send_chat_notification_internal(next_holder, 'Bastão')
        changed = True
    elif not next_holder and current_holder_status: # No one eligible, clear baton
         print(f'Ninguém elegível, limpando bastão de {current_holder_status}')
         duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
         log_status_change(current_holder_status, 'Bastão', '', duration)
         st.session_state.status_texto[current_holder_status] = ''
         st.session_state.bastao_start_time = None
         changed = True
    elif not next_holder and not current_holder_status: # No one eligible and no one has it
         if st.session_state.bastao_start_time is not None: changed = True # Ensure start time is cleared
         st.session_state.bastao_start_time = None


    if changed: print('Estado do bastão mudou.'); save_state()
    return changed

# ============================================
# 3. FUNÇÕES DE CALLBACK (FORA)
# ============================================

def update_queue(consultor):
    print(f'UPDATE QUEUE: {consultor}')
    st.session_state['gif_warning'] = False
    st.session_state['rotation_gif_start_time'] = None
    checkbox_key = f'check_{consultor}'
    # State reflects the NEW value of the checkbox AFTER the click
    is_checked = st.session_state.get(checkbox_key, False)
    # Get status BEFORE the change for logging
    old_status_text = st.session_state.status_texto.get(consultor, '')
    was_holder_before = consultor == (st.session_state.bastao_queue[0] if st.session_state.bastao_queue else None)


    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())

    if is_checked: # BECOMING available
        new_status_log = '' # Log as becoming available
        st.session_state.status_texto[consultor] = '' # Clear any specific status like Atividade
        if consultor not in st.session_state.master_order: st.session_state.master_order.append(consultor)
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
        st.session_state.skipped_this_lap.discard(consultor)
        # Don't add to completed_this_lap here
    else: # BECOMING unavailable
        new_status_log = 'Indisponível'
        st.session_state.status_texto[consultor] = '' # Clear specific status like Atividade too
        if consultor in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(consultor)
        st.session_state.skipped_this_lap.discard(consultor)
        st.session_state.completed_this_lap.discard(consultor)

    log_status_change(consultor, old_status_text, new_status_log, duration)

    print(f' Fila Ativa: {st.session_state.bastao_queue}')
    print(f' Master Order: {st.session_state.master_order}')
    print(f' Skipped: {st.session_state.skipped_this_lap}')
    print(f' Completed: {st.session_state.completed_this_lap}')

    reset_triggered = check_cycle_reset()
    baton_changed = check_and_assume_baton() # Check baton after queue potentially changed

    # Always save state after manual checkbox interaction
    save_state()
    st.rerun()


def rotate_bastao():
    print('ROTATE BASTAO')
    selected = st.session_state.get('consultor_selectbox')
    st.session_state['gif_warning'] = False
    st.session_state['rotation_gif_start_time'] = None

    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    queue = st.session_state.bastao_queue
    if not queue or selected != queue[0]: st.session_state['gif_warning'] = True; st.rerun(); return

    holder = queue.pop(0)
    queue.append(holder)
    st.session_state.bastao_queue = queue
    duration = datetime.now() - st.session_state.bastao_start_time if st.session_state.bastao_start_time else timedelta(0)
    log_status_change(holder, 'Bastão', '', duration)
    st.session_state.status_texto[holder] = ''
    st.session_state.bastao_counts[holder] = st.session_state.bastao_counts.get(holder, 0) + 1
    st.session_state.play_sound = True
    st.session_state.rotation_gif_start_time = datetime.now()
    st.session_state.completed_this_lap.add(holder) # Mark as completed

    print(f' Fila Ativa: {st.session_state.bastao_queue}')
    print(f' Master Order: {st.session_state.master_order}')
    print(f' Skipped: {st.session_state.skipped_this_lap}')
    print(f' Completed: {st.session_state.completed_this_lap}')

    reset_triggered = check_cycle_reset()
    check_and_assume_baton() # Assign to the new queue[0]

    # State is saved within check_and_assume_baton if needed
    st.rerun()

def skip_turn():
    print('SKIP TURN')
    selected = st.session_state.get('consultor_selectbox')
    st.session_state['gif_warning'] = False
    st.session_state['rotation_gif_start_time'] = None

    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    queue = st.session_state.bastao_queue
    if selected not in queue: st.warning(f'{selected} não está na fila ativa.'); return

    is_holder = selected == queue[0]
    queue.remove(selected)
    st.session_state.bastao_queue = queue
    old_status = 'Bastão' if is_holder else st.session_state.status_texto.get(selected, '') or 'Disponível'
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, old_status, 'Pulou Turno', duration)
    st.session_state.status_texto[selected] = '' # Clear specific status
    st.session_state.skipped_this_lap.add(selected)
    # DO NOT add to completed_this_lap

    print(f' Fila Ativa: {st.session_state.bastao_queue}')
    print(f' Master Order: {st.session_state.master_order}')
    print(f' Skipped: {st.session_state.skipped_this_lap}')
    print(f' Completed: {st.session_state.completed_this_lap}')

    reset_triggered = check_cycle_reset()
    baton_changed = False
    if is_holder or reset_triggered: # If holder skipped, or cycle reset, re-check baton
        baton_changed = check_and_assume_baton()

    # Save state unless baton change already saved it
    if not baton_changed: save_state()
    st.rerun()

def update_status(status_text, change_to_available):
    # This function implies marking as UNAVAILABLE with a specific status
    print(f'UPDATE STATUS: {status_text}')
    selected = st.session_state.get('consultor_selectbox')
    st.session_state['gif_warning'] = False
    st.session_state['rotation_gif_start_time'] = None

    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    if selected not in st.session_state.status_texto: return # Should not happen

    st.session_state[f'check_{selected}'] = False # Mark unavailable
    is_holder = selected == (st.session_state.bastao_queue[0] if st.session_state.bastao_queue else None)
    old_status = st.session_state.status_texto.get(selected, '') or ('Bastão' if is_holder else 'Disponível')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, old_status, status_text, duration)
    st.session_state.status_texto[selected] = status_text # Set the specific status (Atividade, etc.)

    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.skipped_this_lap.discard(selected)
    st.session_state.completed_this_lap.discard(selected)

    if status_text in STATUS_SAIDA_PRIORIDADE:
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)

    print(f' Fila Ativa: {st.session_state.bastao_queue}')
    print(f' Master Order: {st.session_state.master_order}')
    print(f' Skipped: {st.session_state.skipped_this_lap}')
    print(f' Completed: {st.session_state.completed_this_lap}')

    reset_triggered = check_cycle_reset()
    baton_changed = False
    if is_holder or reset_triggered: # If holder left, or cycle reset, re-check baton
        baton_changed = check_and_assume_baton()

    # Save state unless baton change already saved it
    if not baton_changed: save_state()
    st.rerun()

def manual_rerun():
    print('MANUAL RERUN')
    st.session_state['gif_warning'] = False
    st.session_state['rotation_gif_start_time'] = None
    # No state changes needed, just refresh UI
    st.rerun()

# ============================================
# 4. GERAÇÃO DO CÓDIGO DE EXECUÇÃO (STRING)
# ============================================

def generate_execution_code():
    execution_lines = [
        "# --- INÍCIO DA EXECUÇÃO ---",
        'st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")',
        "st.markdown('<style>div.stAlert { display: none !important; }</style>', unsafe_allow_html=True)",
        "init_session_state() # Load state AFTER set_page_config",
        "",
        "st.title(f'Controle Bastão Cesupe {BASTAO_EMOJI}')",
        'st.markdown("<hr style=\\"border: 1px solid #E75480;\\">", unsafe_allow_html=True)',
        "",
        "# --- Auto Refresh & Timed Elements ---",
        "gif_start_time = st.session_state.get('rotation_gif_start_time')",
        "show_gif = False",
        "refresh_interval = 30000",
        "if gif_start_time:",
        "    try:",
        "        elapsed = (datetime.now() - gif_start_time).total_seconds()",
        "        if elapsed < 20:",
        "            show_gif = True",
        "            refresh_interval = 5000",
        "        else:",
        "            st.session_state.rotation_gif_start_time = None", # Clear implicitly on next run
        "    except TypeError: st.session_state.rotation_gif_start_time = None",
        "st_autorefresh(interval=refresh_interval, key='auto_rerun_key')",
        "",
        "if st.session_state.get('play_sound', False):",
        "    st.components.v1.html(play_sound_html(), height=0, width=0)",
        "    st.session_state.play_sound = False",
        "",
        "if show_gif:",
        "    st.image(GIF_URL_ROTATION, width=200, caption='BASTÃO GIRADO!')",
        "if st.session_state.get('gif_warning', False):",
        "    st.error('🚫 Ação inválida! Verifique as regras.')",
        "    st.image(GIF_URL_WARNING, width=150)",
        "",
        "# --- Garantir Assunção Inicial ou Pós-Reset ---",
        "current_holder_from_status = None",
        "for status in st.session_state.status_texto.values():",
        "    if status == 'Bastão': current_holder_from_status = True; break",
        "if not current_holder_from_status and st.session_state.bastao_queue:",
        "    print('!!! FORÇANDO CHECK ASSUME BATON NO RENDER !!!')",
        "    if check_and_assume_baton():",
        "        print('--> Baton foi reassumido, rerunning...')",
        "        st.rerun() # Rerun immediately if baton assignment changed",
        "",
        "# --- Layout Principal ---",
        'col_principal, col_disponibilidade = st.columns([1.5, 1])',
        "active_queue = st.session_state.bastao_queue",
        "master = st.session_state.master_order",
        "skipped = st.session_state.skipped_this_lap",
        "responsavel = active_queue[0] if active_queue else ''",
        "proximo_responsavel = active_queue[1] if len(active_queue) > 1 else ''",
        "fila_restante = active_queue[2:]",
        "",
        "with col_principal:",
        '    st.header("Responsável pelo Bastão")',
        "    col_gif_icon, col_time = st.columns([0.25, 0.75])",
        "    col_gif_icon.image('https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExYjlqeWg3bXpuZ2ltMXdsNXJ6OW13eWF5aXlqYnc1NGNjamFjczlpOSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/xAFPuHVjmsBmU/giphy.gif', width=50)",
        "    bastao_duration = timedelta()",
        "    if responsavel and st.session_state.bastao_start_time:",
        "        try: bastao_duration = datetime.now() - st.session_state.bastao_start_time",
        "        except: pass",
        "    col_time.markdown(f'#### 🕒 Tempo: **{format_time_duration(bastao_duration)}**')",
        "    if responsavel:",
        "        st.markdown(f'<span style=\"background-color: #E75480; color: white; padding: 5px 10px; border-radius: 5px; font-size: 2em; font-weight: bold;\">🔥 {responsavel}</span>', unsafe_allow_html=True)",
        "    else: st.markdown('## (Ninguém na fila ativa)')",
        '    st.markdown("###")',
        '    st.header("Próximos da Fila Ativa")',
        "    if proximo_responsavel:",
        "        st.markdown(f'### 1º: **{proximo_responsavel}**')",
        "        if fila_restante:",
        "            st.markdown(f'#### 2º em diante: {', '.join(fila_restante)}')",
        "    else:",
        "        if responsavel: st.markdown('*Apenas o responsável na fila ativa.*')",
        "        else: st.markdown('*Fila ativa vazia.*')",
        "    if skipped:",
        "        st.markdown(f'<br><span style=\"color:orange;\">🚫 Pulou nesta volta:</span> {', '.join(sorted(list(skipped)))}', unsafe_allow_html=True)",
        '    st.markdown("###")',
        '    st.header("**Consultor**")',
        "    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')",
        '    st.markdown("#### ")',
        '    st.markdown("**Ações:**")',
        '    col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)',
        "    col_b1.button('🎯 Bastão', on_click=rotate_bastao, use_container_width=True, help='Passa o bastão para o próximo da fila ativa. Apenas o responsável atual pode fazer isso.')",
        "    col_b2.button('⏭️ Pular', on_click=skip_turn, use_container_width=True, help='Sai da fila ativa *nesta volta*. Volta automaticamente no próximo ciclo. Qualquer um na fila ativa pode pular.')",
        "    col_b3.button('✏️ Atividade', on_click=update_status, args=('Atividade', False,), use_container_width=True)",
        "    col_b4.button('🍽️ Almoço', on_click=update_status, args=('Almoço', False,), use_container_width=True)",
        "    col_b5.button('🚶 Saída', on_click=update_status, args=('Saída Temporária', False,), use_container_width=True)",
        '    st.markdown("####")',
        "    st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)",
        '    st.markdown("---")',
        "",
        "with col_disponibilidade:",
        "    st.header('Status dos Consultores')",
        "    st.markdown('Marque/Desmarque para entrar/sair da fila ativa.')",
        "    list_na_fila_ui = []",
        "    list_atividade_ui = []",
        "    list_almoco_ui = []",
        "    list_saida_ui = []",
        "    list_indisponivel_ui = []",
        "    for nome in CONSULTORES:",
        "        is_checked = st.session_state.get(f'check_{nome}', False)",
        "        status = st.session_state.status_texto.get(nome, '')",
        "        if is_checked: list_na_fila_ui.append(nome)",
        "        elif status == 'Atividade': list_atividade_ui.append(nome)",
        "        elif status == 'Almoço': list_almoco_ui.append(nome)",
        "        elif status == 'Saída Temporária': list_saida_ui.append(nome)",
        "        else: list_indisponivel_ui.append(nome)",
        "    st.subheader(f'✅ Na Fila ({len(list_na_fila_ui)})')",
        "    nomes_renderizados = 0",
        "    if master:", # Iterate based on master order for consistency
        "        for nome in master:",
        "            if nome in list_na_fila_ui:", # Only render if checkbox is checked
        "                nomes_renderizados += 1",
        "                col_nome, col_check = st.columns([0.8, 0.2])",
        "                checkbox_key = f'check_{nome}'",
        "                # Checkbox is never disabled visually here",
        "                col_check.checkbox(' ', key=checkbox_key, on_change=update_queue, args=(nome,), label_visibility='collapsed')",
        "                if nome == responsavel:",
        "                    display = f'<span style=\"background-color: #E75480; color: white; padding: 2px 6px; border-radius: 5px; font-weight: bold;\">🔥 {nome}</span>'",
        "                elif nome in skipped:",
        "                    display = f'**{nome}** :orange-background[Pulou]'",
        "                elif nome in active_queue:",
        "                    display = f'**{nome}** :blue-background[Na Fila]'",
        "                else:", # Checked, in master, not skipped, but not in active queue? Should be rare/transient
        "                    display = f'**{nome}** :grey-background[Disponível]'",
        "                col_nome.markdown(display, unsafe_allow_html=True)",
        "    # Handle consultants checked ON but not yet in master order (new entries)",
        "    newly_available = [nome for nome in list_na_fila_ui if nome not in master]",
        "    for nome in newly_available:",
        "        nomes_renderizados += 1",
        "        col_nome, col_check = st.columns([0.8, 0.2])",
        "        checkbox_key = f'check_{nome}'",
        "        col_check.checkbox(' ', key=checkbox_key, on_change=update_queue, args=(nome,), label_visibility='collapsed')",
        "        # Should appear at the end of the active queue conceptually",
        "        display = f'**{nome}** :blue-background[Na Fila]' ",
        "        col_nome.markdown(display, unsafe_allow_html=True)",
        "",
        "    if nomes_renderizados == 0: st.markdown('_Ninguém disponível na fila._')",
        "    st.markdown('---')",
        "    def render_section(title, icon, names, tag_color):",
        "        st.subheader(f'{icon} {title} ({len(names)})')",
        "        if not names: st.markdown(f'_Ninguém em {title.lower()}._')",
        "        else:",
        "            for nome in sorted(names):",
        "                col_nome, col_check = st.columns([0.8, 0.2])",
        "                key = f'check_{nome}'",
        "                col_check.checkbox(' ', key=key, on_change=update_queue, args=(nome,), label_visibility='collapsed')",
        "                col_nome.markdown(f'**{nome}** :{tag_color}-background[{title}]', unsafe_allow_html=True)",
        "        st.markdown('---')",
        "    render_section('Atividade', '✏️', list_atividade_ui, 'yellow')",
        "    render_section('Almoço', '🍽️', list_almoco_ui, 'blue')",
        "    render_section('Saída', '🚶', list_saida_ui, 'red')",
        "    render_section('Indisponível', '❌', list_indisponivel_ui, 'grey')",
        "    # Daily report check",
        "    current_hour = datetime.now().hour",
        "    today = datetime.now().date()",
        "    last_run = st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()",
        "    if current_hour >= 20 and today > last_run:",
        "        send_daily_report()",
        "",
        "print('--- FIM DO RENDER ---')" # Debug print
    ]
    return "\n".join(execution_lines)


# ============================================
# 5. EXECUÇÃO FINAL
# ============================================
app_code_to_exec = generate_execution_code()
exec(app_code_to_exec, globals()) # Pass globals() to ensure functions are found
