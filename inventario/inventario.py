import sqlite3
from .producto import Producto

class Inventario:
    def __init__(self, db_name="inventario.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                precio REAL NOT NULL
            )
        ''')
        self.conn.commit()

    def agregar_producto(self, nombre, cantidad, precio):
        self.cursor.execute(
            "INSERT INTO productos (nombre, cantidad, precio) VALUES (?, ?, ?)",
            (nombre, cantidad, precio)
        )
        self.conn.commit()

    def eliminar_producto(self, id_producto):
        self.cursor.execute("DELETE FROM productos WHERE id_producto=?", (id_producto,))
        self.conn.commit()

    def actualizar_producto(self, id_producto, cantidad=None, precio=None):
        if cantidad is not None:
            self.cursor.execute("UPDATE productos SET cantidad=? WHERE id_producto=?", (cantidad, id_producto))
        if precio is not None:
            self.cursor.execute("UPDATE productos SET precio=? WHERE id_producto=?", (precio, id_producto))
        self.conn.commit()

    def obtener_productos(self):
        self.cursor.execute("SELECT * FROM productos")
        rows = self.cursor.fetchall()
        return [Producto(*row) for row in rows]
