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
if 'puntos_pendientes' not in st.session_state:
    st.session_state.puntos_pendientes = {}
if 'ultimo_cambio' not in st.session_state:
    st.session_state.ultimo_cambio = time.time()

# Función para guardar puntos en la base de datos
def guardar_puntos():
    if st.session_state.puntos_pendientes:
        with st.spinner('Guardando puntos...'):
            try:
                for punto_id, datos in st.session_state.puntos_pendientes.items():
                    supabase.table('puntos_sesion')\
                        .update({
                            'puntos': datos['puntos']
                        })\
                        .eq('id', punto_id)\
                        .execute()
                st.session_state.puntos_pendientes = {}
                st.success('✅ Puntos guardados exitosamente')
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar puntos: {str(e)}")

# Función para mostrar el encabezado con información del curso
def mostrar_encabezado():
    if 'curso_actual' not in st.session_state:
        st.warning("⚠️ No hay curso seleccionado")
        st.info("Por favor, selecciona un curso en la página de Gestión de Cursos")
        st.page_link("pages/1_gestionar_cursos.py", label="Ir a Gestión de Cursos")
        st.stop()
    else:
        # Obtener información actualizada del curso
        curso = supabase.table('cursos')\
            .select('*')\
            .eq('id', st.session_state.curso_actual)\
            .single()\
            .execute()
        
        if not curso.data:
            st.error("El curso seleccionado ya no existe")
            del st.session_state.curso_actual
            del st.session_state.curso_nombre
            st.rerun()
        
        st.info(f"📚 Curso actual: {curso.data['nombre']}")

# Título y encabezado
st.title("🎯 Asignación de Puntos")
mostrar_encabezado()

# Selector de sesión si no hay una seleccionada
if 'sesion_actual' not in st.session_state:
    sesiones = supabase.table('sesiones')\
        .select('*')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .order('fecha', desc=True)\
        .execute()

    if not sesiones.data:
        st.warning("No hay sesiones creadas para este curso")
        st.stop()

    # Crear selector de sesión
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
sesion_actual = supabase.table('sesiones')\
    .select('*')\
    .eq('id', st.session_state.sesion_actual)\
    .single()\
    .execute()

if not sesion_actual.data:
    st.error("Error al cargar la información de la sesión")
    st.stop()

# Mostrar información actual y botón para cambiar de sesión
col1, col2, col3 = st.columns([2,2,1])
with col1:
    st.info(f"📅 Sesión: {st.session_state.sesion_nombre}")
with col2:
    st.info(f"Puntaje máximo: {sesion_actual.data['puntaje_maximo']}")
with col3:
    if st.button("🔄 Cambiar Sesión"):
        del st.session_state.sesion_actual
        del st.session_state.sesion_nombre
        st.rerun()

# Tabs para diferentes vistas
tab1, tab2 = st.tabs(["👥 Vista por Grupos", "📋 Vista Individual"])

with tab1:
    # Obtener grupos del curso
    grupos = supabase.table('grupos')\
        .select('*')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .order('nombre')\
        .execute()

    if grupos.data:
        for grupo in grupos.data:
            with st.expander(f"👥 {grupo['nombre']}", expanded=True):
                # Obtener estudiantes del grupo
                estudiantes_grupo = supabase.table('estudiantes_grupo')\
                    .select('*, estudiantes_curso!inner(*)')\
                    .eq('grupo_id', grupo['id'])\
                    .execute()
                
                if estudiantes_grupo.data:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Mostrar lista de estudiantes y sus puntos actuales
                        for e in estudiantes_grupo.data:
                            est = e['estudiantes_curso']
                            punto = supabase.table('puntos_sesion')\
                                .select('*')\
                                .eq('sesion_id', st.session_state.sesion_actual)\
                                .eq('estudiante_id', est['id'])\
                                .single()\
                                .execute()
                            
                            if punto.data:
                                puntos_actual = st.session_state.puntos_pendientes.get(
                                    punto.data['id'], 
                                    {
                                        'puntos': punto.data['puntos']
                                    }
                                )
                                st.write(
                                    f"- {est['apellidos']}, {est['nombres']} "
                                    f"(Individual: {punto.data['puntos_individual']}, "  
                                    f"Grupal: {punto.data['puntos_grupal']}, "
                                    f"Total: {puntos_actual['puntos']})"
                                )
                    
                    with col2:
                        # Asignar puntos al grupo
                        puntos_grupo = st.number_input(
                            "Puntos para el grupo",
                            min_value=0.0,
                            max_value=float(sesion_actual.data['puntaje_maximo']),
                            step=0.5,
                            key=f"grupo_{grupo['id']}"
                        )
                        
                        if st.button("Asignar a todos", key=f"btn_grupo_{grupo['id']}"):
                            # Actualizar puntos para todos los miembros del grupo
                            for e in estudiantes_grupo.data:
                                punto = supabase.table('puntos_sesion')\
                                    .select('*')\
                                    .eq('sesion_id', st.session_state.sesion_actual)\
                                    .eq('estudiante_id', e['estudiante_id'])\
                                    .single()\
                                    .execute()
                                
                                if punto.data:
                                    st.session_state.puntos_pendientes[punto.data['id']] = {
                                        'puntos': punto.data['puntos'] + puntos_grupo
                                    }
                            
                            st.session_state.ultimo_cambio = time.time()
                            st.success(f"Puntos asignados al grupo: {puntos_grupo}")
    else:
        st.info("No hay grupos creados en este curso")

with tab2:
    # Obtener todos los estudiantes y sus puntos
    estudiantes = supabase.table('estudiantes_curso')\
        .select('*')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .order('apellidos')\
        .execute()

    if estudiantes.data:
        # Crear una tabla para todos los estudiantes
        for estudiante in estudiantes.data:
            # Obtener punto existente
            punto = supabase.table('puntos_sesion')\
                .select('*')\
                .eq('sesion_id', st.session_state.sesion_actual)\
                .eq('estudiante_id', estudiante['id'])\
                .single()\
                .execute()

            if punto.data:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**{estudiante['apellidos']}, {estudiante['nombres']}**")
                    # Mostrar desglose actual
                    puntos_actual = st.session_state.puntos_pendientes.get(
                        punto.data['id'], 
                        {
                            'puntos': punto.data['puntos']
                        }
                    )
                    st.write(
                        f"Individual: {punto.data['puntos_individual']} | "
                        f"Grupal: {punto.data['puntos_grupal']} | "
                        f"Total actual: {puntos_actual['puntos']}"
                    )
                
                with col2:
                    # Al modificar puntos individuales, mostramos el total resultante
                    nuevo_individual = st.number_input(
                        "Puntos individuales",
                        min_value=0.0,
                        max_value=float(sesion_actual.data['puntaje_maximo']),
                        value=float(punto.data['puntos_individual']),
                        step=0.5,
                        key=f"punto_{punto.data['id']}"
                    )
                    
                    if nuevo_individual + punto.data['puntos_grupal'] != puntos_actual['puntos']:
                        st.session_state.puntos_pendientes[punto.data['id']] = {
                            'puntos': nuevo_individual + punto.data['puntos_grupal']
                        }
                        st.session_state.ultimo_cambio = time.time()

# Barra inferior fija con estado y botón de guardar
st.markdown(
    """
    <style>
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 15px;
        z-index: 999;
        border-top: 1px solid #ddd;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# Footer con información y botón de guardar
st.markdown("---")
col1, col2 = st.columns([3,1])
with col1:
    if st.session_state.puntos_pendientes:
        tiempo_espera = max(5 - (time.time() - st.session_state.ultimo_cambio), 0)
        st.info(f"Hay {len(st.session_state.puntos_pendientes)} cambios pendientes de guardar. "
               f"Se guardarán automáticamente en {tiempo_espera:.1f} segundos.")
with col2:
    if st.session_state.puntos_pendientes:
        if st.button("💾 Guardar Ahora", key="guardar_manual", use_container_width=True):
            guardar_puntos()

# Guardado automático después de 5 segundos
if st.session_state.puntos_pendientes and \
   (time.time() - st.session_state.ultimo_cambio) >= 5:
    guardar_puntos()