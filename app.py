from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from inventario.inventario import Inventario
from conexion.conexion import obtener_conexion_mysql
import os
import json
import csv

app = Flask(__name__)
app.secret_key = "mi_clave_secreta"

# ------------------ LOGIN ------------------
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

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
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# ------------------ PRODUCTOS ------------------
@app.route("/productos", methods=["GET", "POST"])
def productos():
    if request.method == "POST" and "add" in request.form:
        nombre = request.form["nombre"]
        cantidad = int(request.form["cantidad"])
        precio = float(request.form["precio"])
        inv.agregar_producto(nombre, cantidad, precio)
        sincronizar_archivos()
        flash("✅ Producto añadido con éxito", "success")
        return redirect(url_for("productos"))

    buscar_nombre = request.args.get("buscar")
    if buscar_nombre:
        productos = [p for p in inv.obtener_productos() if buscar_nombre.lower() in p.nombre.lower()]
    else:
        productos = inv.obtener_productos()
    return render_template("productos.html", productos=productos)

@app.route("/eliminar/<int:id_producto>")
def eliminar(id_producto):
    inv.eliminar_producto(id_producto)
    sincronizar_archivos()
    flash("🗑️ Producto eliminado", "danger")
    return redirect(url_for("productos"))

@app.route("/actualizar/<int:id_producto>", methods=["POST"])
def actualizar(id_producto):
    cantidad = int(request.form["cantidad"])
    precio = float(request.form["precio"])
    inv.actualizar_producto(id_producto, cantidad=cantidad, precio=precio)
    sincronizar_archivos()
    flash("✏️ Producto actualizado", "info")
    return redirect(url_for("productos"))

@app.route("/editar/<int:id_producto>")
def editar(id_producto):
    productos = inv.obtener_productos()
    producto = next((p for p in productos if p.id_producto == id_producto), None)
    if producto is None:
        flash("❌ Producto no encontrado", "warning")
        return redirect(url_for("productos"))
    return render_template("editar.html", producto=producto)

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

# --- LOGIN / REGISTER ajustado a tu tabla ---
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
    return redirect(url_for("index"))


# ------------------ RUTA PROTEGIDA ------------------
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", nombre=current_user.nombre, rol=current_user.rol)

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
