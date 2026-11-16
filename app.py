import os
import sqlite3
from datetime import datetime
from functools import wraps
import unicodedata
import re
from flask import Flask, flash, g, redirect, render_template, request, session, url_for, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'futgool.db')
app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']



def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()


def init_db():
    with app.app_context():
        db().executescript('''
        CREATE TABLE IF NOT EXISTS court_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_date TEXT NOT NULL,
            start_hour INTEGER NOT NULL CHECK(start_hour BETWEEN 13 AND 21),
            court_number INTEGER NOT NULL CHECK(court_number BETWEEN 1 AND 14),
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(booking_date, start_hour, court_number)
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'jugador' CHECK(role IN ('jugador','arbitro','admin')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            scheduled_at TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 14,
            creator_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS registrations (
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY(match_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            player_id INTEGER NOT NULL REFERENCES users(id),
            type TEXT NOT NULL CHECK(type IN ('gol','asistencia','amarilla','roja')),
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS ratings (
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            author_id INTEGER NOT NULL REFERENCES users(id),
            target_id INTEGER NOT NULL REFERENCES users(id),
            score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
            comment TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(match_id, author_id, target_id)
        );
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        db().commit()

@app.before_request
def load_user():
    g.user = db().execute('SELECT id, username, email, role FROM users WHERE id=?', (session.get('user_id', -1),)).fetchone()


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not g.user:
            flash('Inicia sesión para continuar.', 'error')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper


def get_match(match_id):
    match = db().execute('''SELECT m.*, u.username creator,
        (SELECT COUNT(*) FROM registrations r WHERE r.match_id=m.id) joined
        FROM matches m JOIN users u ON u.id=m.creator_id WHERE m.id=?''', (match_id,)).fetchone()
    if match is None:
        abort(404)
    return match

@app.route('/')
def home():
    counts = db().execute('SELECT (SELECT COUNT(*) FROM users) users, (SELECT COUNT(*) FROM matches) matches, (SELECT COUNT(*) FROM events WHERE type="gol") goals').fetchone()
    upcoming = db().execute('''SELECT m.*, u.username creator,
      (SELECT COUNT(*) FROM registrations r WHERE r.match_id=m.id) joined
      FROM matches m JOIN users u ON u.id=m.creator_id ORDER BY m.scheduled_at DESC LIMIT 6''').fetchall()
    return render_template('home.html', counts=counts, matches=upcoming)

@app.route('/registro', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        if not (3 <= len(username) <= 30) or '@' not in email or len(password) < 8:
            flash('Nombre de 3 a 30 caracteres, correo válido y contraseña de al menos 8 caracteres.', 'error')
        else:
            try:
                db().execute('INSERT INTO users(username,email,password) VALUES(?,?,?)', (username,email,generate_password_hash(password)))
                db().commit()
                flash('Cuenta creada. Ya puedes iniciar sesión.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('El nombre o correo ya está registrado.', 'error')
    return render_template('auth.html', mode='register')

@app.route('/ingresar', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = db().execute('SELECT * FROM users WHERE email=?', (request.form.get('email','').strip().lower(),)).fetchone()
        if user and check_password_hash(user['password'], request.form.get('password','')):
            session.clear()
            session['user_id'] = user['id']
            flash('¡Bienvenido a la cancha!', 'success')
            return redirect(url_for('home'))
        flash('Correo o contraseña incorrectos.', 'error')
    return render_template('auth.html', mode='login')

@app.post('/salir')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/partidos')
def matches():
    rows = db().execute('''SELECT m.*,u.username creator,
      (SELECT COUNT(*) FROM registrations r WHERE r.match_id=m.id) joined
      FROM matches m JOIN users u ON u.id=m.creator_id ORDER BY m.scheduled_at DESC''').fetchall()
    return render_template('matches.html', matches=rows)

@app.route('/partidos/crear', methods=['GET','POST'])
@login_required
def create_match():
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        location = request.form.get('location','').strip()
        when = request.form.get('scheduled_at','')
        try:
            capacity = int(request.form.get('capacity','14'))
            datetime.fromisoformat(when)
            if not (3 <= len(title) <= 80 and 3 <= len(location) <= 120 and 2 <= capacity <= 40):
                raise ValueError()
        except ValueError:
            flash('Revisa los datos: título, ubicación, fecha y cupos entre 2 y 40.', 'error')
        else:
            cur = db().execute('INSERT INTO matches(title,location,scheduled_at,capacity,creator_id) VALUES(?,?,?,?,?)', (title,location,when,capacity,g.user['id']))
            db().execute('INSERT INTO registrations(match_id,user_id) VALUES(?,?)', (cur.lastrowid,g.user['id']))
            db().commit()
            flash('Partido creado. Ya estás inscrito.', 'success')
            return redirect(url_for('match_detail',match_id=cur.lastrowid))
    return render_template('create_match.html')

@app.route('/partidos/<int:match_id>')
def match_detail(match_id):
    match = get_match(match_id)
    players = db().execute('''SELECT u.id,u.username FROM registrations r JOIN users u ON u.id=r.user_id WHERE r.match_id=? ORDER BY u.username''', (match_id,)).fetchall()
    events = db().execute('''SELECT e.type,e.created_at,u.username FROM events e JOIN users u ON u.id=e.player_id WHERE e.match_id=? ORDER BY e.id DESC''', (match_id,)).fetchall()
    ratings = db().execute('''SELECT r.score,r.comment,a.username author,t.username target FROM ratings r JOIN users a ON a.id=r.author_id JOIN users t ON t.id=r.target_id WHERE r.match_id=? ORDER BY r.rowid DESC''',(match_id,)).fetchall()
    joined = g.user and any(p['id']==g.user['id'] for p in players)
    can_manage = g.user and (g.user['id']==match['creator_id'] or g.user['role'] in ('arbitro','admin'))
    return render_template('match_detail.html',match=match,players=players,events=events,ratings=ratings,joined=joined,can_manage=can_manage)

@app.post('/partidos/<int:match_id>/inscribir')
@login_required
def join_match(match_id):
    match = get_match(match_id)
    existing = db().execute('SELECT 1 FROM registrations WHERE match_id=? AND user_id=?', (match_id,g.user['id'])).fetchone()
    if existing:
        flash('Ya estás inscrito.', 'error')
    elif match['joined'] >= match['capacity']:
        flash('No quedan cupos.', 'error')
    else:
        db().execute('INSERT INTO registrations(match_id,user_id) VALUES(?,?)',(match_id,g.user['id']))
        db().commit()
        flash('Inscripción exitosa.', 'success')
    return redirect(url_for('match_detail',match_id=match_id))

@app.post('/partidos/<int:match_id>/salir')
@login_required
def leave_match(match_id):
    get_match(match_id)
    db().execute('DELETE FROM registrations WHERE match_id=? AND user_id=?',(match_id,g.user['id']))
    db().commit()
    flash('Saliste del partido.', 'success')
    return redirect(url_for('match_detail',match_id=match_id))

@app.post('/partidos/<int:match_id>/evento')
@login_required
def add_event(match_id):
    match = get_match(match_id)
    if not (g.user['id']==match['creator_id'] or g.user['role'] in ('arbitro','admin')):
        abort(403)
    try:
        player_id = int(request.form.get('player_id',''))
    except ValueError:
        abort(400)
    event_type = request.form.get('type','')
    if event_type not in ('gol','asistencia','amarilla','roja'):
        abort(400)
    if not db().execute('SELECT 1 FROM registrations WHERE match_id=? AND user_id=?',(match_id,player_id)).fetchone():
        abort(400)
    db().execute('INSERT INTO events(match_id,player_id,type,created_by) VALUES(?,?,?,?)',(match_id,player_id,event_type,g.user['id']))
    db().commit()
    flash('Evento registrado.', 'success')
    return redirect(url_for('match_detail',match_id=match_id))

@app.post('/partidos/<int:match_id>/evaluar')
@login_required
def rate(match_id):
    get_match(match_id)
    try:
        target_id = int(request.form.get('target_id',''))
        score = int(request.form.get('score',''))
    except ValueError:
        abort(400)
    comment = request.form.get('comment','').strip()[:250]
    if target_id==g.user['id'] or score not in range(1,6):
        abort(400)
    for uid in (target_id,g.user['id']):
        if not db().execute('SELECT 1 FROM registrations WHERE match_id=? AND user_id=?',(match_id,uid)).fetchone():
            abort(403)
    db().execute('''INSERT INTO ratings(match_id,author_id,target_id,score,comment) VALUES(?,?,?,?,?)
      ON CONFLICT(match_id,author_id,target_id) DO UPDATE SET score=excluded.score,comment=excluded.comment''',(match_id,g.user['id'],target_id,score,comment))
    db().commit()
    flash('Evaluación guardada.', 'success')
    return redirect(url_for('match_detail',match_id=match_id))

@app.route('/ranking')
def ranking():
    rows = db().execute('''SELECT u.username,
      SUM(CASE WHEN e.type='gol' THEN 1 ELSE 0 END) goals,
      SUM(CASE WHEN e.type='asistencia' THEN 1 ELSE 0 END) assists,
      (SELECT ROUND(AVG(r.score),1) FROM ratings r WHERE r.target_id=u.id) rating
      FROM users u LEFT JOIN events e ON e.player_id=u.id GROUP BY u.id ORDER BY goals DESC,assists DESC,u.username''').fetchall()
    return render_template('ranking.html',players=rows)

@app.route('/comunidad',methods=['GET','POST'])
def community():
    if request.method=='POST':
        if not g.user:
            return redirect(url_for('login'))
        body = request.form.get('body','').strip()
        if not 1 <= len(body) <= 500:
            flash('Escribe un mensaje de hasta 500 caracteres.', 'error')
        else:
            db().execute('INSERT INTO posts(user_id,body) VALUES(?,?)',(g.user['id'],body))
            db().commit()
            flash('Publicación compartida.', 'success')
            return redirect(url_for('community'))
    posts = db().execute('SELECT p.*,u.username FROM posts p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC LIMIT 100').fetchall()
    return render_template('community.html',posts=posts)


# Asistente de ayuda local: no usa APIs externas ni envía datos a terceros.
def normalize_question(value):
    value = unicodedata.normalize('NFKD', value.lower())
    return ''.join(c for c in value if not unicodedata.combining(c))


def chatbot_answer(message):
    q = normalize_question(message)
    words = set(re.findall(r'[a-z0-9]+', q))
    if words & {'hola', 'buenas', 'hey', 'saludos'}:
        return '¡Hola! Soy NEXOBOT, asistente de FUTGOOL PLAYER. Puedo ayudarte con partidos, inscripciones, estadísticas, ranking, comunidad y cuentas.'
    if words & {'registrar', 'registro', 'cuenta', 'registrarme', 'usuario', 'contrasena', 'password'}:
        return 'Para crear una cuenta, presiona «Crear cuenta» arriba, completa usuario, correo y contraseña. Luego inicia sesión desde «Ingresar».'
    if words & {'iniciar', 'ingresar', 'login', 'sesion', 'entrar'}:
        return 'Selecciona «Ingresar» en la barra superior y escribe tus credenciales. Si no tienes cuenta, elige «Crear cuenta».'
    if words & {'crear', 'agendar', 'organizar', 'programar'} and words & {'partido', 'partidos', 'encuentro'}:
        return 'Para crear un partido, inicia sesión, entra a «Partidos» y usa la opción de crear partido. Completa nombre, fecha, hora, lugar y cupos.'
    if words & {'inscribir', 'inscribirme', 'unirme', 'participar', 'anotarme', 'cupo', 'cupos'}:
        return 'Para inscribirte, inicia sesión, entra a «Partidos», abre el encuentro que te interese y selecciona la opción para unirte si hay cupos.'
    if words & {'estadisticas', 'goles', 'gol', 'asistencias', 'tarjetas', 'eventos'}:
        return 'En el detalle de un partido se pueden registrar eventos como goles, asistencias y tarjetas, según los permisos disponibles. El ranking reúne las estadísticas de los jugadores.'
    if words & {'ranking', 'clasificacion', 'posiciones', 'tabla'}:
        return 'En «Ranking» puedes consultar los jugadores y sus goles, asistencias y valoraciones.'
    if words & {'evaluar', 'evaluacion', 'calificar', 'valoracion', 'puntuar'}:
        return 'Abre el detalle de un partido para consultar las opciones de evaluación de jugadores. Las valoraciones se registran de 1 a 5.'
    if words & {'comunidad', 'publicar', 'mensaje', 'publicacion', 'amigos'}:
        return 'En «Comunidad» puedes leer publicaciones. Para escribir un mensaje necesitas iniciar sesión.'
    if words & {'arbitro', 'arbitros', 'admin', 'administrador', 'roles'}:
        return 'FUTGOOL PLAYER contempla roles de jugador, árbitro y administrador. Algunas acciones requieren permisos específicos.'
    if words & {'torneos', 'torneo', 'qr', 'clanes', 'clan'}:
        return 'Los torneos, los códigos QR para equipos y los clanes están planteados como futuras mejoras del proyecto; no forman parte de las funciones principales actuales.'
    if words & {'nexora', 'empresa', 'desarrollador', 'creador'}:
        return 'NEXORA TECH es la empresa ficticia que desarrolla FUTGOOL PLAYER como proyecto académico para conectar a futbolistas amateur.'
    if words & {'ayuda', 'funciones', 'puedes', 'hacer', 'opciones'}:
        return 'Puedo explicarte cómo crear una cuenta, iniciar sesión, crear o unirte a partidos, registrar estadísticas, consultar el ranking y participar en la comunidad.'
    return 'Todavía no tengo una respuesta específica para eso. Prueba preguntarme: «¿Cómo creo un partido?», «¿Cómo me inscribo?» o «¿Dónde veo el ranking?». Soy un asistente de respuestas guiadas, no una IA generativa.'


@app.post('/api/chatbot')
def chatbot():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('message'), str):
        return jsonify(error='Envía un mensaje de texto válido.'), 400
    message = data['message'].strip()
    if not message or len(message) > 500:
        return jsonify(error='El mensaje debe tener entre 1 y 500 caracteres.'), 400
    return jsonify(reply=chatbot_answer(message))


# Reservas de canchas: 14 canchas, 9 turnos de 60 minutos (13:00 a 22:00).
from datetime import date as date_type

def validate_booking_date(value):
    try:
        day = date_type.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if day < date_type.today():
        return None
    return day

@app.get('/api/canchas/disponibilidad')
def court_availability():
    day = validate_booking_date(request.args.get('fecha', ''))
    if day is None:
        return jsonify(error='Elige una fecha válida, hoy o posterior.'), 400
    rows = db().execute("""SELECT b.start_hour, b.court_number, u.username
        FROM court_bookings b JOIN users u ON u.id=b.user_id
        WHERE b.booking_date=?""", (day.isoformat(),)).fetchall()
    booked = {(r['start_hour'], r['court_number']): r['username'] for r in rows}
    slots = []
    for h in range(13, 22):
        courts = [{'numero': n, 'disponible': (h, n) not in booked,
                   'reservado_por': booked.get((h, n))} for n in range(1, 15)]
        available = sum(c['disponible'] for c in courts)
        slots.append({'inicio': f'{h:02d}:00', 'fin': f'{h+1:02d}:00',
                      'hora': h, 'disponibles': available, 'ocupadas': 14-available,
                      'canchas': courts})
    return jsonify(fecha=day.isoformat(), total_canchas=14, turnos=slots)

@app.post('/api/canchas/reservar')
@login_required
def court_reserve():
    data = request.get_json(silent=True) or {}
    day = validate_booking_date(data.get('fecha'))
    try:
        hour = int(data.get('hora'))
    except (ValueError, TypeError):
        hour = -1
    try:
        court = int(data.get('cancha'))
    except (ValueError, TypeError):
        court = -1
    if day is None or hour not in range(13,22) or court not in range(1,15):
        return jsonify(error='Fecha u hora inválida.'), 400
    if day == date_type.today() and datetime.now().hour >= hour:
        return jsonify(error='Este horario ya comenzó o terminó.'), 400
    conn = db()
    try:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('INSERT INTO court_bookings(booking_date,start_hour,court_number,user_id) VALUES(?,?,?,?)',
                     (day.isoformat(), hour, court, g.user['id']))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify(error='La cancha ya está reservada para ese horario. Actualiza la disponibilidad.'), 409
    except Exception:
        conn.rollback()
        raise
    return jsonify(ok=True, reservado_por=g.user['username'], cancha=court, fecha=day.isoformat(), inicio=f'{hour:02d}:00', fin=f'{hour+1:02d}:00')

if __name__ == '__main__':
    init_db()
   
app.run(debug=False)

