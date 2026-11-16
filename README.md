# FUTGOOL PLAYER — NEXORA TECH

Proyecto académico de aplicación web para fútbol amateur. Funciona en Visual Studio Code con Python, Flask y SQLite.

## Cómo ejecutar en Windows

1. Instala Python 3.11 o superior y Visual Studio Code.
2. Abre esta carpeta en Visual Studio Code: **Archivo > Abrir carpeta**.
3. Abre la terminal integrada (**Terminal > Nueva terminal**).
4. Ejecuta los comandos:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Si PowerShell impide activar el entorno, usa directamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

5. Entra en el navegador a **http://127.0.0.1:5000**.

El archivo `futgool.db` se crea automáticamente en el primer inicio.

## Prueba rápida

1. Registra dos cuentas con correos distintos.
2. Ingresa con la primera y crea un partido.
3. Sal de la sesión, ingresa con la segunda cuenta e inscríbete.
4. Vuelve a la primera cuenta, entra al partido y registra un gol o asistencia.
5. Abre el ranking para ver las estadísticas.
6. Evalúa a otro jugador desde la ficha del partido y publica en Comunidad.

## Qué está implementado

- Registro e inicio de sesión con contraseñas cifradas mediante hash.
- Crear partidos con fecha, lugar y capacidad.
- Inscribirse y retirarse de partidos.
- Registrar goles, asistencias y tarjetas (creador del partido o árbitro/admin).
- Evaluar jugadores inscritos (de 1 a 5 estrellas) y comentar.
- Ranking acumulado de goles, asistencias y promedio de evaluaciones.
- Publicaciones en comunidad.
- Roles definidos en base de datos: jugador, árbitro y administrador. Todos los nuevos usuarios se crean como jugador.

## Pendiente para una versión más avanzada

- Panel específico de administración y árbitros, asignación de roles.
- Gestión de torneos, clanes y registro de equipos con QR.
- Recuperación de contraseñas, confirmación de correo, moderación y notificaciones.
- Protección CSRF, limitación de intentos de inicio de sesión, cookies HTTPS, copias de seguridad y despliegue seguro.

## Importante

Este proyecto es un **prototipo académico local**, no un sitio listo para publicar en Internet. `debug=True` y la clave de desarrollo son solo para uso local. Para producción, configura una `SECRET_KEY` aleatoria, desactiva debug y agrega las protecciones de seguridad faltantes.


## Chatbot NEXOBOT (nuevo)
- Se abre con el botón flotante **⚽ ¿Necesitas ayuda?** en cualquier página.
- Responde preguntas frecuentes sobre cuentas, partidos, inscripciones, estadísticas, ranking y comunidad.
- Es un **chatbot local de respuestas guiadas**: no requiere claves de API ni conexión a servicios de IA.
- Backend: `POST /api/chatbot` (JSON `{"message":"¿Cómo creo un partido?"}`); frontend: `static/chatbot.js`.
- Para actualizar tu proyecto anterior, copia `app.py`, `templates/base.html`, `static/style.css` y `static/chatbot.js` desde este ZIP a las mismas rutas de tu proyecto. **No borres `futgool.db`** si ya tienes usuarios o partidos guardados.


## NEXOBOT y reservas de canchas

- Preguntas seleccionables en el chat y botón «Hablar con un agente» que abre WhatsApp.
- «Ver horarios y reservar cancha» permite elegir una fecha y consultar disponibilidad REAL guardada en SQLite.
- Hay 14 canchas por cada franja horaria de una hora: 13:00–14:00 hasta 21:00–22:00.
- Las reservas requieren sesión iniciada; se asigna automáticamente la primera cancha libre.
- Las reservas se guardan en la tabla `court_bookings` de `futgool.db`.
- Los ejemplos de 12 ocupadas o 0 disponibles NO se simulan: las cifras cambian solo con reservas registradas.
- Esta versión no incluye pagos, cancelaciones ni un panel de administración de reservas.
- Para producción: añadir CSRF, controles de permisos y despliegue seguro; no ejecutar Flask con debug=True en internet.


## Reservas por cancha (actualización)
- NEXOBOT muestra 9 horarios de 13:00 a 22:00, de 60 minutos.
- Cada horario permite elegir exactamente una de 14 canchas.
- Las canchas reservadas se bloquean y muestran el nombre de usuario del titular.
- El servidor comprueba la reserva con restricción UNIQUE para impedir duplicados.
- Es necesario iniciar sesión para reservar.
- Los nombres de los titulares se muestran a los visitantes: usar nombres públicos o alias y revisar privacidad antes de publicar.
- No elimines tu archivo `futgool.db` si ya tienes datos; el esquema de reservas es compatible con la versión anterior.
