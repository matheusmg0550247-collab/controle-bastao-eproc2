# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, date
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import traceback # Para depuração de erros

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
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    """Inicializa e retorna o dicionário de estado GLOBAL compartilhado."""
    print("--- Inicializando o Cache de Estado GLOBAL (Executa Apenas 1x) ---")
    return {
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES}, 
        'report_last_run_date': datetime.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'rotation_gif_start_time': None,
        'lunch_warning_info': None, 
        'status_transitions': [], # <-- MODIFICADO: Lista para armazenar transições
    }

# --- Constantes ---
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = ""
BASTAO_EMOJI = "🌸"
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
STATUS_SAIDA_PRIORIDADE = ['Saída Temporária']
# Lista expandida para incluir estados "implícitos" para o relatório
ALL_STATUSES_FOR_REPORT = ['Bastão', '', 'Atividade', 'Almoço', 'Saída Temporária', 'Ausente', 'Sessão', 'Indisponível'] 
STATUSES_DE_SAIDA = ['Atividade', 'Almoço', 'Saída Temporária', 'Ausente', 'Sessão'] 
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_LUNCH_WARNING = 'https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGZlbHN1azB3b2drdTI1eG10cDEzeWpmcmtwenZxNTV0bnc2OWgzZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/bNlqpmBJRDMpxulfFB/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/refs/heads/main/doorbell-223669.mp3"

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

def date_serializer(obj):
    if isinstance(obj, (datetime, date)): 
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        # Serializa timedelta como segundos totais para consistência
        return obj.total_seconds() 
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
        global_data['lunch_warning_info'] = st.session_state.get('lunch_warning_info') 
        global_data['status_transitions'] = st.session_state.status_transitions.copy() # <-- MODIFICADO: Salva transições

        print(f'*** Estado GLOBAL Salvo (Cache de Recurso) ***')
    except Exception as e: 
        print(f'Erro ao salvar estado GLOBAL: {e}')
        # Adiciona traceback para mais detalhes em caso de erro
        # traceback.print_exc() 

# --- FUNÇÃO `load_state` (GLOBAL) ---
def load_state():
    """Carrega o estado GLOBAL (Cache) e retorna para a sessão LOCAL."""
    global_data = get_global_state_cache()
    loaded_data = {k: v for k, v in global_data.items()}
    return loaded_data
# --- FIM DAS MUDANÇAS DE PERSISTÊNCIA ---

def send_chat_notification_internal(consultor, status):
    # (Código mantido)
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
def load_logs(): return [] # Mantido, mas não usado diretamente pelo relatório
def save_logs(l): pass # Mantido, mas não usado diretamente pelo relatório

# <-- MODIFICADO: Adiciona a transição à lista global -->
def log_status_change(consultor, old_status, new_status, duration):
    """Registra a mudança de status e a adiciona à lista de transições."""
    print(f'LOG: {consultor} de "{old_status or "Inicio"}" para "{new_status or "Disponível"}" após {duration}')
    
    # Garante que a duração seja timedelta
    if not isinstance(duration, timedelta): 
        duration = timedelta(0)
        
    # Garante que a lista de transições exista na sessão
    if 'status_transitions' not in st.session_state:
        st.session_state.status_transitions = []

    # Cria a entrada de log/transição
    transition_entry = {
        'timestamp': datetime.now(),
        'consultor': consultor,
        'previous_status': old_status if old_status is not None else 'Inicio', # Status anterior ('Inicio' se for o primeiro)
        'current_status': new_status if new_status is not None else 'Disponível', # Status atual ('Disponível' se limpou)
        'duration': duration.total_seconds() # Armazena como segundos para facilitar
    }
    
    # Adiciona à lista local
    st.session_state.status_transitions.append(transition_entry)
    
    # Atualiza o tempo de início do novo status
    st.session_state.current_status_starts[consultor] = datetime.now()
    
    # Salva o estado global imediatamente para persistir a transição
    save_state() 

def format_time_duration(duration_obj):
    """Formata um objeto timedelta ou um número de segundos."""
    if isinstance(duration_obj, timedelta):
        s = int(duration_obj.total_seconds())
    elif isinstance(duration_obj, (int, float)):
        s = int(duration_obj)
    else:
        return '--:--:--'
        
    if s < 0: s = 0 # Evita tempos negativos
    h, remainder = divmod(s, 3600)
    m, s = divmod(remainder, 60)
    return f'{h:02}:{m:02}:{s:02}'

# <-- MODIFICADO: Processa transições e contagens para o relatório -->
def send_daily_report():
    print("Tentando enviar backup diário...")
    today = date.today()
    today_str = today.isoformat()

    # Pega dados do estado da sessão
    bastao_counts = st.session_state.get('bastao_counts', {}).copy()
    transitions = st.session_state.get('status_transitions', []).copy()

    if not GOOGLE_CHAT_WEBHOOK_BACKUP:
        print("Backup não enviado. Webhook não configurado.")
        st.session_state['report_last_run_date'] = datetime.now()
        # Não precisa salvar estado aqui
        return

    # Filtra transições de hoje
    today_transitions = [
        t for t in transitions 
        if isinstance(t.get('timestamp'), datetime) and t['timestamp'].date() == today
    ]

    # Calcula durações totais por status
    total_durations = {consultor: {status: 0.0 for status in ALL_STATUSES_FOR_REPORT} for consultor in CONSULTORES}
    
    if not today_transitions:
        print("Nenhuma transição registrada hoje para calcular durações.")
    else:
        for t in today_transitions:
            consultor = t.get('consultor')
            prev_status = t.get('previous_status')
            duration_seconds = t.get('duration', 0.0)
            
            # Mapeia status vazio ('') para 'Disponível' para clareza no relatório
            report_status = prev_status if prev_status != '' else 'Disponível' 
            
            if consultor in total_durations and report_status in total_durations[consultor]:
                total_durations[consultor][report_status] += duration_seconds
            else:
                 print(f"Aviso: Consultor '{consultor}' ou status '{report_status}' não encontrado na inicialização de durações.")


    # Formata o relatório
    report_text = f"📊 **Backup Diário - {today_str}**\n\n"

    # Seção Contagem de Bastão
    report_text += "**Contagem de Bastão Recebido:**\n"
    if not bastao_counts or all(count == 0 for count in bastao_counts.values()):
        report_text += "_Nenhuma passagem registrada._\n"
    else:
        sorted_counts = sorted(bastao_counts.items())
        for consultor, count in sorted_counts:
            if count > 0:
                 report_text += f"- {consultor}: {count} vez{'es' if count > 1 else ''}\n"
    report_text += "\n"

    # Seção Duração nos Status
    report_text += "**Tempo Total Aproximado por Status (HH:MM:SS):**\n"
    if not today_transitions:
         report_text += "_Nenhuma atividade registrada para calcular durações._\n"
    else:
        for consultor in CONSULTORES:
            consultor_report = f"- **{consultor}:** "
            parts = []
            for status in ALL_STATUSES_FOR_REPORT:
                 # Renomeia '' para 'Disponível' no relatório
                 display_status = status if status != '' else 'Disponível'
                 if display_status == 'Inicio': continue # Ignora estado inicial
                 
                 duration_seconds = total_durations[consultor].get(display_status, 0.0)
                 # Apenas mostra status onde o tempo foi > 0
                 if duration_seconds > 0:
                     parts.append(f"{display_status}: {format_time_duration(duration_seconds)}")
            
            if parts: # Apenas adiciona linha se houve alguma atividade
                 report_text += consultor_report + ", ".join(parts) + "\n"
            # else: # Opcional: Linha para quem não teve atividade
            #      report_text += f"- **{consultor}:** _Sem atividade registrada._\n"


    chat_message = {'text': report_text}
    print(f"Enviando backup para: {GOOGLE_CHAT_WEBHOOK_BACKUP}")
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_BACKUP, json=chat_message)
        response.raise_for_status()
        st.session_state['report_last_run_date'] = datetime.now()
        print("Backup diário enviado com sucesso.")
        
        # LIMPA os dados para o próximo dia
        st.session_state.bastao_counts = {nome: 0 for nome in CONSULTORES}
        st.session_state.status_transitions = []
        save_state() # Salva o estado limpo
        
    except requests.exceptions.RequestException as e:
        print(f'Erro ao enviar backup diário: {e}')
        if e.response is not None:
            print(f'Status: {e.response.status_code}, Resposta: {e.response.text}')
            
    except Exception as e_general: # Captura outros erros potenciais
         print(f"Erro inesperado ao processar ou enviar relatório: {e_general}")
         # traceback.print_exc() # Descomente para depuração


def init_session_state():
    """Inicializa/sincroniza o st.session_state com o estado GLOBAL do cache."""
    persisted_state = load_state()
    
    defaults = {
        'bastao_start_time': None, 
        'report_last_run_date': datetime.min, 
        'rotation_gif_start_time': None,
        'play_sound': False, 
        'gif_warning': False, 
        'lunch_warning_info': None,
        # 'just_received_baton' foi removido, não é mais necessário
    }

    # Sincroniza as variáveis simples
    for key, default in defaults.items():
        if key in ['play_sound', 'gif_warning']: # Mantém flags locais
            st.session_state.setdefault(key, default)
        else: # Carrega do global
            st.session_state[key] = persisted_state.get(key, default)

    # Sincroniza as coleções de estado
    st.session_state['bastao_queue'] = persisted_state.get('bastao_queue', []).copy()
    st.session_state['priority_return_queue'] = persisted_state.get('priority_return_queue', []).copy()
    st.session_state['bastao_counts'] = persisted_state.get('bastao_counts', {}).copy()
    st.session_state['skip_flags'] = persisted_state.get('skip_flags', {}).copy()
    st.session_state['status_texto'] = persisted_state.get('status_texto', {}).copy()
    st.session_state['current_status_starts'] = persisted_state.get('current_status_starts', {}).copy()
    st.session_state['status_transitions'] = persisted_state.get('status_transitions', []).copy() # <-- Carrega transições

    # Garante consultores e sincroniza checkboxes
    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, 0)
        st.session_state.skip_flags.setdefault(nome, False)
        
        current_status = st.session_state.status_texto.get(nome, 'Indisponível') 
        st.session_state.status_texto.setdefault(nome, current_status)
        
        is_available = (current_status == 'Bastão' or current_status == '') and nome not in st.session_state.priority_return_queue
        st.session_state[f'check_{nome}'] = is_available
        
        if nome not in st.session_state.current_status_starts:
                st.session_state.current_status_starts[nome] = datetime.now()

    checked_on = {c for c in CONSULTORES if st.session_state.get(f'check_{c}')}
    if not st.session_state.bastao_queue and checked_on:
        print('!!! Fila vazia na carga, reconstruindo !!!')
        st.session_state.bastao_queue = sorted(list(checked_on))

    check_and_assume_baton()
    print('--- Estado Sincronizado (GLOBAL -> LOCAL) ---')


def update_queue(consultor):
    # (Código mantido, sem st.rerun())
    print(f'CALLBACK UPDATE QUEUE: {consultor}')
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    
    is_checked = st.session_state.get(f'check_{consultor}') 
    old_status_text = st.session_state.status_texto.get(consultor, '')
    was_holder_before = consultor == next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())

    if is_checked: 
        log_status_change(consultor, old_status_text or 'Indisponível', '', duration) # <-- Chama log_status_change
        st.session_state.status_texto[consultor] = '' 
        if consultor not in st.session_state.bastao_queue:
            st.session_state.bastao_queue.append(consultor) 
            print(f'Adicionado {consultor} ao fim da fila.')
        st.session_state.skip_flags[consultor] = False 
        if consultor in st.session_state.priority_return_queue:
            st.session_state.priority_return_queue.remove(consultor)
            
    else: 
        if old_status_text not in STATUSES_DE_SAIDA and old_status_text != 'Bastão':
            log_old_status = old_status_text or ('Bastão' if was_holder_before else 'Disponível')
            log_status_change(consultor, log_old_status , 'Indisponível', duration) # <-- Chama log_status_change
            st.session_state.status_texto[consultor] = 'Indisponível' 
        else: # Se já estava em Saída ou Bastão, loga a transição para 'Indisponível' (desmarcado manualmente)
             log_status_change(consultor, old_status_text , 'Indisponível', duration) # <-- Chama log_status_change
             st.session_state.status_texto[consultor] = 'Indisponível' 

        if consultor in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(consultor)
            print(f'Removido {consultor} da fila.')
        st.session_state.skip_flags.pop(consultor, None) 
        
    baton_changed = check_and_assume_baton() # Pode tocar som aqui dentro
    if not baton_changed:
        # Se o bastão não mudou, mas o estado sim, precisamos salvar
        save_state()

def rotate_bastao(): 
    # (Código mantido, toca som diretamente)
    print('CALLBACK ROTATE BASTAO (PASSAR)')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 

    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder:
        st.session_state.gif_warning = True
        return 

    current_index = -1
    try: current_index = queue.index(current_holder)
    except ValueError:
        st.warning(f'Erro interno: Portador {current_holder} não encontrado na fila. Tentando corrigir.')
        if check_and_assume_baton(): pass 
        return

    reset_triggered = False
    first_eligible_index_overall = find_next_holder_index(-1, queue, skips) 
    potential_next_index = find_next_holder_index(current_index, queue, skips)

    if potential_next_index != -1 and first_eligible_index_overall != -1:
        first_eligible_holder_overall = queue[first_eligible_index_overall]
        potential_next_holder = queue[potential_next_index]

        if potential_next_holder == first_eligible_holder_overall and current_holder != first_eligible_holder_overall:
            print("--- RESETANDO CICLO (Detectado ao passar para o primeiro elegível) ---")
            st.session_state.skip_flags = {c: False for c in CONSULTORES if st.session_state.get(f'check_{c}')}
            skips = st.session_state.skip_flags 
            reset_triggered = True
            next_index = first_eligible_index_overall 
        else:
            next_index = potential_next_index
    else:
        next_index = -1

    if next_index != -1:
        next_holder = queue[next_index]
        print(f'Passando bastão de {current_holder} para {next_holder} (Reset Triggered: {reset_triggered})')
        duration = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        
        log_status_change(current_holder, 'Bastão', '', duration) # <-- Chama log_status_change
        st.session_state.status_texto[current_holder] = '' 
        
        log_status_change(next_holder, st.session_state.status_texto.get(next_holder, ''), 'Bastão', timedelta(0)) # <-- Chama log_status_change
        st.session_state.status_texto[next_holder] = 'Bastão'
        
        st.session_state.bastao_start_time = datetime.now()
        st.session_state.skip_flags[next_holder] = False 
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound = True # <-- Toca som na passagem
        print("SOUND TRIGGER: rotate_bastao successful.")
        st.session_state.rotation_gif_start_time = datetime.now()
        
        # save_state() é chamado dentro de log_status_change
    else:
        print('Ninguém elegível. Forçando re-check e mantendo estado atual.')
        st.warning('Não há próximo consultor elegível na fila no momento.')
        check_and_assume_baton() 

def toggle_skip(): 
    # (Código mantido, sem st.rerun())
    print('CALLBACK TOGGLE SKIP')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 

    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    if not st.session_state.get(f'check_{selected}'): st.warning(f'{selected} não está disponível para marcar/desmarcar.'); return

    current_skip_status = st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = not current_skip_status
    new_status_str = 'MARCADO para pular' if not current_skip_status else 'DESMARCADO para pular'
    print(f'{selected} foi {new_status_str}')

    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected == current_holder and st.session_state.skip_flags[selected]:
        print(f'Portador {selected} se marcou para pular. Tentando passar o bastão...')
        save_state() # Salva a flag de skip antes de chamar rotate
        rotate_bastao() # Pode tocar som aqui dentro
        return 

    save_state() 

def update_status(status_text, change_to_available): 
    # (Código mantido, chama log_status_change)
    print(f'CALLBACK UPDATE STATUS: {status_text}')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': 
        st.warning('Selecione um consultor.')
        return

    if status_text != 'Almoço':
        st.session_state.lunch_warning_info = None
    
    current_lunch_warning = st.session_state.get('lunch_warning_info')
    is_second_try = False
    if current_lunch_warning and current_lunch_warning.get('consultor') == selected:
         elapsed = (datetime.now() - current_lunch_warning.get('start_time', datetime.min)).total_seconds()
         if elapsed < 30:
             is_second_try = True 

    if status_text == 'Almoço' and not is_second_try:
        all_statuses = st.session_state.status_texto
        num_na_fila = sum(1 for s in all_statuses.values() if s == '' or s == 'Bastão')
        num_atividade = sum(1 for s in all_statuses.values() if s == 'Atividade')
        total_ativos = num_na_fila + num_atividade
        num_almoco = sum(1 for s in all_statuses.values() if s == 'Almoço')
        limite_almoco = total_ativos / 2.0
        
        print(f"Check Almoço: Ativos={total_ativos}, EmAlmoço={num_almoco}, Limite={limite_almoco}")
        
        if total_ativos > 0 and num_almoco >= limite_almoco:
            print(f"AVISO ALMOÇO (Global): {selected}.")
            st.session_state.lunch_warning_info = {
                'consultor': selected,
                'start_time': datetime.now(),
                'message': f'Consultor {selected} verificar horário. Metade dos consultores ativos já em almoço. Clique novamente em "Almoço" para confirmar.'
            }
            save_state() 
            return 
            
    st.session_state.lunch_warning_info = None

    st.session_state[f'check_{selected}'] = False 
    was_holder = next((True for c, s in st.session_state.status_texto.items() if s == 'Bastão' and c == selected), False)
    old_status = st.session_state.status_texto.get(selected, '') or ('Bastão' if was_holder else 'Disponível')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    
    # Loga a mudança ANTES de mudar o status_texto
    log_status_change(selected, old_status, status_text, duration) # <-- Chama log_status_change
    
    st.session_state.status_texto[selected] = status_text 

    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.skip_flags.pop(selected, None)

    if status_text == 'Saída Temporária':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)

    print(f'... Fila: {st.session_state.bastao_queue}, Skips: {st.session_state.skip_flags}')
    baton_changed = False
    if was_holder: 
        baton_changed = check_and_assume_baton() # Pode tocar som aqui dentro
    
    # save_state() é chamado dentro de log_status_change e check_and_assume_baton
    # então não é estritamente necessário aqui, a menos que NENHUMA das duas
    # condições acima seja verdadeira, o que é raro. Adicionar por segurança.
    if not baton_changed and not was_holder:
        save_state() 


def manual_rerun():
    print('CALLBACK MANUAL RERUN')
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    st.rerun() 

# ============================================
# 4. EXECUÇÃO PRINCIPAL DO STREAMLIT APP
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")
# Linha que esconde alertas removida 
init_session_state()

st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)

st.title(f'Controle Bastão Cesupe {BASTAO_EMOJI}')
st.markdown("<hr style='border: 1px solid #E75480;'>", unsafe_allow_html=True)

gif_start_time = st.session_state.get('rotation_gif_start_time')
lunch_warning_info = st.session_state.get('lunch_warning_info') 

show_gif = False
show_lunch_warning = False
refresh_interval = 40000 

if gif_start_time:
    try:
        elapsed = (datetime.now() - gif_start_time).total_seconds()
        if elapsed < 20: 
            show_gif = True
            refresh_interval = 2000 
        else: 
            st.session_state.rotation_gif_start_time = None
            save_state() 
    except: 
        st.session_state.rotation_gif_start_time = None
        
if lunch_warning_info and lunch_warning_info.get('start_time'):
    try:
        elapsed_lunch = (datetime.now() - lunch_warning_info['start_time']).total_seconds()
        if elapsed_lunch < 30: 
            show_lunch_warning = True
            refresh_interval = 2000 
        else:
            st.session_state.lunch_warning_info = None 
            save_state() 
    except Exception as e:
        print(f"Erro ao processar timer do aviso de almoço: {e}")
        st.session_state.lunch_warning_info = None
            
st_autorefresh(interval=refresh_interval, key='auto_rerun_key') 

# <-- MODIFICADO: Lógica de som simplificada -->
if st.session_state.get('play_sound', False):
    st.components.v1.html(play_sound_html(), height=0, width=0)
    st.session_state.play_sound = False # Reseta o som após renderizar

if show_gif: st.image(GIF_URL_ROTATION, width=200, caption='Bastão Passado!')

if show_lunch_warning:
    st.warning(f"🔔 **{lunch_warning_info['message']}**")
    st.image(GIF_URL_LUNCH_WARNING, width=200)

if st.session_state.get('gif_warning', False):
    st.error('🚫 Ação inválida! Verifique as regras.'); st.image(GIF_URL_WARNING, width=150)

# Layout
col_principal, col_disponibilidade = st.columns([1.5, 1])
queue = st.session_state.bastao_queue
skips = st.session_state.skip_flags
responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
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

# --- Coluna Principal ---
with col_principal:
    st.header("Responsável pelo Bastão")
    _, col_time = st.columns([0.25, 0.75])
    duration = timedelta()
    if responsavel and st.session_state.bastao_start_time:
        try: duration = datetime.now() - st.session_state.bastao_start_time
        except: pass
    col_time.markdown(f'#### 🕒 Tempo: **{format_time_duration(duration)}**')
    if responsavel:
        st.markdown(f'<span style="font-size: 2em; font-weight: bold;">{responsavel}</span>', unsafe_allow_html=True)
    else: st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
    st.markdown("###")

    st.header("Próximos da Fila")
    if proximo:
        st.markdown(f'### 1º: **{proximo}**')
    if restante:
        st.markdown(f'#### 2º em diante: {", ".join(restante)}')
    if not proximo and not restante:
        if responsavel: st.markdown('*Apenas o responsável atual é elegível.*')
        elif queue and all(skips.get(c, False) or not st.session_state.get(f'check_{c}') for c in queue) : st.markdown('*Todos disponíveis estão marcados para pular...*')
        else: st.markdown('*Ninguém elegível na fila.*')
    elif not restante and proximo: st.markdown("&nbsp;")


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

    st.markdown("###")
    st.header("**Consultor**")
    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### "); st.markdown("**Ações:**")
    
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
            ui_lists['fila'].append(nome) 
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

    # Verifica se deve enviar o relatório diário
    now = datetime.now()
    last_run_dt = st.session_state.report_last_run_date
    # Garante que last_run_dt seja datetime para comparação segura
    if not isinstance(last_run_dt, datetime):
        last_run_dt = datetime.min
        
    if now.hour >= 20 and now.date() > last_run_dt.date():
        send_daily_report()

print('--- FIM DO RENDER ---')
