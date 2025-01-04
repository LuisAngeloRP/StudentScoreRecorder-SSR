# pages/3_gestionar_grupos.py
import streamlit as st
import pandas as pd
from supabase import create_client

# Configuración de la página
st.set_page_config(page_title="Gestión de Grupos", page_icon="👥")

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
        st.page_link("pages/1_📚_Mis_Cursos.py", label="Ir a Gestión de Cursos")
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
st.title("👥 Gestión de Grupos")
mostrar_encabezado()

def obtener_siguiente_numero_grupo():
    grupos = supabase.table('grupos')\
        .select('nombre')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .execute()
    
    if not grupos.data:
        return 1
    
    numeros = []
    for grupo in grupos.data:
        try:
            # Extraer número del nombre "Grupo X"
            num = int(grupo['nombre'].split(' ')[1])
            numeros.append(num)
        except:
            continue
    
    return max(numeros) + 1 if numeros else 1

def obtener_estudiantes_sin_grupo():
    try:
        # Obtener todos los estudiantes del curso que no están en ningún grupo
        query = f"""
        SELECT e.* 
        FROM estudiantes_curso e
        LEFT JOIN estudiantes_grupo g ON e.id = g.estudiante_id
        WHERE e.curso_id = {st.session_state['curso_actual']}
        AND g.estudiante_id IS NULL
        ORDER BY e.apellidos, e.nombres
        """
        response = supabase.table('estudiantes_curso').select("*").execute()
        estudiantes = response.data
        
        if not estudiantes:
            return []
        
        estudiantes_en_grupos = supabase.table('estudiantes_grupo')\
            .select('estudiante_id')\
            .execute()
        
        ids_en_grupos = [e['estudiante_id'] for e in estudiantes_en_grupos.data] if estudiantes_en_grupos.data else []
        
        return [e for e in estudiantes if e['id'] not in ids_en_grupos]
    
    except Exception as e:
        st.error(f"Error al obtener estudiantes: {str(e)}")
        return []

# Crear nuevo grupo
with st.form("nuevo_grupo", clear_on_submit=True):
    st.subheader("Crear Nuevo Grupo")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        siguiente_numero = obtener_siguiente_numero_grupo()
        nombre_sugerido = f"Grupo {siguiente_numero}"
        nombre = st.text_input("Nombre del Grupo", 
                             value=nombre_sugerido,
                             help="Se asignará automáticamente si lo dejas vacío")
    with col2:
        es_grupo_especial = st.checkbox("Grupo Especial", 
                                      help="Permite agregar estudiantes que ya están en otros grupos")
    
    # Obtener estudiantes disponibles
    if es_grupo_especial:
        estudiantes = supabase.table('estudiantes_curso')\
            .select('*')\
            .eq('curso_id', st.session_state['curso_actual'])\
            .order('apellidos')\
            .execute().data
    else:
        estudiantes = obtener_estudiantes_sin_grupo()
    
    if estudiantes:
        estudiantes_opciones = [
            f"{e['apellidos']}, {e['nombres']}" for e in estudiantes
        ]
        estudiantes_seleccionados = st.multiselect(
            "Seleccionar Estudiantes",
            options=estudiantes_opciones,
            help="Selecciona los estudiantes que formarán parte del grupo"
        )
    else:
        if es_grupo_especial:
            st.warning("No hay estudiantes en el curso")
        else:
            st.warning("No hay estudiantes disponibles (todos están en grupos)")
        estudiantes_seleccionados = []
    
    submitted = st.form_submit_button("Crear Grupo", use_container_width=True)
    
    if submitted:
        if not estudiantes_seleccionados:
            st.error("Debes seleccionar al menos un estudiante")
        else:
            try:
                # Crear grupo
                grupo = supabase.table('grupos').insert({
                    'curso_id': st.session_state['curso_actual'],
                    'nombre': nombre if nombre and nombre.strip() else nombre_sugerido
                }).execute()
                
                grupo_id = grupo.data[0]['id']
                
                # Asociar estudiantes al grupo
                for estudiante_nombre in estudiantes_seleccionados:
                    apellidos = estudiante_nombre.split(',')[0]
                    estudiante = next(
                        e for e in estudiantes 
                        if e['apellidos'] == apellidos
                    )
                    
                    supabase.table('estudiantes_grupo').insert({
                        'grupo_id': grupo_id,
                        'estudiante_id': estudiante['id']
                    }).execute()
                
                st.success(f"✅ Grupo creado exitosamente")
                st.rerun()
            except Exception as e:
                if 'unique_grupo_curso' in str(e):
                    st.error("Ya existe un grupo con este nombre en el curso")
                else:
                    st.error(f"Error al crear el grupo: {str(e)}")

# Ver grupos existentes
st.markdown("---")
st.subheader("📋 Grupos Existentes")

try:
    # Obtener grupos del curso
    grupos = supabase.table('grupos')\
        .select('*')\
        .eq('curso_id', st.session_state['curso_actual'])\
        .order('nombre')\
        .execute()

    if grupos.data:
        # Búsqueda de grupos
        busqueda = st.text_input("🔍 Buscar grupo", placeholder="Nombre del grupo")
        
        grupos_mostrar = grupos.data
        if busqueda:
            grupos_mostrar = [g for g in grupos.data if busqueda.lower() in g['nombre'].lower()]
        
        # Mostrar grupos
        for grupo in grupos_mostrar:
            with st.expander(f"👥 {grupo['nombre']}", expanded=True):
                # Obtener miembros del grupo
                miembros = supabase.table('estudiantes_grupo')\
                    .select('*, estudiantes_curso!inner(*)')\
                    .eq('grupo_id', grupo['id'])\
                    .execute()
                
                if miembros.data:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write("**Integrantes:**")
                        for m in miembros.data:
                            est = m['estudiantes_curso']
                            col_est1, col_est2 = st.columns([4, 1])
                            with col_est1:
                                st.write(f"- {est['apellidos']}, {est['nombres']}")
                            with col_est2:
                                if st.button("❌", key=f"del_est_{m['id']}", 
                                           help="Quitar del grupo"):
                                    supabase.table('estudiantes_grupo')\
                                        .delete()\
                                        .eq('id', m['id'])\
                                        .execute()
                                    st.success("Estudiante removido del grupo")
                                    st.rerun()
                    
                    with col2:
                        if st.button("🗑️ Eliminar Grupo", key=f"del_grupo_{grupo['id']}",
                                   help="Eliminar grupo completo"):
                            supabase.table('grupos')\
                                .delete()\
                                .eq('id', grupo['id'])\
                                .execute()
                            st.success("Grupo eliminado exitosamente")
                            st.rerun()
    else:
        st.info("No hay grupos creados en este curso")

except Exception as e:
    st.error(f"Error al cargar los grupos: {str(e)}")

# Resumen
st.markdown("---")
col1, col2, col3 = st.columns(3)

estudiantes_total = supabase.table('estudiantes_curso')\
    .select('id')\
    .eq('curso_id', st.session_state['curso_actual'])\
    .execute()

estudiantes_en_grupos = supabase.table('estudiantes_grupo')\
    .select('estudiante_id')\
    .execute()

with col1:
    st.metric("Total Grupos", len(grupos.data) if grupos.data else 0)
with col2:
    st.metric("Total Estudiantes", len(estudiantes_total.data) if estudiantes_total.data else 0)
with col3:
    estudiantes_unicos = len(set(e['estudiante_id'] for e in estudiantes_en_grupos.data)) if estudiantes_en_grupos.data else 0
    st.metric("En Grupos", estudiantes_unicos)

# Información adicional
with st.expander("ℹ️ Ayuda"):
    st.markdown("""
    ### Tipos de Grupos:
    1. **Grupos Normales**: Los estudiantes solo pueden estar en un grupo
    2. **Grupos Especiales**: Permiten estudiantes que ya están en otros grupos
    
    ### Notas importantes:
    - Los nombres de grupo se autogeneran si no se especifican
    - Puedes quitar estudiantes individualmente o eliminar grupos completos
    - Al eliminar un grupo, los estudiantes quedan disponibles para otros grupos
    """)