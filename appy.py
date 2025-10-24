# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh

# --- Constantes de Consultores (Mantidas) ---
CONSULTORES = sorted([
    "Alex Paulo da Silva",
# ... (Lista de consultores omitida por brevidade, mas mantida no código)
    "Vanessa Ligiane Pimenta Santos"
])

# --- FUNÇÃO DE CACHE GLOBAL ---
# ... (Função get_global_state_cache mantida)
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
        # NOVO: Variável para controle de bloqueio na primeira tentativa (GLOBAL)
        'skip_block': {}, 
    }

# --- Constantes ---
# ... (Constantes mantidas)
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/refs/heads/main/doorbell-223669.mp3"
# NOVO GIF DE ALERTA DE ALMOÇO
GIF_URL_LUNCH_ALERT = 'https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExMjBjN2l5eG52ejN6cW1sYjZobXRsdDd0NjZ6aXV0aGg5aXA5N2EyZCZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/wmGUXuhdoL9TFhDDet/giphy.gif'

# ... (STATUSES_DE_SAIDA e outras constantes mantidas)

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

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
        # NOVO: Salva o estado de bloqueio
        global_data['skip_block'] = st.session_state.skip_block.copy() 

        print(f'*** Estado GLOBAL Salvo (Cache de Recurso) ***')
    except Exception as e: 
        print(f'Erro ao salvar estado GLOBAL: {e}')

# --- FUNÇÃO `load_state` (GLOBAL) ---
def load_state():
# ... (Função load_state mantida)
    """Carrega o estado GLOBAL (Cache) e retorna para a sessão LOCAL."""
    global_data = get_global_state_cache()
    loaded_data = {k: v for k, v in global_data.items()}
    return loaded_data

# ... (Outras funções auxiliares mantidas)

def init_session_state():
    """Inicializa/sincroniza o st.session_state com o estado GLOBAL do cache."""
    persisted_state = load_state()
    
    defaults = {
        'bastao_start_time': None, 
        'report_last_run_date': datetime.min, 
        'rotation_gif_start_time': None,
        'play_sound': False, 
        'gif_warning': False,
        # NOVO: Estado para controle de alerta de almoço (LOCAL DE SESSÃO)
        'lunch_alert_time': None, 
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
    # NOVO: Sincroniza a variável de bloqueio da primeira tentativa
    st.session_state['skip_block'] = persisted_state.get('skip_block', {}).copy()
    
    # ... (Restante da função init_session_state mantida)
    # Garante que todos os consultores estão nas listas de controle e sincroniza o checkbox
    for nome in CONSULTORES:
    # ... (Conteúdo do loop mantido)
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
# NOVA FUNÇÃO DE LÓGICA DE ALMOÇO
# ============================================
def check_lunch_capacity(consultor_tentativa):
    """
    Verifica se a marcação de 'Almoço' pelo consultor_tentativa excede 50%.
    
    Retorna True se DEVE BLOQUEAR, False caso contrário (pode prosseguir).
    """
    status_map = st.session_state.status_texto
    
    # Consultores que devem ser desconsiderados do cálculo do total
    ignored_statuses = ['Sessão', 'Ausente', 'Indisponível']
    
    # Total de consultores considerados ativos/elegíveis (não ignorados)
    total_ativos = sum(1 for c in CONSULTORES if status_map.get(c) not in ignored_statuses)
    
    # Número atual de consultores em Almoço
    num_em_almoco = sum(1 for c, s in status_map.items() if s == 'Almoço')
    
    # Se o consultor_tentativa NÃO está em Almoço e está tentando entrar:
    if status_map.get(consultor_tentativa) != 'Almoço':
        
        # A nova contagem de almoço será: atual + 1 (o consultor_tentativa)
        num_almoco_apos_tentativa = num_em_almoco + 1
        
        # Se o consultor_tentativa está em um status ignorado, o total_ativos não muda.
        # Se ele NÃO está em um status ignorado, o total_ativos não muda. 
        # Apenas se ele estivesse em um status IGNORADO e fosse considerado no total_ativos
        # e estivesse saindo para almoço, o total_ativos mudaria.
        # Simplificando, vamos considerar o total_ativos como a base.
        
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

# ============================================
# 3. FUNÇÕES DE CALLBACK GLOBAIS
# ============================================

# ... (Funções update_queue, rotate_bastao, toggle_skip mantidas)

def update_status(status_text, change_to_available): 
    print(f'CALLBACK UPDATE STATUS: {status_text}')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    
    if not selected or selected == 'Selecione um nome': 
        st.warning('Selecione um consultor.'); return

    # --- NOVA LÓGICA DE BLOQUEIO DE ALMOÇO ---
    if status_text == 'Almoço':
        if check_lunch_capacity(selected):
            # Se a checagem retornar True (deve bloquear), define o alerta e RERUN
            st.session_state.lunch_alert_time = datetime.now()
            # Reinicializa a opção do selectbox para o usuário tentar novamente
            st.session_state['consultor_selectbox'] = 'Selecione um nome' 
            save_state()
            st.rerun() 
            return # Sai da função, bloqueando a marcação

    # Se passou pelo check_lunch_capacity (ou não era Almoço):
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
    st.rerun()


def manual_rerun():
    print('CALLBACK MANUAL RERUN')
    # Limpa o alerta de almoço ao tentar atualizar manualmente
    if st.session_state.lunch_alert_time:
         st.session_state.lunch_alert_time = None
         
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.rerun()

# ============================================
# 4. EXECUÇÃO PRINCIPAL DO STREAMLIT APP
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")
st.markdown('<style>div.stAlert { display: none !important; }</style>', unsafe_allow_html=True)
# O estado é carregado aqui do cache global
init_session_state()

# --- Scroll para o Topo (CORRIGIDO) ---
st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
# --- Fim Scroll para o Topo ---

st.title(f'Controle Bastão Cesupe {BASTAO_EMOJI}')
st.markdown("<hr style='border: 1px solid #E75480;'>", unsafe_allow_html=True)

# Auto Refresh & Timed Elements
gif_start_time = st.session_state.get('rotation_gif_start_time')
lunch_alert_time = st.session_state.get('lunch_alert_time')
show_gif = False; 
refresh_interval = 40000 # 40 segundos (40.000 milissegundos)

if gif_start_time:
    try:
        elapsed = (datetime.now() - gif_start_time).total_seconds()
        if elapsed < 20: 
             show_gif = True; 
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
            refresh_interval = min(refresh_interval, 1000) # 1 segundo de refresh para a mensagem desaparecer rápido
        else:
            st.session_state.lunch_alert_time = None # Limpa a mensagem
            
    except:
        st.session_state.lunch_alert_time = None
        
st_autorefresh(interval=refresh_interval, key='auto_rerun_key') 
# --- Fim Lógica de Alerta de Almoço ---

if st.session_state.get('play_sound', False):
    st.components.v1.html(play_sound_html(), height=0, width=0); st.session_state.play_sound = False
    
if show_gif: st.image(GIF_URL_ROTATION, width=200, caption='Bastão Passado!')

if st.session_state.get('gif_warning', False):
    st.error('🚫 Ação inválida! Verifique as regras.'); st.image(GIF_URL_WARNING, width=150)

# Alerta de Almoço (aparece no topo)
if show_lunch_alert:
    consultor_bloqueado = st.session_state.consultor_selectbox # Use o último consultor selecionado antes do bloqueio
    st.warning(f'🚫 **{consultor_bloqueado}**, verificar marcação. Mais da metade dos consultores encontra-se em horário de almoço.')
    st.image(GIF_URL_LUNCH_ALERT, width=150)

# Layout
col_principal, col_disponibilidade = st.columns([1.5, 1])
# ... (Restante do código de layout mantido)

# --- Coluna Principal (Mantida, apenas os botões expandidos) ---
with col_principal:
# ... (Cabeçalhos e informações da fila mantidos)

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

# --- Coluna Disponibilidade (Mantida) ---
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
