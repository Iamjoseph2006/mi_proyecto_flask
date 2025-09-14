# conexion/conexion.py
import mysql.connector
from mysql.connector import Error

def obtener_conexion_mysql():
    """
    Devuelve una conexión a la base de datos MySQL 'sweet_spot'.
    """
    try:
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  # Cambia si tu MySQL tiene contraseña
            database="sweet_spot"
        )
        return conexion
    except Error as e:
        print(f"Error de conexión a MySQL: {e}")
        return None