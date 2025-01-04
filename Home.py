# Home.py
import streamlit as st
import pandas as pd
from supabase import create_client
import time
from datetime import datetime, date
import xlsxwriter

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Puntos", 
    page_icon="🎯", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar puntos: {str(e)}")

# Título principal
st.title("🎯 Sistema de Puntos")

# Sección de Selección Rápida
with st.container():
    # Selector de Curso
    cursos = supabase.table('cursos').select('*').execute()
    if cursos.data:
        col1, col2, col3 = st.columns([2,2,1])
        
        with col1:
            curso_actual = st.selectbox(
                "Seleccionar Curso",
                options=[c['id'] for c in cursos.data],
                format_func=lambda x: next(c['nombre'] for c in cursos.data if c['id'] == x),
                index=next((i for i, c in enumerate(cursos.data) 
                          if c['id'] == st.session_state.get('curso_actual', None)), 0)
            )
            
            if curso_actual != st.session_state.get('curso_actual'):
                st.session_state.curso_actual = curso_actual
                st.session_state.curso_nombre = next(c['nombre'] for c in cursos.data if c['id'] == curso_actual)
                if 'sesion_actual' in st.session_state:
                    del st.session_state.sesion_actual
                st.rerun()
        
        with col2:
            if 'curso_actual' in st.session_state:
                sesiones = supabase.table('sesiones')\
                    .select('*')\
                    .eq('curso_id', st.session_state['curso_actual'])\
                    .order('fecha', desc=True)\
                    .execute()
                
                if sesiones.data:
                    sesion_actual = st.selectbox(
                        "Seleccionar Sesión",
                        options=[s['id'] for s in sesiones.data],
                        format_func=lambda x: next(s['nombre'] + f" ({s['fecha']})" 
                                                 for s in sesiones.data if s['id'] == x),
                        index=next((i for i, s in enumerate(sesiones.data) 
                                  if s['id'] == st.session_state.get('sesion_actual', None)), 0)
                    )
                    
                    if sesion_actual != st.session_state.get('sesion_actual'):
                        st.session_state.sesion_actual = sesion_actual
                        st.session_state.sesion_nombre = next(s['nombre'] for s in sesiones.data if s['id'] == sesion_actual)
                        st.rerun()
                else:
                    st.warning("No hay sesiones en este curso")
        
        with col3:
            # Botones de acción
            if st.button("➕ Nueva Sesión", use_container_width=True):
                st.switch_page("pages/4_gestionar_sesiones.py")
            
            if 'sesion_actual' in st.session_state:
                if st.button("📥 Descargar Sesión", use_container_width=True):
                    with st.spinner("Descargando datos..."):
                        # Obtener todos los estudiantes del curso
                        estudiantes = supabase.table('estudiantes_curso')\
                            .select('*')\
                            .eq('curso_id', st.session_state['curso_actual'])\
                            .order('apellidos')\
                            .execute()
                        
                        # Obtener puntos individuales
                        puntos_ind = supabase.table('puntos_individuales')\
                            .select('*')\
                            .eq('sesion_id', st.session_state.sesion_actual)\
                            .execute()
                            
                        # Obtener puntos grupales
                        puntos_grupales = supabase.table('puntos_grupales')\
                            .select('*, grupos!inner(nombre)')\
                            .eq('sesion_id', st.session_state.sesion_actual)\
                            .execute()
                            
                        # Crear diccionario de puntos grupales por grupo
                        grupos_dict = {pg['grupo_id']: {'puntos': pg['puntos'], 'nombre': pg['grupos']['nombre']} 
                                     for pg in puntos_grupales.data}
                            
                        # Obtener membresía de grupos
                        estudiantes_grupos = supabase.table('estudiantes_grupo')\
                            .select('*')\
                            .execute()
                            
                        # Crear diccionario de grupos por estudiante
                        grupos_por_estudiante = {}
                        for eg in estudiantes_grupos.data:
                            if eg['estudiante_id'] not in grupos_por_estudiante:
                                grupos_por_estudiante[eg['estudiante_id']] = []
                            if eg['grupo_id'] in grupos_dict:
                                grupos_por_estudiante[eg['estudiante_id']].append(grupos_dict[eg['grupo_id']])
                        
                        # Crear diccionario de puntos individuales
                        puntos_dict = {p['estudiante_id']: p['puntos'] for p in puntos_ind.data}
                        
                        # Preparar datos para Excel
                        excel_data = []
                        for est in estudiantes.data:
                            puntos_individuales = puntos_dict.get(est['id'], 0)
                            grupos_est = grupos_por_estudiante.get(est['id'], [])
                            puntos_grupales = sum(g['puntos'] for g in grupos_est)
                            grupos_nombres = ', '.join(g['nombre'] for g in grupos_est)
                            
                            excel_data.append({
                                'Apellidos': est['apellidos'],
                                'Nombres': est['nombres'],
                                'Grupos': grupos_nombres,
                                'Puntos Individuales': puntos_individuales,
                                'Puntos Grupales': puntos_grupales,
                                'Total': puntos_individuales + puntos_grupales
                                
                            })
                        
                        # Crear DataFrame y exportar a Excel
                        df = pd.DataFrame(excel_data)
                        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nombre_archivo = f"sesion_{st.session_state.sesion_nombre.replace(' ', '_')}_{fecha_actual}.xlsx"
                        
                        # Configurar el writer de Excel
                        buffer = pd.ExcelWriter(nombre_archivo, engine='xlsxwriter')
                        df.to_excel(buffer, index=False, sheet_name='Puntos')
                        
                        # Ajustar ancho de columnas
                        worksheet = buffer.sheets['Puntos']
                        for idx, col in enumerate(df.columns):
                            max_length = max(df[col].astype(str).apply(len).max(),
                                          len(col)) + 2
                            worksheet.set_column(idx, idx, max_length)
                        
                        buffer.close()
                        
                        # Leer el archivo y prepararlo para descarga
                        with open(nombre_archivo, 'rb') as f:
                            bytes_data = f.read()
                        
                        st.download_button(
                            label="📥 Descargar Excel",
                            data=bytes_data,
                            file_name=nombre_archivo,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

# Mostrar información actual si hay curso y sesión seleccionados
if 'curso_actual' in st.session_state and 'sesion_actual' in st.session_state:
    st.divider()
    
    # Obtener información de la sesión actual
    sesion = supabase.table('sesiones')\
        .select('*')\
        .eq('id', st.session_state.sesion_actual)\
        .execute()
    
    if sesion.data:
        # Mostrar información resumida
        col1, col2, col3 = st.columns([2,2,1])
        with col1:
            st.info(f"📚 Curso: {st.session_state.curso_nombre}")
        with col2:
            st.info(f"📅 Sesión: {st.session_state.sesion_nombre}")
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
                # Layout en grid de 3 columnas para los grupos
                cols = st.columns(3)
                for idx, grupo in enumerate(grupos.data):
                    with cols[idx % 3]:
                        with st.container():
                            st.subheader(f"👥 {grupo['nombre']}", divider="blue")
                            
                            # Obtener puntos grupales
                            puntos_grupales = supabase.table('puntos_grupales')\
                                .select('*')\
                                .eq('sesion_id', st.session_state.sesion_actual)\
                                .eq('grupo_id', grupo['id'])\
                                .execute()

                            if not puntos_grupales.data:
                                puntos_grupales = supabase.table('puntos_grupales').insert({
                                    'sesion_id': st.session_state.sesion_actual,
                                    'grupo_id': grupo['id'],
                                    'puntos': 0
                                }).execute()

                            punto_grupal = puntos_grupales.data[0]
                            
                            # Input de puntos grupales
                            nuevo_puntaje = st.number_input(
                                "Puntos grupales",
                                min_value=0.0,
                                max_value=float(sesion.data[0]['puntaje_maximo']),
                                value=float(punto_grupal['puntos']),
                                step=0.5,
                                key=f"grupo_{grupo['id']}"
                            )
                            
                            if nuevo_puntaje != punto_grupal['puntos']:
                                st.session_state.puntos_grupales_pendientes[punto_grupal['id']] = nuevo_puntaje
                                st.session_state.ultimo_cambio = time.time()
                            
                            # Mostrar estudiantes del grupo
                            estudiantes_grupo = supabase.table('estudiantes_grupo')\
                                .select('estudiante_id, estudiantes_curso!inner(*)')\
                                .eq('grupo_id', grupo['id'])\
                                .execute()

                            if estudiantes_grupo.data:
                                for estudiante in estudiantes_grupo.data:
                                    est = estudiante['estudiantes_curso']
                                    st.write(f"- {est['apellidos']}, {est['nombres']}")
            else:
                st.info("No hay grupos creados en este curso")

        # Vista Individual
        with tab2:
            busqueda = st.text_input("🔍 Buscar estudiante", "")
            
            estudiantes = supabase.table('estudiantes_curso')\
                .select('*')\
                .eq('curso_id', st.session_state['curso_actual'])\
                .order('apellidos')\
                .execute()

            if estudiantes.data:
                estudiantes_filtrados = estudiantes.data
                if busqueda:
                    busqueda = busqueda.lower()
                    estudiantes_filtrados = [
                        est for est in estudiantes.data
                        if busqueda in f"{est['nombres']} {est['apellidos']}".lower()
                    ]

                # Layout en grid de 3 columnas para estudiantes
                cols = st.columns(3)
                for idx, estudiante in enumerate(estudiantes_filtrados):
                    with cols[idx % 3]:
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
                        puntos_actuales = st.session_state.puntos_individuales_pendientes.get(
                            punto_individual['id'], punto_individual['puntos']
                        )

                        # Nombre con color rojo si tiene 0 puntos
                        nombre_estudiante = f"{estudiante['apellidos']}, {estudiante['nombres']}"
                        if puntos_actuales == 0:
                            nombre_estudiante = f":red[{nombre_estudiante}]"

                        nuevo_puntaje = st.number_input(
                            f"**{nombre_estudiante}**",
                            min_value=0.0,
                            max_value=float(sesion.data[0]['puntaje_maximo']),
                            value=float(puntos_actuales),
                            step=0.5,
                            key=f"ind_{estudiante['id']}"
                        )

                        if nuevo_puntaje != puntos_actuales:
                            st.session_state.puntos_individuales_pendientes[punto_individual['id']] = nuevo_puntaje
                            st.session_state.ultimo_cambio = time.time()
            else:
                st.info("No hay estudiantes en este curso")

        # Barra de estado y guardado
        st.divider()
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

        # Guardado automático
        if cambios_pendientes > 0 and (time.time() - st.session_state.ultimo_cambio) >= 5:
            guardar_puntos()
else:
    st.warning("👆 Selecciona un curso y una sesión para comenzar")