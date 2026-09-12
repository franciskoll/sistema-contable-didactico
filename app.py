if archivo_cargado is not None:
    try:
        datos_recuperados = json.load(archivo_cargado)
        
        for renglon in datos_recuperados.get("libro_diario", []):
            if isinstance(renglon.get("Fecha"), str):
                renglon["Fecha"] = datetime.date.fromisoformat(renglon["Fecha"])
                
        for clave, movs in datos_recuperados.get("submayores", {}).items():
            if isinstance(movs, list):
                for m in movs:
                    if isinstance(m.get("Fecha"), str):
                        m["Fecha"] = datetime.date.fromisoformat(m["Fecha"])
            elif isinstance(movs, dict):
                for art, registros in movs.items():
                    for r in registros:
                        if isinstance(r.get("Fecha"), str):
                            r["Fecha"] = datetime.date.fromisoformat(r["Fecha"])

        # Restauración de datos con protección de catálogo
        st.session_state.alumno_nombre = datos_recuperados.get("alumno_nombre", st.session_state.alumno_nombre)
        st.session_state.alumno_curso = datos_recuperados.get("alumno_curso", st.session_state.alumno_curso)
        st.session_state.plan_cuentas = datos_recuperados.get("plan_cuentas", st.session_state.plan_cuentas)
        st.session_state.padron_terceros = datos_recuperados.get("padron_terceros", [])
        
        # Si el JSON trae artículos los carga; si es una versión vieja, conserva los actuales o inicializa en lista
        articulos_recuperados = datos_recuperados.get("padron_articulos", st.session_state.padron_articulos)
        st.session_state.padron_articulos = articulos_recuperados if articulos_recuperados else []
        
        st.session_state.libro_diario = datos_recuperados.get("libro_diario", [])
        st.session_state.submayores = datos_recuperados.get("submayores", st.session_state.submayores)
        
        st.sidebar.success("¡Avance cargado con éxito!")
    except Exception as e:
        st.sidebar.error("Error al leer el archivo JSON.")
