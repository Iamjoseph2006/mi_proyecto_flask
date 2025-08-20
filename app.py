from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", title="Inicio")

@app.route("/about")
def about():
    return render_template("about.html", title="Acerca de")

if __name__ == "__main__":
    app.run(debug=True)