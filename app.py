from flask import Flask, render_template, request, redirect, url_for, flash
from inventario.inventario import Inventario  # Tu clase de inventario con SQLite
import os
import json
import csv

app = Flask(__name__)
app.secret_key = "mi_clave_secreta"

# Crear instancia global de inventario
inv = Inventario()

# Carpeta donde estarán los archivos
DATA_FOLDER = "datos"
TXT_FILE = os.path.join(DATA_FOLDER, "datos.txt")
JSON_FILE = os.path.join(DATA_FOLDER, "datos.json")
CSV_FILE = os.path.join(DATA_FOLDER, "datos.csv")

# Asegurarnos que la carpeta existe
os.makedirs(DATA_FOLDER, exist_ok=True)

# ------------------ FUNCIONES AUXILIARES ------------------

def sincronizar_archivos():
    """
    Sincroniza todos los productos de SQLite con los archivos TXT, JSON y CSV
    """
    productos = inv.obtener_productos()  # Trae todos los productos de la base de datos

    # TXT
    with open(TXT_FILE, "w", encoding="utf-8") as f:
        for p in productos:
            f.write(f"{p.nombre},{p.cantidad},{p.precio}\n")

    # JSON
    data_json = [{"nombre": p.nombre, "cantidad": p.cantidad, "precio": p.precio} for p in productos]
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data_json, f, indent=4)

    # CSV
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
        # Convertir cantidad y precio a números
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
            # Convertimos cantidad y precio a números
            productos.append({
                "nombre": row.get("nombre", ""),
                "cantidad": int(row.get("cantidad", 0)),
                "precio": float(row.get("precio", 0.0))
            })
        return productos

# ------------------ RUTAS ------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# Página de productos con SQLite y sincronización
@app.route("/productos", methods=["GET", "POST"])
def productos():
    if request.method == "POST" and "add" in request.form:
        nombre = request.form["nombre"]
        cantidad = int(request.form["cantidad"])
        precio = float(request.form["precio"])

        # Guardar en SQLite
        inv.agregar_producto(nombre, cantidad, precio)
        # Sincronizar archivos con todos los productos
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
    sincronizar_archivos()  # Mantener archivos actualizados
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

# ------------------ NUEVAS RUTAS PARA ARCHIVOS ------------------

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

# ------------------ EJECUTAR APP ------------------
if __name__ == "__main__":
    # Sincronizar archivos al iniciar la app
    sincronizar_archivos()
    app.run(debug=True)