# pages/4_gestionar_sesiones.py
import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date

# Configuración de la página
st.set_page_config(page_title="Gestión de Sesiones", page_icon="📅")

# Inicializar conexión con Supabase
@st.cache_resource
def init_connection():
    return create_client(
        st.secrets["supabase_url"],
        st.secrets["supabase_key"]
    )

supabase = init_connection()

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

# Título de la página y encabezado
st.title("📅 Gestión de Sesiones")
mostrar_encabezado()

def obtener_siguiente_numero_sesion():
    sesiones = supabase.table('sesiones')\
        .select('nombre')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .execute()
    
    if not sesiones.data:
        return 1
    
    numeros = []
    for sesion in sesiones.data:
        try:
            # Extraer número del nombre "Sesión X"
            num = int(sesion['nombre'].split(' ')[1])
            numeros.append(num)
        except:
            continue
    
    return max(numeros) + 1 if numeros else 1

# Crear nueva sesión
with st.form("nueva_sesion", clear_on_submit=True):
    st.subheader("Crear Nueva Sesión")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        siguiente_numero = obtener_siguiente_numero_sesion()
        nombre_sugerido = f"Sesión {siguiente_numero}"
        nombre = st.text_input("Nombre de la Sesión", 
                             value=nombre_sugerido,
                             help="Se asignará automáticamente si lo dejas vacío")
    with col2:
        fecha = st.date_input("Fecha", value=date.today())
    with col3:
        puntaje_maximo = st.number_input("Puntaje Máximo", 
                                       min_value=1.0, 
                                       max_value=100.0,
                                       value=20.0,
                                       step=0.5)
    
    submitted = st.form_submit_button("Crear Sesión", use_container_width=True)
    
    if submitted:
        try:
            # Validar que haya estudiantes en el curso
            estudiantes = supabase.table('estudiantes_curso')\
                .select('id')\
                .eq('curso_id', st.session_state['curso_actual'])\
                .execute()
            
            if not estudiantes.data:
                st.error("No hay estudiantes registrados en el curso")
            else:
                # Crear sesión
                nombre_final = nombre if nombre and nombre.strip() else nombre_sugerido
                sesion = supabase.table('sesiones').insert({
                    'curso_id': st.session_state['curso_actual'],
                    'nombre': nombre_final,
                    'fecha': fecha.isoformat(),
                    'puntaje_maximo': puntaje_maximo
                }).execute()
                
                sesion_id = sesion.data[0]['id']
                
                # Crear registros de puntos iniciales para todos los estudiantes
                for estudiante in estudiantes.data:
                    supabase.table('puntos_sesion').insert({
                        'sesion_id': sesion_id,
                        'estudiante_id': estudiante['id'],
                        'puntos': 0
                    }).execute()
                
                st.success(f"✅ Sesión '{nombre_final}' creada exitosamente")
                
                # Actualizar estado de sesión actual
                st.session_state.sesion_actual = sesion_id
                st.session_state.sesion_nombre = nombre_final
                
                st.rerun()
        except Exception as e:
            if 'unique_sesion_curso' in str(e):
                st.error("Ya existe una sesión con este nombre en el curso")
            else:
                st.error(f"Error al crear la sesión: {str(e)}")

# Ver sesiones existentes
st.markdown("---")
st.subheader("📋 Sesiones del Curso")

try:
    # Obtener sesiones ordenadas por fecha
    sesiones = supabase.table('sesiones')\
        .select('*')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .order('fecha', desc=True)\
        .execute()

    if sesiones.data:
        # Búsqueda y filtros
        col1, col2 = st.columns(2)
        with col1:
            busqueda = st.text_input("🔍 Buscar sesión", 
                                   placeholder="Nombre de la sesión")
        with col2:
            orden = st.selectbox("Ordenar por", 
                               ["Fecha ▼", "Fecha ▲", "Nombre", "Puntaje máximo"])
        
        sesiones_mostrar = sesiones.data
        if busqueda:
            sesiones_mostrar = [s for s in sesiones.data 
                              if busqueda.lower() in s['nombre'].lower()]
        
        # Ordenar según selección
        if orden == "Fecha ▲":
            sesiones_mostrar = sorted(sesiones_mostrar, key=lambda x: x['fecha'])
        elif orden == "Nombre":
            sesiones_mostrar = sorted(sesiones_mostrar, key=lambda x: x['nombre'])
        elif orden == "Puntaje máximo":
            sesiones_mostrar = sorted(sesiones_mostrar, key=lambda x: x['puntaje_maximo'])
        
        # Mostrar sesiones
        for sesion in sesiones_mostrar:
            with st.expander(
                f"📅 {sesion['nombre']} - {sesion['fecha']}", 
                expanded=sesion['id'] == st.session_state.get('sesion_actual')
            ):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Puntaje Máximo:** {sesion['puntaje_maximo']}")
                    
                    # Mostrar resumen de puntos de la sesión
                    puntos = supabase.table('puntos_sesion')\
                        .select('puntos')\
                        .eq('sesion_id', sesion['id'])\
                        .execute()
                    
                    if puntos.data:
                        puntos_df = pd.DataFrame(puntos.data)
                        st.write("**Estadísticas:**")
                        col_stats1, col_stats2, col_stats3 = st.columns(3)
                        with col_stats1:
                            st.metric("Promedio", f"{puntos_df['puntos'].mean():.2f}")
                        with col_stats2:
                            st.metric("Máximo", f"{puntos_df['puntos'].max():.2f}")
                        with col_stats3:
                            st.metric("Mínimo", f"{puntos_df['puntos'].min():.2f}")
                
                with col2:
                    # Botón para ir a asignar puntos
                    if st.button("✏️ Asignar Puntos", key=f"points_{sesion['id']}"):
                        st.session_state.sesion_actual = sesion['id']
                        st.session_state.sesion_nombre = sesion['nombre']
                        st.switch_page("pages/5_asignar_puntos.py")
                    
                    # Botón para eliminar sesión
                    if st.button("🗑️ Eliminar", key=f"del_{sesion['id']}", type="primary"):
                        if st.session_state.get('sesion_actual') == sesion['id']:
                            del st.session_state.sesion_actual
                            del st.session_state.sesion_nombre
                        
                        supabase.table('sesiones')\
                            .delete()\
                            .eq('id', sesion['id'])\
                            .execute()
                        st.success("Sesión eliminada exitosamente")
                        st.rerun()
    else:
        st.info("No hay sesiones creadas en este curso")

except Exception as e:
    st.error(f"Error al cargar las sesiones: {str(e)}")

# Resumen
st.markdown("---")
if sesiones.data:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sesiones", len(sesiones.data))
    with col2:
        promedios = []
        for sesion in sesiones.data:
            puntos = supabase.table('puntos_sesion')\
                .select('puntos')\
                .eq('sesion_id', sesion['id'])\
                .execute()
            if puntos.data:
                promedio = sum(p['puntos'] for p in puntos.data) / len(puntos.data)
                promedios.append(promedio)
        if promedios:
            st.metric("Promedio General", f"{sum(promedios)/len(promedios):.2f}")
    with col3:
        ultima_sesion = sorted(sesiones.data, key=lambda x: x['fecha'])[-1]
        st.metric("Última Sesión", ultima_sesion['fecha'])

# Información adicional
with st.expander("ℹ️ Ayuda"):
    st.markdown("""
    ### Gestión de Sesiones:
    - Los nombres se autogeneran secuencialmente
    - Cada sesión tiene un puntaje máximo configurable
    - Se inicializan los puntos en 0 para todos los estudiantes
    - Puedes ordenar y filtrar las sesiones
    
    ### Para asignar puntos:
    1. Crea una nueva sesión o selecciona una existente
    2. Usa el botón "Asignar Puntos" para ir a la página de asignación
    3. Puedes asignar puntos por grupo o individualmente
    """)