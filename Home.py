# Home.py
import streamlit as st
from supabase import create_client

# Configuración inicial de la página
st.set_page_config(
    page_title="Sistema de Puntos",
    page_icon="✏️",
    layout="wide"
)

# Inicializar conexión con Supabase
@st.cache_resource
def init_connection():
    return create_client(
        st.secrets["supabase_url"],
        st.secrets["supabase_key"]
    )

# Crear conexión a Supabase
supabase = init_connection()

# Obtener curso actual
def mostrar_curso_actual():
    if 'curso_actual' in st.session_state:
        curso = supabase.table('cursos')\
            .select('*')\
            .eq('id', st.session_state.curso_actual)\
            .single()\
            .execute()
        
        if curso.data:
            st.sidebar.success(f"✅ Curso actual: {curso.data['nombre']}")
            if st.sidebar.button("🔄 Cambiar Curso"):
                del st.session_state.curso_actual
                del st.session_state.curso_nombre
                if 'sesion_actual' in st.session_state:
                    del st.session_state.sesion_actual
                    del st.session_state.sesion_nombre
                st.rerun()
        else:
            del st.session_state.curso_actual
            del st.session_state.curso_nombre
    else:
        st.sidebar.warning("⚠️ No hay curso seleccionado")

# Título y descripción principal
st.title("✏️ Sistema de Anotación de Puntos")

# Mostrar curso actual en el sidebar
mostrar_curso_actual()

# Contenido principal
st.markdown("""
### Bienvenido al Sistema de Anotación de Puntos

Este sistema te permite:
- Gestionar cursos y sus estudiantes
- Crear y administrar grupos por curso
- Asignar puntos en sesiones
           
Utiliza el menú lateral para navegar entre las diferentes funciones:

1. 📚 Gestión de Cursos
   - Crear nuevos cursos
   - Seleccionar el curso activo

2. 👥 Gestión de Estudiantes
   - Cargar lista de estudiantes desde archivo CSV
   - Agregar estudiantes manualmente
   - Ver lista de estudiantes del curso

3. 👥 Gestión de Grupos
   - Crear grupos de trabajo
   - Asignar estudiantes a grupos
   - Ver grupos existentes

4. 📅 Gestión de Sesiones
   - Crear sesiones de clase
   - Definir puntaje máximo
   - Ver historial de sesiones

5. 🎯 Asignación de Puntos
   - Asignar puntos por grupo o individual
   - Ver puntos en tiempo real
   - Gestionar múltiples estudiantes

6. 📊 Reportes y Estadísticas
   - Ver resumen por estudiante
   - Ver resumen por grupo
   - Visualizar distribución de puntos
""")

# Información del sistema
with st.expander("ℹ️ Información del Sistema"):
    st.markdown("""
    ### Guía Rápida
    
    1. Primero, crea o selecciona un curso en la página de **Gestión de Cursos**
    2. Agrega estudiantes al curso desde **Gestión de Estudiantes**
    3. Opcionalmente, crea grupos en **Gestión de Grupos**
    4. Crea una sesión desde **Gestión de Sesiones**
    5. Asigna puntos desde **Asignación de Puntos**
    6. Consulta el progreso en **Reportes y Estadísticas**
    
    ### Funciones Principales
    
    - **Carga masiva**: Puedes cargar estudiantes desde un archivo CSV
    - **Grupos**: Crea grupos para trabajo colaborativo
    - **Puntos**: Asigna puntos por sesión a estudiantes o grupos completos
    - **Reportes**: Visualiza el progreso y estadísticas
    
    ### Formato del archivo CSV
    
    El archivo CSV para cargar estudiantes debe contener las siguientes columnas:
    - `apellidos`
    - `nombres`
    
    Ejemplo:
    ```
    apellidos,nombres
    Pérez,Juan
    García,María
    ```
    """)

# Caché y estado global
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    # Aquí puedes inicializar otros estados globales si es necesario

# Footer
st.markdown("---")
st.markdown("Sistema de Anotación de Puntos - v2.0")    