from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import mysql.connector
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from functools import wraps
from flask import redirect, url_for
import os  # Asegúrate de importar el módulo os
from dotenv import load_dotenv


app = Flask(__name__)
app.secret_key = 'mysecretkey'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000 
csrf = CSRFProtect(app)


load_dotenv()  # Carga las variables del archivo .env
# Configuración para MySQL
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'estacionamiento')


# Función para conectar a la base de datos MySQL
def get_db_connection():
    conn = mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    return conn


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/carro')
@login_required
def carro():
    if 'logged_in' in session:
        nombre = session['nombre']
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Consulta para obtener los carros registrados
            cursor.execute('SELECT * FROM carros')
            carros = cursor.fetchall()

            # Verificar si el usuario es administrador
            cursor.execute('SELECT * FROM admin WHERE nombre = %s', (nombre,))
            admin_user = cursor.fetchone()

            es_admin = admin_user is not None
            
        except Exception as e:
            print(f"Error al obtener los carros: {str(e)}")
            flash('Error al obtener los carros', 'error')
            return redirect(url_for('index'))
        
        finally:
            conn.close()

        return render_template('carros.html', nombre=nombre, carros=carros, es_admin=es_admin)
    else:
        return redirect(url_for('login'))

def generar_codigo_verificacion():
    return ''.join(random.choices('0123456789', k=4))

@app.route('/registro_autos', methods=['GET', 'POST'])
@login_required
def registro_autos():
    if 'logged_in' in session:
        if request.method == 'POST':
            # Datos del formulario
            placa = request.form['placa']
            marca = request.form['marca']
            modelo = request.form['modelo']
            color = request.form['color']
            propietario = request.form['propietario']
            telefono = request.form['telefono']
            correo = request.form['correo']  # Nuevo campo para el correo electrónico
            precio_pagado = request.form['precio_pagado']
            descripcion = request.form['descripcion']
            
            # Generar código de verificación
            codigo_verificacion = generar_codigo_verificacion()
            
            # Estado de pago
            status_pago = 'Pendiente' if 'status_pago' in request.form else 'Pagado'

            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                # Insertar datos en la base de datos
                cursor.execute('INSERT INTO carros (placa, marca, modelo, color, propietario, telefono, correo, precio_pagado, status_pago, descripcion, codigo_verificacion) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                               (placa, marca, modelo, color, propietario, telefono, correo, precio_pagado, status_pago, descripcion, codigo_verificacion))
                conn.commit()

                # Enviar código al propietario por correo electrónico
                enviar_codigo_por_email(correo, codigo_verificacion)  # Usar el correo electrónico

                flash('Se ha registrado el auto correctamente.', 'success')
                return redirect(url_for('registro_autos'))
            except Exception as e:
                conn.rollback()
                flash(f'Error al registrar el auto: {str(e)}', 'error')
            finally:
                conn.close()

        return render_template('registro_auto.html')
    else:
        return redirect(url_for('login'))


def es_numero_valido(numero):
    patron = re.compile(r'^\+\d{10,15}$')  # Ejemplo para números con código de país y 10 a 15 dígitos
    return patron.match(numero) is not None

def enviar_codigo_por_email(correo_propietario, codigo_verificacion):
    # Configuración del servidor SMTP
    smtp_server = 'smtp.gmail.com'  # Cambia esto por el servidor SMTP que usarás
    smtp_port = 587
    smtp_user = 'rojasbautistae02@gmail.com'  # Cambia esto por tu dirección de correo
    smtp_password = 'wekjixhgsixonmek'  # Cambia esto por tu contraseña de correo

    # Crear el mensaje
    mensaje = MIMEMultipart()
    mensaje['From'] = smtp_user
    mensaje['To'] = correo_propietario
    mensaje['Subject'] = 'Código de Verificación para Estacionamiento'
    
    cuerpo = f'Su código de verificación para el estacionamiento es: {codigo_verificacion}'
    mensaje.attach(MIMEText(cuerpo, 'plain'))

    try:
        # Conectar al servidor SMTP y enviar el correo
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Usar TLS para la seguridad
            server.login(smtp_user, smtp_password)
            server.send_message(mensaje)
            print('Correo enviado correctamente')
    except Exception as e:
        print(f'Error al enviar el correo: {str(e)}')

@app.route('/registro_empleados', methods=['GET', 'POST'])
@login_required
def registro_empleados():
    if 'logged_in' in session:
        if request.method == 'POST':
            nombre = request.form['nombre']
            correo = request.form['correo']
            contrasena = request.form['contrasena']
            
            # Conectar a la base de datos
            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                # Insertar el nuevo empleado en la tabla de empleados
                cursor.execute('INSERT INTO empleados (nombre, correo, contrasena) VALUES (%s, %s, %s)',
                               (nombre, correo, contrasena))
                
                # Confirmar la transacción
                conn.commit()
                
                flash('Se ha registrado el empleado correctamente.', 'success')
                return redirect(url_for('registro_empleados'))

            except Exception as e:
                conn.rollback()
                flash(f'Error al registrar el empleado: {str(e)}', 'error')
            
            finally:
                conn.close()

        return render_template('reg_empleados.html')
    else:
        return redirect(url_for('login'))

@app.route('/empleados')
@login_required
def empleado():
    return render_template('empleados.html')

@app.route('/cartera')
@login_required
def cartera():
    if 'logged_in' in session:
        nombre = session['nombre']  # Obtén el nombre de usuario de la sesión
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Consulta para obtener todos los carros activos
            cursor.execute('SELECT * FROM autos_activos')
            carros = cursor.fetchall()
            
            # Calcular el total acumulado de los precios pagados
            total_acumulado = sum(float(carro['precio']) for carro in carros)
            
        except Exception as e:
            # Manejar el error adecuadamente (por ejemplo, loguearlo)
            print(f"Error al procesar carros: {str(e)}")
            flash('Error al procesar los carros', 'error')
            return redirect(url_for('login'))
        
        finally:
            conn.close()

        return render_template('cartera.html', nombre=nombre, carros=carros, total_acumulado=total_acumulado)
    else:
        return redirect(url_for('login'))


@app.route('/admin')
@login_required
def admin():
    if 'logged_in' in session:
        nombre = session['nombre']  # Obtén el nombre de usuario de la sesión
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Ejecutar la consulta para obtener los carros registrados
        cursor.execute('SELECT * FROM carros')
        carros = cursor.fetchall()
        
        conn.close()

        return render_template('administrador.html', nombre=nombre, carros=carros)
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contraseña']
        recordarme = request.form.get('recordarme')  # Verificar si se seleccionó la opción "Recordarme"

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar en la tabla de administradores
        cursor.execute('SELECT * FROM admin WHERE correo = %s AND contrasena = %s', (correo, contrasena))
        admin_user = cursor.fetchone()

        if admin_user:
            session['logged_in'] = True
            session['nombre'] = admin_user['nombre']
            if recordarme:
                resp = make_response(redirect(url_for('admin')))
                expires = datetime.utcnow() + timedelta(days=30)  # Cookie expira en 30 días
                resp.set_cookie('correo', correo, expires=expires)
                resp.set_cookie('contrasena', contrasena, expires=expires)
                return resp
            conn.close()
            return redirect(url_for('admin'))

        # Buscar en la tabla de empleados
        cursor.execute('SELECT * FROM empleados WHERE correo = %s AND contrasena = %s', (correo, contrasena))
        empleado_user = cursor.fetchone()

        if empleado_user:
            session['logged_in'] = True
            session['nombre'] = empleado_user['nombre']
            if recordarme:
                resp = make_response(redirect(url_for('registro_autos')))
                expires = datetime.utcnow() + timedelta(days=30)  # Cookie expira en 30 días
                resp.set_cookie('correo', correo, expires=expires)
                resp.set_cookie('contrasena', contrasena, expires=expires)
                return resp
            conn.close()
            return redirect(url_for('registro_autos'))

        conn.close()
        error = 'Usuario o contraseña incorrectos'
        return render_template('login.html', error=error)

    # Verificar si las cookies existen
    correo = request.cookies.get('correo', '')
    contrasena = request.cookies.get('contrasena', '')

    if correo and contrasena:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM admin WHERE correo = %s AND contrasena = %s', (correo, contrasena))
        admin_user = cursor.fetchone()

        if admin_user:
            session['logged_in'] = True
            session['nombre'] = admin_user['nombre']
            conn.close()
            return redirect(url_for('admin'))

        cursor.execute('SELECT * FROM empleados WHERE correo = %s AND contrasena = %s', (correo, contrasena))
        empleado_user = cursor.fetchone()

        if empleado_user:
            session['logged_in'] = True
            session['nombre'] = empleado_user['nombre']
            conn.close()
            return redirect(url_for('registro_autos'))

        conn.close()

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('index')))
    resp.set_cookie('correo', '', expires=0)
    resp.set_cookie('contrasena', '', expires=0)
    return resp


@app.route('/hacer_corte', methods=['POST'])
@login_required
def hacer_corte():
    if 'logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            fecha_corte = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Obtener el total del corte desde la tabla autos_activos
            cursor.execute('SELECT SUM(precio) as total FROM autos_activos WHERE cortado = FALSE')
            total_corte = cursor.fetchone()['total']

            if total_corte is None:
                total_corte = 0.00

            print(f"Fecha del corte: {fecha_corte}, Total del corte: {total_corte}")

            # Insertar el nuevo corte en la tabla cortes_caja
            cursor.execute('INSERT INTO cortes_caja (total, fecha_corte) VALUES (%s, %s)', (total_corte, fecha_corte))

            # Actualizar el estado de los carros en autos_activos a cortado
            cursor.execute('UPDATE autos_activos SET cortado = TRUE WHERE cortado = FALSE')

            # Confirmar la transacción
            conn.commit()

            print("Corte de caja realizado correctamente.")
            flash('Corte de caja realizado correctamente.', 'success')
            return redirect(url_for('cartera'))

        except Exception as e:
            conn.rollback()
            print(f"Error al realizar el corte de caja: {str(e)}")
            flash(f'Error al realizar el corte de caja: {str(e)}', 'error')
            return redirect(url_for('cartera'))

        finally:
            conn.close()
    else:
        return redirect(url_for('login'))


@app.route('/ver_cortes')
@login_required
def ver_cortes():
    if 'logged_in' in session:
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener todos los cortes de caja realizados
        cursor.execute('SELECT * FROM cortes_caja')
        cortes = cursor.fetchall()
        
        # Calcular el total de todos los cortes
        total_cortes = sum(corte['total'] for corte in cortes)
        
        conn.close()

        return render_template('ver_cortes.html', cortes=cortes, total_cortes=total_cortes)
    else:
        return redirect(url_for('login'))

@app.route('/editar_pago/<int:carro_id>', methods=['GET', 'POST'])
@login_required
def editar_pago(carro_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        status_pago = request.form['status_pago']

        try:
            # Actualizar el estado de pago en la base de datos
            cursor.execute('UPDATE carros SET status_pago = %s WHERE id = %s', (status_pago, carro_id))
            conn.commit()

            flash('Estado de pago actualizado correctamente.', 'success')
        except Exception as e:
            flash(f'Error al actualizar el estado de pago: {str(e)}', 'error')
        finally:
            conn.close()

        # Volver a renderizar la misma página después de actualizar
        return redirect(url_for('editar_pago', carro_id=carro_id))

    # Obtener los detalles del carro
    cursor.execute('SELECT * FROM carros WHERE id = %s', (carro_id,))
    carro = cursor.fetchone()
    conn.close()

    return render_template('editar_pago.html', carro=carro)

@app.route('/entrega', methods=['GET', 'POST'])
@login_required
def entrega():
    if request.method == 'POST':
        codigo_verificacion = request.form['codigo_verificacion']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Verificar si el código de verificación existe, el auto no ha sido entregado
            cursor.execute('''
                SELECT * FROM carros 
                WHERE codigo_verificacion = %s 
                AND entregado = FALSE
            ''', (codigo_verificacion,))
            carro = cursor.fetchone()

            if carro:
                if carro['status_pago'] == 'Pendiente':
                    # Redirigir a la página de actualización de pago
                    print("Flash Message: Pendiente de pago")
                    flash('Pendiente de pago', 'error')

                    return redirect(url_for('editar_pago', carro_id=carro['id']))
                
                # Mover el auto a la tabla autos_activos
                cursor.execute('INSERT INTO autos_activos (id_carro, precio) VALUES (%s, %s)',
                               (carro['id'], carro['precio_pagado']))
                
                # Actualizar el estado del carro
                cursor.execute('UPDATE carros SET entregado = TRUE WHERE codigo_verificacion = %s', (codigo_verificacion,))
                
                conn.commit()
                flash('El auto ha sido entregado correctamente.', 'success')
            else:
                flash('Código de verificación no válido o el auto ya ha sido entregado.', 'error')

        except Exception as e:
            conn.rollback()
            flash(f'Error al procesar la entrega: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('entrega'))

    return render_template('entregar_auto.html')




if __name__ == '__main__':
    app.run(debug=True)
