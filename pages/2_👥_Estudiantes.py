# pages/2_gestionar_estudiantes.py
import streamlit as st
import pandas as pd
from supabase import create_client

# Configuración de la página
st.set_page_config(page_title="Gestión de Estudiantes", page_icon="👥")

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
st.title("👥 Gestión de Estudiantes")
mostrar_encabezado()

def cargar_estudiantes_desde_archivo():
    uploaded_file = st.file_uploader(
        "Cargar lista de estudiantes (CSV)", 
        type=['csv'],
        help="El archivo debe contener las columnas: apellidos,nombres"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if 'apellidos' not in df.columns or 'nombres' not in df.columns:
                st.error("El archivo debe contener las columnas 'apellidos' y 'nombres'")
                return
            
            progress_bar = st.progress(0)
            estudiantes_agregados = 0
            errores = []
            total_estudiantes = len(df)
            
            for _, row in df.iterrows():
                try:
                    supabase.table('estudiantes_curso').insert({
                        'curso_id': st.session_state['curso_actual'],
                        'apellidos': row['apellidos'].strip(),
                        'nombres': row['nombres'].strip()
                    }).execute()
                    estudiantes_agregados += 1
                except Exception as e:
                    if 'duplicate key' in str(e):
                        errores.append(f"{row['apellidos']}, {row['nombres']} (ya existe)")
                    else:
                        errores.append(f"{row['apellidos']}, {row['nombres']} (error: {str(e)})")
                progress_bar.progress(estudiantes_agregados / total_estudiantes)
            
            if estudiantes_agregados > 0:
                st.success(f"✅ {estudiantes_agregados} estudiantes agregados exitosamente")
            if errores:
                with st.expander(f"⚠️ {len(errores)} errores encontrados"):
                    for error in errores:
                        st.write(error)
            st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")

def agregar_estudiante_manual():
    with st.form("nuevo_estudiante", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            apellidos = st.text_input("Apellidos")
        with col2:
            nombres = st.text_input("Nombres")
        
        submitted = st.form_submit_button("Agregar Estudiante", use_container_width=True)
        
        if submitted:
            if not apellidos or not nombres:
                st.error("Apellidos y nombres son requeridos")
            else:
                try:
                    supabase.table('estudiantes_curso').insert({
                        'curso_id': st.session_state['curso_actual'],
                        'apellidos': apellidos.strip(),
                        'nombres': nombres.strip()
                    }).execute()
                    st.success(f"✅ Estudiante {apellidos}, {nombres} agregado exitosamente")
                    st.rerun()
                except Exception as e:
                    if 'duplicate key' in str(e):
                        st.error("Este estudiante ya existe en el curso")
                    else:
                        st.error(f"Error al agregar estudiante: {str(e)}")

# Tabs para diferentes funciones
tab1, tab2 = st.tabs(["📤 Cargar desde archivo", "✍️ Agregar manualmente"])

with tab1:
    cargar_estudiantes_desde_archivo()
    
with tab2:
    agregar_estudiante_manual()

# Ver lista de estudiantes
st.markdown("---")
st.subheader("📋 Lista de Estudiantes")

try:
    # Obtener estudiantes del curso actual
    estudiantes = supabase.table('estudiantes_curso')\
        .select('*')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .order('apellidos')\
        .execute()

    if estudiantes.data:
        # Container para mejorar la presentación
        with st.container():
            # Barra de búsqueda
            busqueda = st.text_input("🔍 Buscar estudiante", 
                                   placeholder="Ingresa apellido o nombre")
            
            estudiantes_mostrar = estudiantes.data
            if busqueda:
                busqueda = busqueda.lower()
                estudiantes_mostrar = [
                    e for e in estudiantes.data
                    if busqueda in e['apellidos'].lower() or 
                       busqueda in e['nombres'].lower()
                ]
            
            if not estudiantes_mostrar:
                st.info("No se encontraron estudiantes")
            
            # Mostrar estudiantes en una lista con acciones
            for estudiante in estudiantes_mostrar:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{estudiante['apellidos']}**")
                with col2:
                    st.write(estudiante['nombres'])
                with col3:
                    if st.button("🗑️", key=f"del_{estudiante['id']}", 
                               help="Eliminar estudiante"):
                        try:
                            supabase.table('estudiantes_curso')\
                                .delete()\
                                .eq('id', estudiante['id'])\
                                .execute()
                            st.success("Estudiante eliminado del curso")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar estudiante: {str(e)}")
    else:
        st.info("No hay estudiantes registrados en este curso")
        st.button("📤 Cargar estudiantes", on_click=lambda: st.set_page_config(initial_sidebar_state="expanded"))

except Exception as e:
    st.error(f"Error al cargar la lista de estudiantes: {str(e)}")

# Información adicional
with st.expander("ℹ️ Información"):
    st.markdown("""
    ### Cómo agregar estudiantes:
    1. **Carga masiva**: Usa un archivo CSV con las columnas 'apellidos' y 'nombres'
    2. **Agregar manual**: Ingresa los datos de cada estudiante individualmente
    
    ### Formato del archivo CSV:
    ```
    apellidos,nombres
    Pérez García,Juan
    Martínez López,María
    ```
    
    ### Notas importantes:
    - Los nombres y apellidos se limpian automáticamente de espacios extra
    - No se permiten estudiantes duplicados en el mismo curso
    - Al eliminar un estudiante, se eliminan sus registros de puntos
    """)

# Resumen al final de la página
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.metric("Total de estudiantes", len(estudiantes.data) if estudiantes.data else 0)
with col2:
    grupos = supabase.table('grupos')\
        .select('id')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .execute()
    st.metric("Grupos en el curso", len(grupos.data) if grupos.data else 0)