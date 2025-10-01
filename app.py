from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from inventario.inventario import Inventario
from conexion.conexion import obtener_conexion_mysql
from flask import session
import os
import json
import csv

app = Flask(__name__)
app.secret_key = "mi_clave_secreta"

# ------------------ LOGIN ------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # ruta a tu formulario de login
login_manager.login_message = "⚠️ Debes Iniciar Sesión para Acceder"
login_manager.login_message_category = "warning"


# ------------------ CLASE USUARIO ------------------
class Usuario(UserMixin):
    def __init__(self, id_usuario, nombre, mail, rol, password_hash):
        self.id = id_usuario
        self.nombre = nombre
        self.mail = mail
        self.rol = rol
        self.password = password_hash

@login_manager.user_loader
def load_user(user_id):
    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE id_usuario = %s", (user_id,))
    row = cursor.fetchone()
    conexion.close()
    if row:
        return Usuario(row["id_usuario"], row["nombre"], row["mail"], row["rol"], row["password"])
    return None

# ------------------ INVENTARIO ------------------
inv = Inventario()

DATA_FOLDER = "datos"
TXT_FILE = os.path.join(DATA_FOLDER, "datos.txt")
JSON_FILE = os.path.join(DATA_FOLDER, "datos.json")
CSV_FILE = os.path.join(DATA_FOLDER, "datos.csv")
os.makedirs(DATA_FOLDER, exist_ok=True)

# ------------------ FUNCIONES AUXILIARES ------------------
def sincronizar_archivos():
    productos = inv.obtener_productos()
    with open(TXT_FILE, "w", encoding="utf-8") as f:
        for p in productos:
            f.write(f"{p.nombre},{p.cantidad},{p.precio}\n")
    data_json = [{"nombre": p.nombre, "cantidad": p.cantidad, "precio": p.precio} for p in productos]
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data_json, f, indent=4)
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["nombre", "cantidad", "precio"])
        for p in productos:
            writer.writerow([p.nombre, p.cantidad, p.precio])

def leer_txt():
    if not os.path.exists(TXT_FILE):
        return []
    with open(TXT_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip().split(",") for line in f.readlines()]
        return [{"nombre": l[0], "cantidad": int(l[1]), "precio": float(l[2])} for l in lines]

def leer_json():
    if not os.path.exists(JSON_FILE):
        return []
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def leer_csv():
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        productos = []
        for row in reader:
            productos.append({
                "nombre": row.get("nombre", ""),
                "cantidad": int(row.get("cantidad", 0)),
                "precio": float(row.get("precio", 0.0))
            })
        return productos

# ------------------ RUTAS PÁGINAS ------------------
@app.route("/")
def index():
    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    conexion.close()
    return render_template("index.html", productos=productos)

@app.route("/about")
def about():
    return render_template("about.html")

# ------------------ PRODUCTOS ------------------
# Inicializar carrito si no existe
@app.before_request
def init_cart():
    if "cart" not in session:
        session["cart"] = []

# --- Ver productos (Tienda) ---
@app.route("/productos", methods=["GET"])
@login_required
def productos_tienda():
    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos WHERE cantidad > 0")
    productos = cursor.fetchall()
    conexion.close()
    return render_template("productos.html", productos=productos)

# --- Agregar producto al carrito ---
@app.route("/agregar_carrito/<int:id_producto>")
@login_required
def agregar_carrito(id_producto):
    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos WHERE id_producto=%s", (id_producto,))
    producto = cursor.fetchone()
    conexion.close()

    if producto:
        carrito = session.get("cart", [])

        # Buscar si ya está en el carrito
        for item in carrito:
            if item["id_producto"] == id_producto:
                if item["cantidad"] < producto["cantidad"]:  # Validar stock
                    item["cantidad"] += 1
                    flash(f"{producto['nombre']} +1 en el carrito.", "info")
                else:
                    flash("Stock Insuficiente.", "warning")
                break
        else:
            if producto["cantidad"] > 0:  # Solo agregar si hay stock
                carrito.append({
                    "id_producto": producto["id_producto"],
                    "nombre": producto["nombre"],
                    "precio": float(producto["precio"]),
                    "cantidad": 1
                })
                flash(f"{producto['nombre']} Agregado al Carrito. ✅", "success")
            else:
                flash("Producto sin stock disponible.", "danger")

        session["cart"] = carrito
    else:
        flash("Producto no encontrado.", "danger")

    return redirect(url_for("productos_tienda"))


# --- Ver carrito ---
@app.route("/carrito")
@login_required
def carrito():
    carrito = session.get("cart", [])
    total = sum(item["precio"] * item["cantidad"] for item in carrito)
    return render_template("carrito.html", carrito=carrito, total=total)


# --- Actualizar cantidad en carrito ---
@app.route("/actualizar_carrito/<int:id_producto>", methods=["POST"])
@login_required
def actualizar_carrito(id_producto):
    nueva_cantidad = int(request.form.get("cantidad", 1))

    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT cantidad FROM productos WHERE id_producto=%s", (id_producto,))
    producto = cursor.fetchone()
    conexion.close()

    carrito = session.get("cart", [])
    for item in carrito:
        if item["id_producto"] == id_producto:
            if nueva_cantidad <= 0:
                carrito.remove(item)  # Eliminar si es 0
                flash("🗑️ Producto eliminado del carrito.", "warning")
            elif nueva_cantidad <= producto["cantidad"]:  # Validar stock
                item["cantidad"] = nueva_cantidad
                flash("✅ Cantidad Actualizada en el Carrito.", "info")
            else:
                flash("Stock Insuficiente.", "danger")
            break

    session["cart"] = carrito
    return redirect(url_for("carrito"))


# --- Eliminar producto del carrito ---
@app.route("/eliminar_carrito/<int:id_producto>")
@login_required
def eliminar_carrito(id_producto):
    carrito = session.get("cart", [])
    carrito = [item for item in carrito if item["id_producto"] != id_producto]
    session["cart"] = carrito
    flash("🗑️ Producto Eliminado del Carrito.", "danger")
    return redirect(url_for("carrito"))


# --- Finalizar compra ---
@app.route("/finalizar_compra", methods=["POST"])
@login_required
def finalizar_compra():
    carrito = session.get("cart", [])
    if not carrito:
        flash("Tu carrito está vacío.", "warning")
        return redirect(url_for("productos_tienda"))

    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor()

    # Total de la compra
    total = sum(item["precio"] * item["cantidad"] for item in carrito)

    # Insertar venta
    cursor.execute(
        "INSERT INTO ventas (id_usuario, fecha, total) VALUES (%s, NOW(), %s)",
        (current_user.id, total)
    )
    id_venta = cursor.lastrowid

    # Insertar detalle de venta y actualizar stock
    for item in carrito:
        subtotal = item["precio"] * item["cantidad"]
        cursor.execute(
            "INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, subtotal) VALUES (%s, %s, %s, %s)",
            (id_venta, item["id_producto"], item["cantidad"], subtotal)
        )
        cursor.execute(
            "UPDATE productos SET cantidad = cantidad - %s WHERE id_producto = %s AND cantidad >= %s",
            (item["cantidad"], item["id_producto"], item["cantidad"])
        )

    conexion.commit()
    conexion.close()

    session["cart"] = []  # Vaciar carrito
    flash("✅ ¡Compra Realizada con Éxito!", "success")
    return redirect(url_for("dashboard"))

# --- Insertar Productos ---
@app.route("/crear", methods=["GET", "POST"])
@login_required
def crear_producto():
    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        cantidad = request.form["cantidad"]
        precio = request.form["precio"]

        conexion = obtener_conexion_mysql()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO productos (nombre, categoria, cantidad, precio) VALUES (%s, %s, %s, %s)",
                       (nombre, categoria, cantidad, precio))
        conexion.commit()
        conexion.close()
        flash("✏️ Producto Agregado Correctamente.", "success")
        return redirect(url_for("dashboard"))

    return render_template("crear_producto.html")


@app.route("/editar/<int:id_producto>", methods=["GET", "POST"])
@login_required
def editar_producto(id_producto):
    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor(dictionary=True)

    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        cantidad = request.form["cantidad"]
        precio = request.form["precio"]

        cursor.execute(
            "UPDATE productos SET nombre=%s, categoria=%s, cantidad=%s, precio=%s WHERE id_producto=%s",
            (nombre, categoria, cantidad, precio, id_producto)
        )
        conexion.commit()
        conexion.close()
        flash("✏️ Producto Actualizado Correctamente.", "success")
        return redirect(url_for("productos"))

    # Para GET: obtenemos los datos del producto y mostramos el formulario
    cursor.execute("SELECT * FROM productos WHERE id_producto=%s", (id_producto,))
    producto = cursor.fetchone()
    conexion.close()

    if producto is None:
        flash("Producto no Encontrado", "error")
        return redirect(url_for("productos"))

    return render_template("editar_producto.html", producto=producto)


@app.route("/actualizar/<int:id_producto>", methods=["POST"])
@login_required
def actualizar(id_producto):
    nombre = request.form["nombre"]
    categoria = request.form["categoria"]
    cantidad = int(request.form["cantidad"])
    precio = float(request.form["precio"])

    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE productos
        SET nombre=%s, categoria=%s, cantidad=%s, precio=%s
        WHERE id_producto=%s
    """, (nombre, categoria, cantidad, precio, id_producto))

    conexion.commit()
    print(f"Filas afectadas: {cursor.rowcount}")
    conexion.close()

    flash("✏️ Producto actualizado correctamente", "info")
    return redirect(url_for("dashboard"))



@app.route("/eliminar/<int:id>", methods=["POST"])
@login_required
def eliminar_producto(id):
    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM productos WHERE id_producto=%s", (id,))
    conexion.commit()
    conexion.close()
    flash("🗑️ Producto eliminado", "info")
    return redirect(url_for("listar_productos"))


# ------------------ ARCHIVOS ------------------
@app.route("/productos_txt")
def productos_txt():
    productos = leer_txt()
    return render_template("productos_txt.html", productos=productos)

@app.route("/productos_json")
def productos_json():
    productos = leer_json()
    return render_template("productos_json.html", productos=productos)

@app.route("/productos_csv")
def productos_csv():
    productos = leer_csv()
    return render_template("productos_csv.html", productos=productos)

# ------------------ Register ------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        mail = request.form["mail"]
        rol = request.form.get("rol", "cliente")
        password = request.form["password"]
        password_hash = generate_password_hash(password)  # Guardamos hash en "password"

        conexion = obtener_conexion_mysql()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuarios (nombre, mail, password, rol) VALUES (%s,%s,%s,%s)",
                (nombre, mail, password_hash, rol)
            )
            conexion.commit()
            flash("✅ Usuario registrado con éxito", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"❌ Error al registrar usuario: {e}", "danger")
        finally:
            conexion.close()
    return render_template("register.html")

# ------------------ Login ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        mail = request.form["mail"]
        password = request.form["password"]
        conexion = obtener_conexion_mysql()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE mail=%s", (mail,))
        row = cursor.fetchone()
        conexion.close()

        if row and row["password"] and check_password_hash(row["password"], password):
            usuario = Usuario(row["id_usuario"], row["nombre"], row["mail"], row["rol"], row["password"])
            login_user(usuario)
            flash("✅ Sesión Iniciada", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Correo o Contraseña Incorrectos", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("✅ Sesión Cerrada", "success")
    return redirect(url_for("login"))


# ------------------ Dashboard ------------------
@app.route("/dashboard")
@login_required
def dashboard():
    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor(dictionary=True)

    if current_user.rol == "Administrador":
        # Métricas
        cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
        total_usuarios = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM productos")
        total_productos = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM ventas")
        total_ventas = cursor.fetchone()["total"]

        cursor.execute("SELECT IFNULL(SUM(total),0) AS ingresos FROM ventas")
        ingresos = cursor.fetchone()["ingresos"]

        # Usuarios
        cursor.execute("SELECT * FROM usuarios")
        usuarios = cursor.fetchall()

        # Productos
        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()

        # Ventas
        cursor.execute("""
            SELECT v.id_venta, u.nombre AS cliente, v.fecha, v.total
            FROM ventas v
            JOIN usuarios u ON v.id_usuario = u.id_usuario
            ORDER BY v.fecha DESC
        """)
        ventas = cursor.fetchall()

        conexion.close()
        return render_template(
            "dashboard_admin.html",
            data={
                "usuarios": total_usuarios,
                "productos": total_productos,
                "ventas": total_ventas,
                "ingresos": ingresos,
            },
            usuarios=usuarios,     # ✅ se envía al template
            productos=productos,
            ventas=ventas
        )

    elif current_user.rol == "Empleado":
        # Productos
        cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()

        # Ventas
        cursor.execute("""
            SELECT v.id_venta, u.nombre AS cliente, v.fecha, v.total
            FROM ventas v
            JOIN usuarios u ON v.id_usuario = u.id_usuario
            ORDER BY v.fecha DESC
        """)
        ventas = cursor.fetchall()

        conexion.close()
        return render_template("dashboard_empleado.html", productos=productos, ventas=ventas)

    elif current_user.rol == "Cliente":
        # Solo sus compras
        cursor.execute("""
            SELECT v.id_venta, v.fecha, v.total
            FROM ventas v
            WHERE v.id_usuario = %s
            ORDER BY v.fecha DESC
        """, (current_user.id,))
        compras = cursor.fetchall()

        conexion.close()
        return render_template("dashboard_cliente.html", compras=compras)

    conexion.close()
    return redirect(url_for("index"))


# ------------------ Eliminar Usuario ------------------
@app.route("/eliminar_usuario/<int:id_usuario>", methods=["POST"])
@login_required
def eliminar_usuario(id_usuario):
    if current_user.rol != "Administrador":
        flash("No tienes permiso para realizar esta acción.", "danger")
        return redirect(url_for("dashboard"))

    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor()

    cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario,))
    conexion.commit()
    conexion.close()

    flash("🗑️ Usuario Eliminado Correctamente.", "success")
    return redirect(url_for("dashboard"))


# --- Ver detalle de una venta ---
@app.route("/detalle_venta/<int:id_venta>")
@login_required
def detalle_venta(id_venta):
    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor(dictionary=True)

    # Obtener la venta
    cursor.execute("""
        SELECT v.id_venta, v.fecha, v.total, u.nombre AS cliente
        FROM ventas v
        JOIN usuarios u ON v.id_usuario = u.id_usuario
        WHERE v.id_venta = %s
    """, (id_venta,))
    venta = cursor.fetchone()

    if not venta:
        conexion.close()
        flash("Venta no encontrada.", "danger")
        return redirect(url_for("dashboard"))

    # Obtener los productos de la venta
    cursor.execute("""
        SELECT dv.id_producto, p.nombre, dv.cantidad, dv.subtotal AS precio_unitario 


        FROM detalle_ventas dv
        JOIN productos p ON dv.id_producto = p.id_producto
        WHERE dv.id_venta = %s
    """, (id_venta,))
    detalles = cursor.fetchall()

    conexion.close()
    return render_template("detalle_venta.html", venta=venta, detalles=detalles)
# --- Eliminar venta ---
@app.route("/eliminar_venta/<int:id_venta>", methods=["POST", "GET"])
@login_required
def eliminar_venta(id_venta):
    # Solo admin puede eliminar
    if current_user.rol != "Administrador":
        flash("No tienes permisos para eliminar ventas.", "danger")
        return redirect(url_for("dashboard"))

    conexion = obtener_conexion_mysql()
    cursor = conexion.cursor()

    try:
        # Primero borrar los detalles de la venta
        cursor.execute("DELETE FROM detalle_ventas WHERE id_venta = %s", (id_venta,))
        # Luego borrar la venta
        cursor.execute("DELETE FROM ventas WHERE id_venta = %s", (id_venta,))
        conexion.commit()
        flash("Venta eliminada correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar la venta: {e}", "danger")
    finally:
        conexion.close()

    return redirect(url_for("dashboard"))


# ------------------ TEST DB ------------------
@app.route("/test_db")
def test_db():
    conexion = obtener_conexion_mysql()
    if conexion:
        conexion.close()
        return "✅ Conexión a MySQL correcta"
    else:
        return "❌ No se pudo conectar a MySQL"

# ------------------ EJECUTAR APP ------------------
if __name__ == "__main__":
    sincronizar_archivos()
    app.run(debug=True)