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
    # ... (Implementation as before) ...
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
        print(f'*** Estado Salvo ***')
    except Exception as e: print(f'Erro ao salvar estado: {e}')


def load_state():
    # ... (Implementation as before) ...
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
                 elif isinstance(ts, datetime): temp_starts[c] = ts
                 else: temp_starts[c] = datetime.now()
             data['current_status_starts'] = temp_starts
        else: data['current_status_starts'] = {}
        if 'master_order' not in data or not isinstance(data['master_order'], list): data['master_order'] = []
        data.setdefault('status_texto', {})
        data.setdefault('bastao_queue', [])
        data.setdefault('bastao_counts', {})
        data.setdefault('priority_return_queue', [])
        return data
    except Exception as e: print(f'Erro ao carregar estado: {e}. Resetando.'); return {}


def send_chat_notification_internal(c, s): pass
def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'
def load_logs(): return []
def save_logs(l): pass

def log_status_change(consultor, old_status, new_status, duration):
    # ... (Implementation as before) ...
    print(f'LOG: {consultor} de "{old_status or '-'}" para "{new_status or '-'}" após {duration}')
    if not isinstance(duration, timedelta): duration = timedelta(0)
    st.session_state.current_status_starts[consultor] = datetime.now()


def format_time_duration(duration):
    # ... (Implementation as before) ...
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'


def send_daily_report(): pass

def init_session_state():
    # ... (Implementation as before) ...
    persisted_state = load_state()
    defaults = {
        'status_texto': {nome: '' for nome in CONSULTORES}, 'bastao_queue': [],
        'bastao_start_time': None, 'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min, 'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [], 'rotation_gif_start_time': None,
        'master_order': [],
        'completed_this_cycle': set(), 'initial_cycle_members': set()
    }
    for key, default in defaults.items():
        if key in ['completed_this_cycle', 'initial_cycle_members']:
             st.session_state[key] = default
        else:
             st.session_state.setdefault(key, persisted_state.get(key, default))
        if key in ['completed_this_cycle', 'initial_cycle_members'] and not isinstance(st.session_state[key], set):
             st.session_state[key] = set() # Ensure it's a set

    loaded_starts = persisted_state.get('current_status_starts', {})
    for nome in CONSULTORES:
        st.session_state.current_status_starts.setdefault(nome, loaded_starts.get(nome, datetime.now()))

    st.session_state.master_order = [c for c in st.session_state.master_order if c in CONSULTORES]
    st.session_state.bastao_queue = [c for c in st.session_state.bastao_queue if c in CONSULTORES]

    active_people = set(st.session_state.bastao_queue) | st.session_state.completed_this_cycle # Use completed instead of skipped
    for nome in CONSULTORES:
        is_active = nome in active_people or bool(st.session_state.status_texto.get(nome))
        st.session_state.setdefault(f'check_{nome}', is_active)

    # Initial cycle definition/check
    if not st.session_state.initial_cycle_members:
         print('!!! Iniciando ciclo na carga !!!')
         st.session_state.bastao_queue = [c for c in st.session_state.master_order if st.session_state.get(f'check_{c}')]
         for c in CONSULTORES:
              if st.session_state.get(f'check_{c}') and c not in st.session_state.bastao_queue:
                  st.session_state.bastao_queue.append(c)
                  if c not in st.session_state.master_order: st.session_state.master_order.append(c)
         st.session_state.initial_cycle_members = set(st.session_state.bastao_queue)
         st.session_state.completed_this_cycle = set()
         print(f' Fila Ativa Pós-Init-Reset: {st.session_state.bastao_queue}')
         print(f' Initial Members Pós-Init-Reset: {st.session_state.initial_cycle_members}')

    print('--- Estado Inicializado ---')
    print(f" Master: {st.session_state.master_order}, Fila: {st.session_state.bastao_queue}, Completed: {st.session_state.completed_this_cycle}, Initial: {st.session_state.initial_cycle_members}")


def check_cycle_reset():
    # ... (Implementation as before) ...
    initial_members = st.session_state.initial_cycle_members
    completed = st.session_state.completed_this_cycle
    initial_still_available = {c for c in initial_members if st.session_state.get(f'check_{c}')}
    print(f'CHECK RESET: Initial Available: {initial_still_available}, Completed: {completed}')
    if initial_still_available and initial_still_available.issubset(completed):
        print('--- RESETANDO CICLO ---')
        st.session_state.completed_this_cycle = set()
        st.session_state.bastao_queue = [c for c in st.session_state.master_order if st.session_state.get(f'check_{c}')]
        for c in CONSULTORES: # Add newly available not in master yet
             if st.session_state.get(f'check_{c}') and c not in st.session_state.bastao_queue:
                 st.session_state.bastao_queue.append(c)
                 if c not in st.session_state.master_order: st.session_state.master_order.append(c)
        st.session_state.initial_cycle_members = set(st.session_state.bastao_queue) # Reset initial members
        print(f'Nova Fila Pós-Reset: {st.session_state.bastao_queue}')
        print(f'Novos Initial Members: {st.session_state.initial_cycle_members}')
        return True
    return False

def check_and_assume_baton():
    # ... (Implementation as before) ...
    print('--- CHECK ASSUME BATON ---')
    queue = st.session_state.bastao_queue
    completed = st.session_state.completed_this_cycle
    current_holder_status = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    next_holder = next((c for c in queue if c not in completed and st.session_state.get(f'check_{c}')), None)
    print(f'Queue: {queue}, Completed: {completed}, Next: {next_holder}, Current: {current_holder_status}')
    if next_holder == current_holder_status: print('Sem mudanças.'); return False
    changed = False
    if current_holder_status and current_holder_status != next_holder:
        print(f'Limpando bastão de {current_holder_status}')
        duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
        log_status_change(current_holder_status, 'Bastão', '', duration)
        st.session_state.status_texto[current_holder_status] = ''
        changed = True
    if next_holder:
        print(f'Atribuindo bastão para {next_holder}')
        old_status = st.session_state.status_texto.get(next_holder, '')
        duration = datetime.now() - st.session_state.current_status_starts.get(next_holder, datetime.now())
        log_status_change(next_holder, old_status, 'Bastão', duration)
        st.session_state.status_texto[next_holder] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        if current_holder_status != next_holder: st.session_state.play_sound = True
        changed = True
    elif not next_holder:
         if current_holder_status:
              print(f'Ninguém elegível, limpando bastão de {current_holder_status}')
              duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
              log_status_change(current_holder_status, 'Bastão', '', duration)
              st.session_state.status_texto[current_holder_status] = ''
              changed = True
         if st.session_state.bastao_start_time is not None: changed = True
         st.session_state.bastao_start_time = None
    if changed: save_state()
    return changed

# ============================================
# 3. FUNÇÕES DE CALLBACK GLOBAIS
# ============================================

def update_queue(consultor):
    # ... (Implementation as before) ...
    print(f'UPDATE QUEUE: {consultor}')
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    is_checked = st.session_state.get(f'check_{consultor}') # New state after click
    old_status_text = st.session_state.status_texto.get(consultor, '')
    was_holder_before = consultor == next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())
    if is_checked: # BECOMING available
        new_status_log = ''
        st.session_state.status_texto[consultor] = ''
        if consultor not in st.session_state.master_order: st.session_state.master_order.append(consultor)
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
        # If cycle hasn't started OR this person was previously out and cycle resets, add to initial
        if not st.session_state.initial_cycle_members:
             st.session_state.initial_cycle_members.add(consultor)
        # Completed status is cleared on reset, don't discard here
    else: # BECOMING unavailable
        new_status_log = 'Indisponível'
        st.session_state.status_texto[consultor] = ''
        if consultor in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(consultor)
        st.session_state.completed_this_cycle.discard(consultor) # Remove from completion if they leave
        # No change to initial_cycle_members needed here

    log_status_change(consultor, old_status_text or ('Bastão' if was_holder_before else 'Indisponível' if not is_checked else 'Disponível'), new_status_log, duration)
    print(f'... Fila Ativa: {st.session_state.bastao_queue}, Master: {st.session_state.master_order}, Completed: {st.session_state.completed_this_cycle}, Initial: {st.session_state.initial_cycle_members}')
    reset = check_cycle_reset()
    baton = check_and_assume_baton()
    if not baton: save_state() # Save if baton didn't change (and save)
    st.rerun()

def finish_turn_action(): # Unified Pass/Skip
    # ... (Implementation as before) ...
    print('FINISH TURN ACTION')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione.'); return
    current_holder_status = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder_status: st.session_state.gif_warning = True; st.rerun(); return

    holder = selected
    st.session_state.completed_this_cycle.add(holder)
    if holder in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(holder) # Remove from active duty this cycle
    duration = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
    log_status_change(holder, 'Bastão', 'Turno Concluído', duration) # Logged as completed/skipped
    st.session_state.status_texto[holder] = '' # Clear status
    st.session_state.bastao_counts[holder] = st.session_state.bastao_counts.get(holder, 0) + 1
    st.session_state.play_sound = True
    st.session_state.rotation_gif_start_time = datetime.now()

    print(f'... Fila Ativa: {st.session_state.bastao_queue}, Master: {st.session_state.master_order}, Completed: {st.session_state.completed_this_cycle}, Initial: {st.session_state.initial_cycle_members}')
    reset = check_cycle_reset()
    check_and_assume_baton() # Assign next or handle reset
    # Save happens in check_and_assume
    st.rerun()

def update_status(status_text, change_to_available): # Mark unavailable + Status
    # ... (Implementation as before) ...
    print(f'UPDATE STATUS: {status_text}')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione.'); return

    st.session_state[f'check_{selected}'] = False # Mark unavailable
    was_holder = next((True for c, s in st.session_state.status_texto.items() if s == 'Bastão' and c == selected), False)
    old_status = st.session_state.status_texto.get(selected, '') or ('Bastão' if was_holder else 'Disponível')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, old_status, status_text, duration)
    st.session_state.status_texto[selected] = status_text # Set the specific status

    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.completed_this_cycle.discard(selected)
    # Don't remove from initial_cycle_members

    if status_text == 'Saída Temporária':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)

    print(f'... Fila Ativa: {st.session_state.bastao_queue}, Master: {st.session_state.master_order}, Completed: {st.session_state.completed_this_cycle}, Initial: {st.session_state.initial_cycle_members}')
    reset = check_cycle_reset()
    baton = False
    if was_holder or reset: # If holder left, or cycle reset, re-check baton
        baton = check_and_assume_baton()
    if not baton: save_state() # Save if baton didn't change
    st.rerun()

def manual_rerun():
    # ... (Implementation as before) ...
    print('MANUAL RERUN')
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
if show_gif: st.image(GIF_URL_ROTATION, width=200, caption='Turno Finalizado!')
if st.session_state.get('gif_warning', False):
    st.error('🚫 Ação inválida! Apenas o portador atual pode usar 🎯 Bastão ou ⏭️ Pular.'); st.image(GIF_URL_WARNING, width=150)

# --- Garantir Assunção Inicial/Pós-Reset ---
holder_exists = any(s == 'Bastão' for s in st.session_state.status_texto.values())
eligible_exists = any(c not in st.session_state.completed_this_cycle for c in st.session_state.bastao_queue)
if not holder_exists and st.session_state.bastao_queue and eligible_exists:
    print('!!! FORÇANDO CHECK ASSUME BATON NO RENDER !!!')
    if check_and_assume_baton():
        print('--> Baton foi reassumido, rerunning...')
        # Use st.experimental_rerun() for newer versions if st.rerun() causes issues here
        st.rerun() # Rerun immediately if baton assignment changed

# --- Layout ---
col_principal, col_disponibilidade = st.columns([1.5, 1])
active_queue = st.session_state.bastao_queue
master = st.session_state.master_order
completed = st.session_state.completed_this_cycle
responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
proximo = next((c for c in active_queue if c not in completed and st.session_state.get(f'check_{c}')), None)
proximo_index = active_queue.index(proximo) if proximo in active_queue else -1
restante = [c for i, c in enumerate(active_queue) if i > proximo_index and c not in completed and st.session_state.get(f'check_{c}')] if proximo_index != -1 else []

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
    st.header("Próximos da Fila (Elegíveis)")
    if proximo: st.markdown(f'### 1º: **{proximo}**')
    if restante: st.markdown(f'#### 2º em diante: {", ".join(restante)}')
    if not proximo:
        if responsavel: st.markdown('*Apenas o responsável na fila ativa.*')
        else: st.markdown('*Ninguém elegível na fila ativa.*')
    if completed: st.markdown(f'<br><span style="color:grey;">✔️ Turno Concluído/Pulou:</span> {", ".join(sorted(list(completed)))}', unsafe_allow_html=True)
    st.markdown("###")
    st.header("**Consultor**")
    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### "); st.markdown("**Ações:**")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.button('🎯 Bastão', on_click=finish_turn_action, use_container_width=True, help='Finaliza seu turno e passa para o próximo. Apenas o responsável atual.')
    c2.button('⏭️ Pular', on_click=finish_turn_action, use_container_width=True, help='Finaliza seu turno e passa para o próximo. Apenas o responsável atual.') # Same action
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
    master_ordered_fila = [c for c in master if c in ui_lists['fila']]
    newly_available = [c for c in ui_lists['fila'] if c not in master]
    combined_fila_render_order = master_ordered_fila + newly_available
    if not combined_fila_render_order: st.markdown('_Ninguém disponível._')
    else:
        for nome in combined_fila_render_order:
            col_nome, col_check = st.columns([0.8, 0.2])
            key = f'check_{nome}'
            col_check.checkbox(' ', key=key, on_click=update_queue, args=(nome,), label_visibility='collapsed') # Use onClick
            if nome == responsavel:
                display = f'<span style="background-color: #E75480; color: white; padding: 2px 6px; border-radius: 5px; font-weight: bold;">🔥 {nome}</span>'
            elif nome in completed:
                display = f'**{nome}** :grey-background[✔️ Concluído]'
            elif nome in active_queue:
                 display = f'**{nome}** :blue-background[Aguardando]'
            else: display = f'**{nome}** :green-background[Disponível]' # Available but not in active queue yet (e.g. just checked)
            col_nome.markdown(display, unsafe_allow_html=True)
    st.markdown('---')

    def render_section(title, icon, names, tag_color):
        st.subheader(f'{icon} {title} ({len(names)})')
        if not names: st.markdown(f'_Ninguém em {title.lower()}._')
        else:
            for nome in sorted(names):
                col_nome, col_check = st.columns([0.8, 0.2])
                key = f'check_{nome}'
                col_check.checkbox(' ', key=key, on_click=update_queue, args=(nome,), label_visibility='collapsed') # Use onClick
                col_nome.markdown(f'**{nome}** :{tag_color}-background[{title}]', unsafe_allow_html=True)
        st.markdown('---')
    render_section('Atividade', '✏️', ui_lists['atividade'], 'yellow')
    render_section('Almoço', '🍽️', ui_lists['almoco'], 'blue')
    render_section('Saída', '🚶', ui_lists['saida'], 'red')
    render_section('Indisponível', '❌', ui_lists['indisponivel'], 'grey')

    if datetime.now().hour >= 20 and datetime.now().date() > (st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()):
        send_daily_report()

print('--- FIM DO SCRIPT ---') # Debug print
