import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh



# --- 2. Definição das Variáveis Globais ---

# ATENÇÃO: NGROK_AUTH_TOKEN e LOG/EXECUÇÃO SÃO REMOVIDOS.



# 🛑 WEBHOOK DE RELATÓRIO DIÁRIO (MANTIDO)

GOOGLE_CHAT_WEBHOOK_RELATORIO = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"



# ⬇️ NOVO WEBHOOK PARA NOTIFICAÇÃO IMEDIATA DE TROCA DE BASTÃO

CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"



BASTAO_EMOJI = "🌸"



# ⬅️ URL PERMANENTE DO SEU APP (Substitua se usou outro nome)

APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app' 



CONSULTORES = [

    "Barbara", "Bruno", "Claudia", "Douglas", "Fábio", "Glayce", "Isac",

    "Isabela", "Ivana", "Leonardo", "Morôni", "Michael", "Pablo", "Ranyer",

    "Victoria"

]



# --- 4. CÓDIGO DO APP STREAMLIT (app.py) ---

def generate_app_code(consultores, emoji, webhook_relatorio, webhook_bastao, public_url):

    app_code_lines = [

        "import streamlit as st",

        "import pandas as pd",

        "import requests",

        "import time",

        "import json",

        "import os",

        "from datetime import datetime, timedelta",

        "from operator import itemgetter",

        "from streamlit_autorefresh import st_autorefresh",

        "",

        f"BASTAO_EMOJI = '{emoji}'",

        f"CONSULTORES = {consultores}",

        f"WEBHOOK_RELATORIO = '{webhook_relatorio}'", 

        f"WEBHOOK_BASTAO = '{webhook_bastao}'",

        f"APP_URL = '{public_url}'",

        "TIMER_RERUN_S = 30",

        "LOG_FILE = 'status_log.json'",

        "STATE_FILE = 'app_state.json'",

        "YOUTUBE_ID = 'yW0D5iK0i_A'",

        "START_TIME_S = 10",

        "PLAYBACK_TIME_MS = 10000",

        "STATUS_SAIDA_PRIORIDADE = ['Saída Temporária']",

        "STATUSES_DE_SAIDA = ['Atividade', 'Almoço', 'Saída Temporária']",

        "GIF_URL = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'",

        "",

        "# --- Funções de Persistência de Estado ---",

        "",

        "def date_serializer(obj):",

        "    if isinstance(obj, datetime):",

        "        return obj.isoformat()",

        "    return str(obj)",

        "",

        "def save_state():",

        "    state_to_save = {",

        "        'status_texto': st.session_state.status_texto,",

        "        'bastao_queue': st.session_state.bastao_queue,",

        "        'bastao_start_time': st.session_state.bastao_start_time,",

        "        'current_status_starts': st.session_state.current_status_starts,",

        "        'report_last_run_date': st.session_state.report_last_run_date,",

        "        'bastao_counts': st.session_state.bastao_counts,",

        "        'priority_return_queue': st.session_state.priority_return_queue,",

        "        'skip_status_display': st.session_state.skip_status_display,",

        "        'skipped_consultors': st.session_state.skipped_consultors,",

        "        'cycle_start_marker': st.session_state.cycle_start_marker,",

        "    }",

        "    try:",

        "        with open(STATE_FILE, 'w') as f:",

        "            json.dump(state_to_save, f, indent=4, default=date_serializer)",

        "    except Exception as e:",

        "        print(f'Erro ao salvar estado: {e}')",

        "",

        "def load_state():",

        "    if os.path.exists(STATE_FILE):",

        "        try:",

        "            with open(STATE_FILE, 'r') as f:",

        "                data = json.load(f)",

        "            ",

        "            for key in ['bastao_start_time', 'report_last_run_date']:",

        "                if data.get(key):",

        "                    data[key] = datetime.fromisoformat(data[key])",

        "            for consultor, time_str in data['current_status_starts'].items():",

        "                data['current_status_starts'][consultor] = datetime.fromisoformat(time_str)",

        "            ",

        "            return data",

        "        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:",

        "            print(f'Erro ao carregar estado: {e}. Iniciando estado padrão.')",

        "            return {}",

        "    return {}",

        "",

        "# --- Funções de Log e Notificação ---",

        "",

        "def send_chat_notification_internal(consultor, status):",

        "    if WEBHOOK_BASTAO and status == 'Bastão':",

        '        message_template = "🎉 **BASTÃO GIRADO!** 🎉 \\n\\n- **Novo Responsável:** {consultor}\\n- **Acesse o Painel:** https://controle-bastao-eproc.streamlit.app/" ',

        '        message_text = message_template.format(consultor=consultor, app_url=APP_URL)',

        '        chat_message = {"text": message_text}',

        '        try:',

        '            response = requests.post(WEBHOOK_BASTAO, json=chat_message)',

        '            response.raise_for_status()',

        '            return True',

        '        except requests.exceptions.RequestException as e: ',

        '            print("="*60)',

        '            print(f"❌ ERRO GRAVE: FALHA AO ENVIAR NOTIFICAÇÃO DE BASTÃO.")',

        '            print(f"URL USADA: {WEBHOOK_BASTAO}")',

        '            print(f"ERRO: {e}")',

        '            if e.response is not None:',

        '                print(f"STATUS CODE: {e.response.status_code}")',

        '                print(f"RESPOSTA DO SERVIDOR: {e.response.text}")',

        '            print("="*60)',

        '            return False',

        '    return False',

        "",

        "def play_sound_html():",

        '    return """',

        '<audio autoplay="true">',

        '            <source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mp3">',

        '</audio>',

        '"""',

        "",

        "def load_logs():",

        "    try:",

        "        with open(LOG_FILE, 'r') as f:",

        "            return json.load(f)",

        "    except (FileNotFoundError, json.JSONDecodeError):",

        "        return []",

        "def save_logs(logs):\n",

        "    with open(LOG_FILE, 'w') as f: json.dump(logs, f, indent=4, default=date_serializer)",

        "def log_status_change(consultor, old_status, new_status, duration):",

        "    logs = load_logs()",

        "    log_entry = {",

        "        'consultor': consultor,",

        "        'old_status': old_status if old_status != '' else 'Disponível',",

        "        'new_status': new_status if new_status != '' else 'Disponível',",

        "        'duration_s': duration.total_seconds(),",

        "        'start_time': datetime.now().isoformat(),",

        "        'end_time': datetime.now().isoformat()",

        "    }",

        "    logs.append(log_entry)",

        "    save_logs(logs)",

        "    st.session_state['current_status_starts'][consultor] = datetime.now()",

        "    save_state()",

        "",

        "def format_time_duration(duration):",

        "    total_seconds = int(duration.total_seconds())",

        "    hours = total_seconds // 3600",

        "    minutes = (total_seconds % 3600) // 60",

        "    seconds = total_seconds % 60",

        "    return f'{hours:02}:{minutes:02}:{seconds:02}'",

        "",

        "def send_daily_report():",

        "    logs = load_logs()",

        "    today_str = datetime.now().date().isoformat()",

        "    report_data = [log for log in logs if log['start_time'].startswith(today_str)]",

        "    ",

        "    if not report_data or not WEBHOOK_RELATORIO:",

        "        st.session_state['report_last_run_date'] = datetime.now()",

        "        save_state()",

        "        return",

        "    ",

        "    TRACKED_STATUSES = ['Bastão', 'Atividade', 'Almoço', 'Saída Temporária', 'Disponível', 'Pulou Turno (Assumido)']",

        "    summary = {",

        "        consultor: {status: {'count': 0, 'duration_s': 0} for status in TRACKED_STATUSES}",

        "        for consultor in CONSULTORES",

        "    }",

        "    ",

        "    for log in report_data:",

        "        consultor = log['consultor']",

        "        status_to_track = log['old_status']",

        "        if log['new_status'] == 'Pulou Turno (Assumido)':",

        "            status_to_track = log['new_status']",

        "            ",

        "        duration = log['duration_s']",

        "        ",

        "        if consultor in summary and status_to_track in TRACKED_STATUSES:",

        "            summary[consultor][status_to_track]['duration_s'] += duration",

        "            summary[consultor][status_to_track]['count'] += 1",

        "    ",

        "    report_text = ''",

        "    total_movimentacoes = len(report_data)",

        "",

        "    report_text += f'📊 **RELATÓRIO DIÁRIO DE BASTÃO - {today_str}**\\n'",

        "    report_text += f'**Total de Movimentações:** {total_movimentacoes}\\n\\n'",

        "",

        "    bastao_ranking = sorted(",

        "        CONSULTORES,",

        "        key=lambda c: summary.get(c, {}).get('Bastão', {}).get('duration_s', 0),",

        "        reverse=True",

        "    )",

        "    ",

        "    for consultor in bastao_ranking:",

        "        report_text += f'**--- {consultor} ---**\\n'",

        "        consultor_summary = summary.get(consultor, {})",

        "        ",

        "        for status in TRACKED_STATUSES:",

        "            data = consultor_summary.get(status, {'count': 0, 'duration_s': 0})",

        "            if data['count'] > 0:",

        "                duration_td = timedelta(seconds=data['duration_s'])",

        "                duration_str = format_time_duration(duration_td)",

        "                report_text += f'- *{status.replace(' (Assumido)', '')}*: {data['count']}x ({duration_str})\\n'",

        "        ",

        "        report_text += '\\n'",

        "",

        "    chat_message = {",

        "        'text': report_text,",

        "        'cards': [",

        "            {",

        "                'header': {",

        "                    'title': f'{BASTAO_EMOJI} Relatório Diário do Bastão - {today_str}',",

        "                    'subtitle': 'Tempo e Contagem por Status',",

        "                    'imageUrl': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Blue_and_white_graph.svg/1024px-Blue_and_white_graph.svg.png'",

        "                },",

        "                'sections': [",

        "                    {",

        "                        'widgets': [",

        "                            {",

        "                                'textParagraph': {'text': report_text.replace('\\n', '<br>')}",

        "                            }",

        "                        ]",

        "                    }",

        "                ]",

        "            }",

        "        ]",

        "    }",

        "    ",

        "    try:",

        "        response = requests.post(WEBHOOK_RELATORIO, json=chat_message)",

        "        response.raise_for_status()",

        "        st.session_state['report_last_run_date'] = datetime.now()",

        "        save_state()",

        "    except requests.exceptions.RequestException as e: ",

        "        print('='*60)",

        "        print(f'❌ ERRO GRAVE: FALHA AO ENVIAR RELATÓRIO DIÁRIO.')",

        "        print(f'URL USADA: {WEBHOOK_RELATORIO}')",

        "        print(f'ERRO: {e}')",

        "        if e.response is not None:",

        "            print(f'STATUS CODE: {e.response.status_code}')",

        "            print(f'RESPOSTA DO SERVIDOR: {e.response.text}')",

        "        print('='*60)",

        "        ",

        "    st.rerun()",

        "",

        "# --- Inicialização do Session State ---",

        "",

        "def init_session_state():",

        "    persisted_state = load_state()",

        "    ",

        "    default_datetime = datetime.now()",

        "    default_date_min = datetime.min",

        "    ",

        "    st.session_state['status_texto'] = persisted_state.get('status_texto', {nome: '' for nome in CONSULTORES})",

        "    st.session_state['bastao_queue'] = persisted_state.get('bastao_queue', [])",

        "    st.session_state['bastao_start_time'] = persisted_state.get('bastao_start_time', None)",

        "    st.session_state['current_status_starts'] = persisted_state.get('current_status_starts', {nome: default_datetime for nome in CONSULTORES})",

        "    st.session_state['report_last_run_date'] = persisted_state.get('report_last_run_date', default_date_min)",

        "    st.session_state['bastao_counts'] = persisted_state.get('bastao_counts', {nome: 0 for nome in CONSULTORES})",

        "    st.session_state['priority_return_queue'] = persisted_state.get('priority_return_queue', [])",

        "    st.session_state['skip_status_display'] = persisted_state.get('skip_status_display', {nome: False for nome in CONSULTORES})",

        "    st.session_state['skipped_consultors'] = persisted_state.get('skipped_consultors', [])",

        "    st.session_state['cycle_start_marker'] = persisted_state.get('cycle_start_marker', None)",

        "    ",

        "    for nome in CONSULTORES:",

        "        checkbox_key = f'check_{nome}'",

        "        if checkbox_key not in st.session_state:",

        "            st.session_state[checkbox_key] = nome in persisted_state.get('bastao_queue', []) or nome in st.session_state['skipped_consultors']",

        "    \n",

        "    if not os.path.exists(STATE_FILE):",

        "        save_state()",

        "",

        "# --- Lógica Principal ---",

        "",

        "def manual_rerun():", 

        "    st.session_state['gif_warning'] = False ", 

        "    st.rerun()", 

        "    ",

        "def check_and_assume_baton(consultor=None):\n",

        "    current_responsavel = st.session_state['bastao_queue'][0] if st.session_state['bastao_queue'] else ''\n",

        "    \n",

        "    if current_responsavel and st.session_state['status_texto'].get(current_responsavel) == 'Bastão':\n",

        "        return\n",

        "    \n",

        "    for index, nome in enumerate(st.session_state['bastao_queue']):",

        "        current_status = st.session_state['status_texto'].get(nome, '')\n",

        "        \n",

        "        if nome in st.session_state['skipped_consultors']:\n",

        "             continue \n",

        "        \n",

        "        if current_status == '' and nome not in st.session_state['skipped_consultors']:\n",

        "            novo_responsavel = nome\n",

        "            \n",

        "            for c in CONSULTORES:\n",

        "                if st.session_state['status_texto'].get(c) == 'Bastão':\n",

        "                    st.session_state['status_texto'][c] = ''\n",

        "                    \n",

        "            novo_responsavel = nome\n",

        "            st.session_state['status_texto'][novo_responsavel] = 'Bastão'\n",

        "            st.session_state['bastao_start_time'] = datetime.now()\n",

        "            st.session_state['current_status_starts'][novo_responsavel] = datetime.now()\n",

        "            st.session_state['play_sound'] = True\n",

        "            st.session_state['gif_warning'] = False \n",

        "            st.session_state['skip_status_display'][novo_responsavel] = False \n",

        "            send_chat_notification_internal(novo_responsavel, 'Bastão')\n",

        "            save_state()\n",

        "            st.rerun()\n",

        "            return\n",

        "    \n",

        "    if current_responsavel and st.session_state['status_texto'].get(current_responsavel) in STATUSES_DE_SAIDA:\n",

        "        st.session_state['status_texto'][current_responsavel] = ''\n",

        "        st.session_state['bastao_start_time'] = None\n",

        "        save_state()\n",

        "        st.rerun()\n",

        "    \n",

        "def update_queue(consultor):\n",

        "    st.session_state['gif_warning'] = False \n",

        "    checkbox_key = f'check_{consultor}'\n",

        "    is_checked = st.session_state.get(checkbox_key, False)\n",

        "    old_status = st.session_state['status_texto'].get(consultor, '') or 'Disponível'\n",

        "    \n",

        "    if is_checked and consultor not in st.session_state['bastao_queue']:\n",

        "        duration = datetime.now() - st.session_state['current_status_starts'][consultor]\n",

        "        log_status_change(consultor, old_status, 'Disponível na Fila', duration)\n",

        "        \n",

        "        priority_queue = st.session_state.get('priority_return_queue', [])\n",

        "        \n",

        "        if consultor in st.session_state['skipped_consultors']:\n",

        "            st.session_state['skipped_consultors'].remove(consultor)\n",

        "            if not st.session_state['skipped_consultors']:\n",

        "                st.session_state['cycle_start_marker'] = None\n",

        "            \n",

        "        if consultor in priority_queue:\n",

        "            if st.session_state['bastao_queue']:\n",

        "                st.session_state['bastao_queue'].insert(1, consultor)\n",

        "            else:\n",

        "                st.session_state['bastao_queue'].append(consultor)\n",

        "            priority_queue.remove(consultor)\n",

        "        else:\n",

        "            st.session_state['bastao_queue'].append(consultor)\n",

        "            \n",

        "        st.session_state['status_texto'][consultor] = ''\n",

        "        st.session_state['skip_status_display'][consultor] = False \n",

        "        check_and_assume_baton(consultor)\n",

        "    elif not is_checked and consultor in st.session_state['bastao_queue']:\n",

        "        duration = datetime.now() - st.session_state['current_status_starts'][consultor]\n",

        "        log_status_change(consultor, old_status, 'Indisponível', duration)\n",

        "        st.session_state['bastao_queue'].remove(consultor)\n",

        "        st.session_state['status_texto'][consultor] = ''\n",

        "        st.session_state['skip_status_display'][consultor] = False \n",

        "        \n",

        "        if consultor in st.session_state['skipped_consultors']:\n",

        "            st.session_state['skipped_consultors'].remove(consultor)\n",

        "            if not st.session_state['skipped_consultors']:\n",

        "                st.session_state['cycle_start_marker'] = None\n",

        "            \n",

        "        check_and_assume_baton()\n",

        "    save_state()\n",

        "    st.rerun()\n",

        "    \n",

        "def rotate_bastao():\n",

        "    selected_name = st.session_state.get('consultor_selectbox', 'Selecione um nome')\n",

        "    st.session_state['gif_warning'] = False \n",

        "    if selected_name != 'Selecione um nome' and selected_name in st.session_state['status_texto']:\n",

        "        if st.session_state['bastao_queue'] and selected_name == st.session_state['bastao_queue'][0]:\n",

        "            antigo_responsavel = selected_name\n",

        "            old_status = 'Bastão'\n",

        "            \n",

        "            # 1. Lógica de reintrodução ANTES da rotação (se for o marcador)\n",

        "            if antigo_responsavel == st.session_state.get('cycle_start_marker') and st.session_state['skipped_consultors']:\n",

        "                \n",

        "                st.session_state['bastao_queue'].pop(0)\n",

        "                st.session_state['bastao_queue'].append(antigo_responsavel)\n",

        "                st.session_state['bastao_queue'].extend(st.session_state['skipped_consultors'])\n",

        "                \n",

        "                st.session_state['skipped_consultors'] = []\n",

        "                st.session_state['cycle_start_marker'] = None\n",

        "                \n",

        "                pass \n",

        "            \n",

        "            # 2. Rotação Padrão (só executa se não houve reintrodução do ciclo)\n",

        "            else: \n",

        "                if selected_name in st.session_state['bastao_queue']:\n",

        "                    st.session_state['bastao_queue'].remove(selected_name)\n",

        "                    st.session_state['bastao_queue'].append(selected_name)\n",

        "            \n",

        "            # 3. Log e atualização de status\n",

        "            st.session_state['status_texto'][antigo_responsavel] = ''\n",

        "            duration = datetime.now() - st.session_state['current_status_starts'][antigo_responsavel]\n",

        "            log_status_change(antigo_responsavel, old_status, 'Disponível na Fila', duration)\n",

        "            \n",

        "            st.session_state['bastao_counts'][antigo_responsavel] = st.session_state['bastao_counts'].get(antigo_responsavel, 0) + 1\n",

        "            st.session_state['play_sound'] = True\n",

        "            st.session_state['skip_status_display'][antigo_responsavel] = False \n",

        "            checkbox_key = f'check_{selected_name}'\n",

        "            st.session_state[checkbox_key] = True\n",

        "            \n",

        "            check_and_assume_baton()\n",

        "            st.rerun()\n",

        "        else:\n",

        "            st.session_state['gif_warning'] = True \n",

        "            st.rerun()\n",

        "    \n",

        "def skip_turn():\n",

        "    st.session_state['gif_warning'] = False \n",

        "    selected_name = st.session_state.get('consultor_selectbox', 'Selecione um nome')\n",

        "    if selected_name != 'Selecione um nome' and selected_name in st.session_state['status_texto']:\n",

        "        \n",

        "        queue = st.session_state['bastao_queue']\n",

        "        current_status = st.session_state['status_texto'].get(selected_name, '')\n",

        "        \n",

        "        if selected_name not in queue and current_status != 'Bastão':\n",

        "             st.warning('O consultor selecionado deve estar na fila ou com o Bastão para Pular.')\n",

        "             return\n",

        "        \n",

        "        if selected_name in queue:\n",

        "            # 1. MARCADOR DE CICLO: Se esta é a primeira pessoa a pular, marca quem está no topo da fila\n",

        "            if not st.session_state['skipped_consultors']:\n",

        "                if queue:\n",

        "                    st.session_state['cycle_start_marker'] = queue[0] \n",

        "                else:\n",

        "                    st.session_state['cycle_start_marker'] = None\n",

        "            \n",

        "            # 2. Log e manipulação de estado\n",

        "            old_status = current_status or 'Disponível'\n",

        "            duration = datetime.now() - st.session_state['current_status_starts'][selected_name]\n",

        "            log_status_change(selected_name, old_status, 'Pulou Turno (Fora da Fila)', duration)\n",

        "            \n",

        "            # 3. Remove da fila principal e adiciona à lista de pulo\n",

        "            queue.remove(selected_name)\n",

        "            st.session_state['skipped_consultors'].append(selected_name)\n",

        "            \n",

        "            # 4. Limpa o status e ativa o marcador visual\n",

        "            st.session_state['status_texto'][selected_name] = '' \n",

        "            st.session_state['skip_status_display'][selected_name] = True \n",

        "            \n",

        "            # 5. O CHECKBOX DEVE PERMANECER MARCADO (NÃO FAZER NADA AQUI)\n",

        "            \n",

        "            # 6. Tenta passar o bastão para o próximo\n",

        "            check_and_assume_baton()\n",

        "            save_state()\n",

        "            st.rerun()\n",

        "            \n",

        "        elif current_status == 'Bastão':\n",

        "             st.warning('O consultor com o bastão deve usar o botão **Bastão** ou **Status de Saída**.')\n",

        "             return\n",

        "    \n",

        "def update_status(status_text, change_to_available):\n",

        "    selected_name = st.session_state.get('consultor_selectbox', 'Selecione um nome')\n",

        "    st.session_state['gif_warning'] = False \n",

        "    \n",

        "    if selected_name != 'Selecione um nome' and selected_name in st.session_state['status_texto']:\n",

        "        old_status = st.session_state['status_texto'].get(selected_name, '') or 'Disponível'\n",

        "        new_status = status_text if status_text != '' else 'Disponível'\n",

        "        duration = datetime.now() - st.session_state['current_status_starts'][selected_name]\n",

        "        log_status_change(selected_name, old_status, new_status, duration)\n",

        "        \n",

        "        st.session_state['status_texto'][selected_name] = status_text\n",

        "        checkbox_key = f'check_{selected_name}'\n",

        "        \n",

        "        if change_to_available is not None:\n",

        "            st.session_state[checkbox_key] = change_to_available\n",

        "        \n",

        "        st.session_state['skip_status_display'][selected_name] = False\n",

        "        \n",

        "        if selected_name in st.session_state['skipped_consultors']:\n",

        "            st.session_state['skipped_consultors'].remove(selected_name)\n",

        "            if not st.session_state['skipped_consultors']:\n",

        "                st.session_state['cycle_start_marker'] = None\n",

        "        \n",

        "        if status_text in STATUSES_DE_SAIDA:\n",

        "            if selected_name in st.session_state['bastao_queue']:\n",

        "                st.session_state['bastao_queue'].remove(selected_name)\n",

        "            \n",

        "            if status_text in STATUS_SAIDA_PRIORIDADE:\n",

        "                if selected_name not in st.session_state['priority_return_queue']:\n",

        "                    st.session_state['priority_return_queue'].append(selected_name)\n",

        "            elif selected_name in st.session_state.get('priority_return_queue', []):\n",

        "                st.session_state['priority_return_queue'].remove(selected_name)\n",

        "        \n",

        "        check_and_assume_baton()\n",

        "        save_state()\n",

        "        st.rerun()\n",

        "    \n",

        "",

        "# --- INÍCIO DA APLICAÇÃO STREAMLIT (app.py) ---",

        "",

        "if 'gif_warning' not in st.session_state:",

        "    st.session_state['gif_warning'] = False",

        "if 'play_sound' not in st.session_state:",

        "    st.session_state['play_sound'] = False",

        "if 'last_rerun_time' not in st.session_state:",

        "    st.session_state['last_rerun_time'] = datetime.now()",

        "",

        "init_session_state()", 

        "",

        "st_autorefresh(interval=30000, key='auto_rerun_key')",

        "",

        "st.markdown(\"""<style>div.stAlert { display: none !important; }</style>\"\"\", unsafe_allow_html=True)",

        

        'st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")',



        "st.title(f'Controle Bastão Cesupe {BASTAO_EMOJI}')",

        'st.markdown("<hr style=\\"border: 1px solid #E75480;\\">", unsafe_allow_html=True)',



        "if st.session_state['gif_warning']:",

        "    st.error('🚫 Apenas o consultor com o bastão pode transferir o bastão!')",

        "    col_gif, col_spacer = st.columns([0.2, 0.8])",

        "    col_gif.image(GIF_URL, width=150)",



        'col_principal, col_disponibilidade = st.columns([1.5, 1])',



        "# RESPONSÁVEL PELO BASTÃO (LÓGICA DA FILA)",

        "responsavel = st.session_state['bastao_queue'][0] if st.session_state['bastao_queue'] else ''",

        "proximo_responsavel = st.session_state['bastao_queue'][1] if len(st.session_state['bastao_queue']) > 1 else ''",

        "fila_restante = st.session_state['bastao_queue'][2:]",



        "with col_principal:",

        '    st.header("Responsável pelo Bastão")',



        "    col_gif, col_time = st.columns([0.25, 0.75])",

        "    col_gif.image('https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExYjlqeWg3bXpuZ2ltMXdsNXJ6OW13eWF5aXlqYnc1NGNjamFjczlpOSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/xAFPuHVjmsBmU/giphy.gif', width=50)",



        "    bastao_duration = timedelta()",

        "    if responsavel and st.session_state.get('bastao_start_time'):",

        "        start_time = st.session_state['bastao_start_time']",

        "        try: bastao_duration = datetime.now() - start_time",

        "        except: pass",

        "        duration_text = format_time_duration(bastao_duration)",

        "        col_time.markdown(f'#### 🕒 Tempo: **{duration_text}**')",

        "    else:",

        "        col_time.markdown('#### 🕒 Tempo: --:--:--')",

        "",

        "    st.text_input(label='Responsável', value=responsavel, disabled=True, label_visibility='collapsed')",

        '    st.markdown("###")',



        # EXIBIÇÃO DA FILA COMPLETA

        '    st.header("Próximos da Fila")',

        "    if proximo_responsavel:",

        "        st.markdown(f'1º: **{proximo_responsavel}**')",

        "        if fila_restante:",

        "            st.markdown(f'2º em diante: {', '.join(fila_restante)}')",

        "    else:",

        '        st.markdown("*Fila vazia. Marque consultores como Disponíveis.*")',

        

        # ADICIONA A EXIBIÇÃO DE QUEM PULOU A VEZ

        "    if st.session_state['skipped_consultors']:",

        "        skipped_list = ', '.join(st.session_state['skipped_consultors'])",

        "        st.markdown(f'<span style=\"color:orange;\">🚫 Pulou a vez (Volta no próximo ciclo):</span> {skipped_list}', unsafe_allow_html=True)",

        

        '    st.markdown("###")',



        '    st.header("**Consultor**")',

        "    st.selectbox(",

        '        "Selecione o Consultor:",',

        "        options=['Selecione um nome'] + CONSULTORES,",

        "        index=0,",

        "        key='consultor_selectbox',",

        "        label_visibility='collapsed'",

        "    )",

        '    st.markdown("#### ")',

        '    st.markdown("**Mudar Status:**")',



        # 5 COLUNAS

        '    col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)',



        # Botões de Ação

        "    col_b1.button('🎯 Bastão', on_click=rotate_bastao, use_container_width=True)",

        "    col_b2.button('⏭️ Pular', on_click=skip_turn, use_container_width=True)",

        "    col_b3.button('✏️ Atividade', on_click=update_status, args=('Atividade', False,), use_container_width=True)",

        "    col_b4.button('🍽️ Almoço', on_click=update_status, args=('Almoço', False,), use_container_width=True)",

        "    col_b5.button('🚶 Saída', on_click=update_status, args=('Saída Temporária', False,), use_container_width=True)",



        '    st.markdown("####")',

        "    st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)",



        '    st.markdown("---")',



        # Coluna de Disponibilidade

        "with col_disponibilidade:",

        '    st.header("**Disponível**")',

        '    st.subheader("Marque para Disponível | Status de Atividade:")',



        # Lógica de cores para os status

        "    STATUS_MAP = {",

        "        'Bastão': ('#E75480', '🏆'),",

        "        'Atividade': ('#ffc107', '✏️'),",

        "        'Almoço': ('#007bff', '🍽️'),",

        "        'Saída Temporária': ('#dc3545', '🚶'),",

        "        '': ('#6c757d', ''),",

        "    }",



        "    for nome in CONSULTORES:",

        '        col_status, col_nome, col_check = st.columns([0.2, 1, 0.2])',

        "        checkbox_key = f'check_{nome}'",



        "        if checkbox_key not in st.session_state:",

        "            st.session_state[checkbox_key] = nome in st.session_state['bastao_queue']",

        "            ",

        "        is_available = col_check.checkbox(label=' ', key=checkbox_key, on_change=update_queue, args=(nome,), disabled=nome in st.session_state['skipped_consultors'])",

        "        current_status_text = st.session_state['status_texto'].get(nome, '')",

        "        is_skip_active = st.session_state['skip_status_display'].get(nome, False)",

        "        ",

        # LÓGICA DE EXIBIÇÃO VISUAL

        "        status_color, status_emoji = STATUS_MAP.get(current_status_text, ('#6c757d', ''))",

        "        display_name = nome",

        "        display_status = ''",

        "        \n",

        "        # Regra de exibição para quem pulou e está marcado (checkbox True)\n",

        "        if nome in st.session_state['skipped_consultors'] and is_available:",

        "            display_status = ' :orange-badge[PULOU]'",

        "        elif current_status_text in STATUSES_DE_SAIDA and current_status_text != '':",

        "            display_status = f'<span style=\"color:{status_color};\">{status_emoji} {current_status_text}</span>'",

        "        elif nome in st.session_state.get('priority_return_queue', []):",

        "            display_status = '<span style=\"color:#ffc107;\">⚠️ Retorno Prioritário</span>'",

        "        elif current_status_text == 'Bastão':",

        "            display_status = f'<span style=\"color:{status_color};\">**{status_emoji} BASTÃO**</span>'",

        "        elif current_status_text == '' and is_available and nome != responsavel:",

        "            display_status = '<span style=\"color:#007bff;\">✅ Disponível na Fila</span>'",

        "        elif not is_available:",

        "            display_status = '<span style=\"color:#dc3545;\">❌ Indisponível</span>'",

        "        \n",

        "        col_status.markdown(f'<span style=\"font-size: 1.5em; color:{status_emoji};\">{status_emoji}</span>', unsafe_allow_html=True)",

        "        col_nome.markdown(f'**{display_name}** {display_status}', unsafe_allow_html=True)",



        "    current_hour = datetime.now().hour",

        "    today = datetime.now().date()",

        "    last_run_date = st.session_state['report_last_run_date'].date()",

        "    ",

        "    if current_hour >= 20 and today > last_run_date:",

        "        send_daily_report()",

        "",

        ""

    ]



    return "\n".join(app_code_lines)



# ⬇️ CHAME A FUNÇÃO generate_app_code E EXECUTE O RESULTADO

# REMOVENDO AS DEPENDÊNCIAS DE NGROK E SUBPROCESS

app_code_final = generate_app_code(CONSULTORES, BASTAO_EMOJI, GOOGLE_CHAT_WEBHOOK_RELATORIO, CHAT_WEBHOOK_BASTAO, APP_URL_CLOUD)



# ⬅️ EXECUTA O CÓDIGO FINAL LIMPO NO AMBIENTE STREAMLIT

exec(app_code_final)
