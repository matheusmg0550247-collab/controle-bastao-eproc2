# ============================================
# 3. FUNÇÕES DE CALLBACK GLOBAIS (update_status Revisada)
# ============================================

# ... (funções update_queue, rotate_bastao, toggle_skip, etc. inalteradas)

def update_status(status_text, change_to_available): 
    print(f'CALLBACK UPDATE STATUS: {status_text}')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False
    st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return

    # 1. Pré-log e cálculos de duração
    st.session_state[f'check_{selected}'] = False # Desmarca o checkbox
    was_holder = next((True for c, s in st.session_state.status_texto.items() if s == 'Bastão' and c == selected), False)
    old_status = st.session_state.status_texto.get(selected, '') or ('Bastão' if was_holder else 'Disponível')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    
    # 2. Log e Definição do Novo Status (Final)
    log_status_change(selected, old_status, status_text, duration)
    st.session_state.status_texto[selected] = status_text # Define o status de Saída

    # --- Lógica de Limite de Almoço (Disparo) ---
    if status_text == 'Almoço':
        limit_reached, lunch_count = check_lunch_limit()
        
        if limit_reached:
            print(f'DEBUG ALMOÇO: ATIVANDO ALERTA! Acionado por {selected}.')
            st.session_state.lunch_warning_active = True
            st.session_state.lunch_warning_trigger_consultor = selected
        
    # Lógica de desativação (redundante, mas para segurança)
    elif old_status == 'Almoço' and st.session_state.lunch_warning_active:
        limit_reached, _ = check_lunch_limit()
        if not limit_reached:
            st.session_state.lunch_warning_active = False
            st.session_state.lunch_warning_trigger_consultor = None
            print("DEBUG ALMOÇO: ALERTA DESATIVADO por mudança de status (saiu do almoço).")
    # ----------------------------------------------------------------------------------

    # 3. Remove da fila e limpa skip flag
    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.skip_flags.pop(selected, None)

    # 4. Gerencia a fila de prioridade
    if status_text == 'Saída Temporária':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)

    # 5. Verifica o bastão se o portador saiu
    print(f'... Fila: {st.session_state.bastao_queue}, Skips: {st.session_state.skip_flags}')
    baton_changed = False
    if was_holder: 
        baton_changed = check_and_assume_baton()
    
    # O save_state é essencial aqui para persistir o novo estado do alerta de almoço no cache global
    if not baton_changed: save_state()
    st.rerun()


# ... (função update_queue inalterada em relação à última versão)
