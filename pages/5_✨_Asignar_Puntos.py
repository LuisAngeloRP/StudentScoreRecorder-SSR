# pages/5_asignar_puntos.py
import streamlit as st
import pandas as pd
from supabase import create_client
import time
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Asignación de Puntos", page_icon="🎯", layout="wide")

# Inicializar conexión con Supabase
@st.cache_resource
def init_connection():
    return create_client(
        st.secrets["supabase_url"],
        st.secrets["supabase_key"]
    )

supabase = init_connection()

# Inicializar estados si no existen
if 'puntos_individuales_pendientes' not in st.session_state:
    st.session_state.puntos_individuales_pendientes = {}
if 'puntos_grupales_pendientes' not in st.session_state:
    st.session_state.puntos_grupales_pendientes = {}
if 'ultimo_cambio' not in st.session_state:
    st.session_state.ultimo_cambio = time.time()

# Función para guardar puntos en la base de datos
def guardar_puntos():
    with st.spinner('Guardando puntos...'):
        try:
            # Guardar puntos individuales
            for punto_id, puntos in st.session_state.puntos_individuales_pendientes.items():
                supabase.table('puntos_individuales')\
                    .update({'puntos': puntos})\
                    .eq('id', punto_id)\
                    .execute()
            st.session_state.puntos_individuales_pendientes = {}

            # Guardar puntos grupales
            for punto_id, puntos in st.session_state.puntos_grupales_pendientes.items():
                supabase.table('puntos_grupales')\
                    .update({'puntos': puntos})\
                    .eq('id', punto_id)\
                    .execute()
            st.session_state.puntos_grupales_pendientes = {}

            st.success('✅ Puntos guardados exitosamente')
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar puntos: {str(e)}")

# Verificar curso y sesión seleccionados
if 'curso_actual' not in st.session_state:
    st.warning("⚠️ Por favor, selecciona un curso en la página de Gestión de Cursos")
    st.page_link("pages/1_📚_Mis_Cursos.py", label="Ir a Gestión de Cursos")
    st.stop()

# Selector de sesión
if 'sesion_actual' not in st.session_state:
    sesiones = supabase.table('sesiones')\
        .select('*')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .order('fecha', desc=True)\
        .execute()

    if not sesiones.data:
        st.warning("No hay sesiones creadas para este curso")
        st.stop()

    sesion_seleccionada = st.selectbox(
        "Seleccionar Sesión",
        options=[s['id'] for s in sesiones.data],
        format_func=lambda x: next(s['nombre'] + f" ({s['fecha']})" for s in sesiones.data if s['id'] == x)
    )

    if sesion_seleccionada:
        st.session_state.sesion_actual = sesion_seleccionada
        st.session_state.sesion_nombre = next(s['nombre'] for s in sesiones.data if s['id'] == sesion_seleccionada)
        st.rerun()

# Obtener información de la sesión actual
sesion = supabase.table('sesiones')\
    .select('*')\
    .eq('id', st.session_state.sesion_actual)\
    .execute()

if not sesion.data:
    st.error("Error al cargar la información de la sesión")
    st.stop()

# Mostrar información de la sesión
col1, col2, col3 = st.columns([2,2,1])
with col1:
    st.info(f"📚 Curso: {st.session_state.get('curso_nombre', 'No seleccionado')}")
with col2:
    st.info(f"📅 Sesión: {st.session_state.get('sesion_nombre', 'No seleccionada')}")
with col3:
    st.info(f"Máximo: {sesion.data[0]['puntaje_maximo']}")

# Tabs para diferentes vistas
tab1, tab2 = st.tabs(["👥 Vista por Grupos", "👤 Vista Individual"])

# Vista de Grupos
with tab1:
    grupos = supabase.table('grupos')\
        .select('*')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .execute()

    if grupos.data:
        for grupo in grupos.data:
            with st.expander(f"👥 {grupo['nombre']}", expanded=True):
                # Obtener puntos grupales
                puntos_grupales = supabase.table('puntos_grupales')\
                    .select('*')\
                    .eq('sesion_id', st.session_state.sesion_actual)\
                    .eq('grupo_id', grupo['id'])\
                    .execute()

                if not puntos_grupales.data:
                    # Crear registro de puntos grupales si no existe
                    puntos_grupales = supabase.table('puntos_grupales').insert({
                        'sesion_id': st.session_state.sesion_actual,
                        'grupo_id': grupo['id'],
                        'puntos': 0
                    }).execute()

                punto_grupal = puntos_grupales.data[0]

                # Obtener estudiantes del grupo
                estudiantes_grupo = supabase.table('estudiantes_grupo')\
                    .select('estudiante_id, estudiantes_curso!inner(*)')\
                    .eq('grupo_id', grupo['id'])\
                    .execute()

                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if estudiantes_grupo.data:
                        for estudiante in estudiantes_grupo.data:
                            est = estudiante['estudiantes_curso']
                            # Obtener puntos individuales del estudiante
                            puntos_ind = supabase.table('puntos_individuales')\
                                .select('*')\
                                .eq('sesion_id', st.session_state.sesion_actual)\
                                .eq('estudiante_id', est['id'])\
                                .execute()

                            if not puntos_ind.data:
                                # Crear registro de puntos individuales si no existe
                                puntos_ind = supabase.table('puntos_individuales').insert({
                                    'sesion_id': st.session_state.sesion_actual,
                                    'estudiante_id': est['id'],
                                    'puntos': 0
                                }).execute()

                            punto_individual = puntos_ind.data[0]
                            
                            puntos_actuales = {
                                'individual': st.session_state.puntos_individuales_pendientes.get(
                                    punto_individual['id'], punto_individual['puntos']
                                ),
                                'grupal': st.session_state.puntos_grupales_pendientes.get(
                                    punto_grupal['id'], punto_grupal['puntos']
                                )
                            }
                            
                            total = puntos_actuales['individual'] + puntos_actuales['grupal']
                            st.write(
                                f"- {est['apellidos']}, {est['nombres']} "
                                f"(Individual: {puntos_actuales['individual']}, "
                                f"Grupal: {puntos_actuales['grupal']}, "
                                f"Total: {total})"
                            )
                
                with col2:
                    nuevo_puntaje = st.number_input(
                        "Puntos grupales",
                        min_value=0.0,
                        max_value=float(sesion.data[0]['puntaje_maximo']),
                        value=float(punto_grupal['puntos']),
                        step=0.5,
                        key=f"grupo_{grupo['id']}"
                    )
                    
                    if st.button("Asignar", key=f"btn_grupo_{grupo['id']}"):
                        st.session_state.puntos_grupales_pendientes[punto_grupal['id']] = nuevo_puntaje
                        st.session_state.ultimo_cambio = time.time()
                        st.success(f"Puntos asignados al grupo: {nuevo_puntaje}")
    else:
        st.info("No hay grupos creados en este curso")

# Vista Individual
with tab2:
    # Agregar buscador
    busqueda = st.text_input("🔍 Buscar estudiante (nombre o apellido)", "")
    
    estudiantes = supabase.table('estudiantes_curso')\
        .select('*')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .order('apellidos')\
        .execute()

    if estudiantes.data:
        # Filtrar estudiantes según la búsqueda
        estudiantes_filtrados = estudiantes.data
        if busqueda:
            busqueda = busqueda.lower()
            estudiantes_filtrados = [
                est for est in estudiantes.data
                if busqueda in f"{est['nombres']} {est['apellidos']}".lower()
            ]

        # Contenedor para centrar el contenido
        with st.container():
            for estudiante in estudiantes_filtrados:
                # Obtener puntos individuales
                puntos_ind = supabase.table('puntos_individuales')\
                    .select('*')\
                    .eq('sesion_id', st.session_state.sesion_actual)\
                    .eq('estudiante_id', estudiante['id'])\
                    .execute()

                if not puntos_ind.data:
                    puntos_ind = supabase.table('puntos_individuales').insert({
                        'sesion_id': st.session_state.sesion_actual,
                        'estudiante_id': estudiante['id'],
                        'puntos': 0
                    }).execute()

                punto_individual = puntos_ind.data[0]

                # Obtener puntos grupales (si pertenece a grupos)
                puntos_grupales_total = 0
                grupos_est = supabase.table('estudiantes_grupo')\
                    .select('grupo_id')\
                    .eq('estudiante_id', estudiante['id'])\
                    .execute()

                if grupos_est.data:
                    for grupo in grupos_est.data:
                        pg = supabase.table('puntos_grupales')\
                            .select('*')\
                            .eq('sesion_id', st.session_state.sesion_actual)\
                            .eq('grupo_id', grupo['grupo_id'])\
                            .execute()
                        
                        if pg.data:
                            puntos_grupales_total += st.session_state.puntos_grupales_pendientes.get(
                                pg.data[0]['id'], pg.data[0]['puntos']
                            )

                # Centrar el contenido usando columnas
                _, col_central, _ = st.columns([1, 2, 1])
                
                with col_central:
                    puntos_ind_actuales = st.session_state.puntos_individuales_pendientes.get(
                        punto_individual['id'], punto_individual['puntos']
                    )
                    
                    # Aplicar color rojo si tiene 0 puntos
                    nombre_estudiante = f"{estudiante['apellidos']}, {estudiante['nombres']}"
                    if puntos_ind_actuales == 0:
                        nombre_estudiante = f":red[{nombre_estudiante}]"
                    
                    nuevo_puntaje = st.number_input(
                        f"**{nombre_estudiante}**",
                        min_value=0.0,
                        max_value=float(sesion.data[0]['puntaje_maximo']),
                        value=float(puntos_ind_actuales),
                        step=0.5,
                        key=f"ind_{estudiante['id']}"
                    )
                    
                    if nuevo_puntaje != puntos_ind_actuales:
                        st.session_state.puntos_individuales_pendientes[punto_individual['id']] = nuevo_puntaje
                        st.session_state.ultimo_cambio = time.time()
                    
# Barra inferior con estado y botón de guardar
st.markdown("---")
col1, col2 = st.columns([3,1])

cambios_pendientes = len(st.session_state.puntos_individuales_pendientes) + \
                    len(st.session_state.puntos_grupales_pendientes)

with col1:
    if cambios_pendientes > 0:
        tiempo_espera = max(5 - (time.time() - st.session_state.ultimo_cambio), 0)
        st.info(f"Hay {cambios_pendientes} cambios pendientes. "
               f"Se guardarán automáticamente en {tiempo_espera:.1f} segundos.")

with col2:
    if cambios_pendientes > 0:
        if st.button("💾 Guardar Ahora", key="guardar_manual", use_container_width=True):
            guardar_puntos()

# Guardado automático después de 5 segundos
if cambios_pendientes > 0 and (time.time() - st.session_state.ultimo_cambio) >= 5:
    guardar_puntos()