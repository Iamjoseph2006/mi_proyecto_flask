from flask import Flask, render_template, request, redirect, url_for, flash
from inventario.inventario import Inventario  # Importa la clase Inventario desde la carpeta inventario

app = Flask(__name__)
app.secret_key = "mi_clave_secreta"  # Necesario para flash messages

# Crear instancia global de inventario
inv = Inventario()

# Página de inicio
@app.route("/")
def index():
    return render_template("index.html")

# Página acerca de
@app.route("/about")
def about():
    return render_template("about.html")

# Página de productos
@app.route("/productos", methods=["GET", "POST"])
def productos():
    # Añadir producto
    if request.method == "POST" and "add" in request.form:
        nombre = request.form["nombre"]
        cantidad = int(request.form["cantidad"])
        precio = float(request.form["precio"])
        inv.agregar_producto(nombre, cantidad, precio)
        flash("✅ Producto añadido con éxito", "success")
        return redirect(url_for("productos"))

    # Buscar por nombre (GET)
    buscar_nombre = request.args.get("buscar")
    if buscar_nombre:
        productos = [p for p in inv.obtener_productos() if buscar_nombre.lower() in p.nombre.lower()]
    else:
        productos = inv.obtener_productos()

    return render_template("productos.html", productos=productos)

# Eliminar producto
@app.route("/eliminar/<int:id_producto>")
def eliminar(id_producto):
    inv.eliminar_producto(id_producto)
    flash("🗑️ Producto eliminado", "danger")
    return redirect(url_for("productos"))

# Actualizar producto
@app.route("/actualizar/<int:id_producto>", methods=["POST"])
def actualizar(id_producto):
    cantidad = int(request.form["cantidad"])
    precio = float(request.form["precio"])
    inv.actualizar_producto(id_producto, cantidad=cantidad, precio=precio)
    flash("✏️ Producto actualizado", "info")
    return redirect(url_for("productos"))

# Editar producto
@app.route("/editar/<int:id_producto>")
def editar(id_producto):
    productos = inv.obtener_productos()
    producto = next((p for p in productos if p.id_producto == id_producto), None)
    if producto is None:
        flash("❌ Producto no encontrado", "warning")
        return redirect(url_for("productos"))
    return render_template("editar.html", producto=producto)


# Ejecutar app
if __name__ == "__main__":
    app.run(debug=True)