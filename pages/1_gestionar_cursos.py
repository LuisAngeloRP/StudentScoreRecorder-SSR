# pages/1_gestionar_cursos.py
import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Gestión de Cursos", page_icon="📚")

# Inicializar conexión con Supabase
@st.cache_resource
def init_connection():
    return create_client(
        st.secrets["supabase_url"],
        st.secrets["supabase_key"]
    )

supabase = init_connection()

# Título de la página
st.title("📚 Gestión de Cursos")

# Función para cargar cursos
def cargar_cursos():
    try:
        response = supabase.table('cursos')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()
        return response.data
    except Exception as e:
        st.error(f"Error al cargar cursos: {str(e)}")
        return []

# Crear nuevo curso
with st.form("nuevo_curso", clear_on_submit=True):
    st.subheader("Crear Nuevo Curso")
    nombre = st.text_input("Nombre del Curso")
    submitted = st.form_submit_button("Crear Curso", use_container_width=True)
    
    if submitted:
        if not nombre:
            st.error("El nombre del curso es obligatorio")
        else:
            try:
                nuevo_curso = supabase.table('cursos').insert({'nombre': nombre}).execute()
                st.success(f"Curso '{nombre}' creado exitosamente")
                
                # Seleccionar automáticamente el nuevo curso
                curso_id = nuevo_curso.data[0]['id']
                st.session_state.curso_actual = curso_id
                st.session_state.curso_nombre = nombre
                
                st.rerun()
            except Exception as e:
                if 'duplicate key' in str(e):
                    st.error("Ya existe un curso con este nombre")
                else:
                    st.error(f"Error al crear el curso: {str(e)}")

# Mostrar curso actualmente seleccionado
if 'curso_actual' in st.session_state:
    st.info(f"✅ Curso actualmente seleccionado: {st.session_state.get('curso_nombre', 'Ninguno')}")

# Separador
st.markdown("---")

# Seleccionar y gestionar cursos existentes
st.subheader("Cursos Existentes")

# Cargar cursos existentes
cursos = cargar_cursos()

if not cursos:
    st.info("No hay cursos creados. Crea un nuevo curso usando el formulario de arriba.")
else:
    # Mostrar cursos en cards con acciones
    for curso in cursos:
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                if curso['id'] == st.session_state.get('curso_actual'):
                    st.markdown(f"### 📌 {curso['nombre']}")
                else:
                    st.markdown(f"### 📚 {curso['nombre']}")
                st.write(f"Creado: {datetime.fromisoformat(curso['created_at']).strftime('%Y-%m-%d')}")
                
                # Mostrar estadísticas del curso
                estudiantes = supabase.table('estudiantes_curso')\
                    .select('id')\
                    .eq('curso_id', curso['id'])\
                    .execute()
                
                grupos = supabase.table('grupos')\
                    .select('id')\
                    .eq('curso_id', curso['id'])\
                    .execute()
                
                sesiones = supabase.table('sesiones')\
                    .select('id')\
                    .eq('curso_id', curso['id'])\
                    .execute()
                
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                with col_stats1:
                    st.write(f"📊 {len(estudiantes.data)} estudiantes")
                with col_stats2:
                    st.write(f"👥 {len(grupos.data)} grupos")
                with col_stats3:
                    st.write(f"📅 {len(sesiones.data)} sesiones")
            
            with col2:
                # Botones de acción
                if curso['id'] != st.session_state.get('curso_actual'):
                    if st.button("📌 Seleccionar", key=f"select_{curso['id']}"):
                        st.session_state.curso_actual = curso['id']
                        st.session_state.curso_nombre = curso['nombre']
                        # Limpiar selección de sesión si existe
                        if 'sesion_actual' in st.session_state:
                            del st.session_state.sesion_actual
                            del st.session_state.sesion_nombre
                        st.rerun()
                
                if st.button("🗑️ Eliminar", key=f"delete_{curso['id']}", type="secondary"):
                    if st.session_state.get('curso_actual') == curso['id']:
                        st.error("No se puede eliminar el curso activo")
                    else:
                        try:
                            supabase.table('cursos').delete().eq('id', curso['id']).execute()
                            st.success(f"Curso eliminado exitosamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar el curso: {str(e)}")
            
            st.markdown("---")

# Información adicional
with st.expander("ℹ️ Ayuda"):
    st.markdown("""
    ### Gestión de Cursos:
    1. **Crear Curso**: Ingresa el nombre y haz clic en 'Crear Curso'
    2. **Seleccionar Curso**: Usa el botón 'Seleccionar' para activar un curso
    3. **Eliminar Curso**: Solo puedes eliminar cursos que no estén activos
    
    ### Notas:
    - El curso seleccionado se mantiene activo en todas las páginas
    - Al cambiar de curso, se limpia la selección de sesión
    - Los nombres de curso deben ser únicos
    """)