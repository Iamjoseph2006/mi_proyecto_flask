from flask_login import UserMixin
from conexion.conexion import obtener_conexion_mysql
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(UserMixin):
    def __init__(self, id_usuario, nombre, mail, password, rol):
        self.id = id_usuario
        self.nombre = nombre
        self.mail = mail
        self.password = password
        self.rol = rol

    @staticmethod
    def obtener_por_mail(mail):
        conn = obtener_conexion_mysql()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE mail=%s", (mail,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Usuario(row['id_usuario'], row['nombre'], row['mail'], row['password'], row['rol'])
        return None

    @staticmethod
    def registrar(nombre, mail, password, rol):
        # Hashear la contraseña
        hashed = generate_password_hash(password)
        conn = obtener_conexion_mysql()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (nombre, mail, password, rol) VALUES (%s,%s,%s,%s)",
            (nombre, mail, hashed, rol)
        )
        conn.commit()
        conn.close()

    def verificar_password(self, password):
        return check_password_hash(self.password, password)