from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)

#KONFIGURASI

app.secret_key = "kunci-rahasia-helpdesk-kemenag"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

DATABASE = "database.db"

# =====================================================
# ADMIN KHUSUS YANG BOLEH MENGELOLA LAPORAN
# =====================================================

ADMIN_LAPORAN = [
    "Emy Edowar",
    "Robby foreth",
    "Dahlan"
]

#DATABASE

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    # tabel Pengguna
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pengguna (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nama TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
        
    """)

    # Tabel Laporan
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS laporan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            judul TEXT NOT NULL,
            deskripsi TEXT NOT NULL,
            status TEXT DEFAULT 'Menunggu',
            tanggal TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES pengguna(id)
        );

        
    """)

    conn.commit()
    conn.close()


#User Login
class User(UserMixin):
    def __init__(self, id, username, nama, role):
        self.id = id
        self.username = username
        self.nama = nama
        self.role = role


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM pengguna WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if user:
        return User(
            user["id"],
            user["username"],
            user["nama"],
            user["role"],
        )
    return None

# =====================================================
# PEMBATASAN AKSES ADMIN LAPORAN
# =====================================================

def admin_laporan_required(function):
    @wraps(function)
    @login_required
    def decorated_function(*args, **kwargs):

        if current_user.username not in ADMIN_LAPORAN:
            flash(
                "Anda tidak memiliki izin untuk mengelola laporan.",
                "danger"
            )
            return redirect(url_for("index"))

        return function(*args, **kwargs)

    return decorated_function

#Membuat akun admin jika belum ada
init_db()
conn = get_db()
admin = conn.execute(
    "SELECT * FROM pengguna WHERE username = ?",
    ("admin",),
).fetchone()

if not admin:
    conn.execute(
        """
        INSERT INTO pengguna (username, password, nama, role)
        VALUES (?, ?, ?, ?)
        """,
        (
            "admin",
            generate_password_hash("admin123"),
            "Administrator",
            "admin",
        ),
    )
    conn.commit()

conn.close()

# ==============================
# HALAMAN LOGIN
# ==============================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM pengguna WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        # Username tidak ditemukan
        if user is None:
            flash("Password atau username salah!", "danger")
            return redirect(url_for("login"))

        # Password salah
        if not check_password_hash(user["password"], password):
            flash("Password atau username salah!", "danger")
            return redirect(url_for("login"))

        # Login berhasil
        user_obj = User(
            id=user["id"],
            username=user["username"],
            nama=user["nama"],
            role=user["role"]
        )

        login_user(user_obj)

        flash("Login berhasil!", "success")

        # Jika admin
        if user["role"] == "admin":
            return redirect(url_for("admin"))

        # Jika user biasa
        return redirect(url_for("index"))

    return render_template("login.html")


# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash("Anda telah logout.", "success")

    return redirect(url_for("login"))


# ==============================
# HALAMAN UTAMA
# ==============================

@app.route("/")
@login_required
def index():

    conn = get_db()

    if current_user.role == "admin":

        total = conn.execute(
            "SELECT COUNT(*) FROM laporan"
        ).fetchone()[0]

        menunggu = conn.execute(
            "SELECT COUNT(*) FROM laporan WHERE status='Menunggu'"
        ).fetchone()[0]

        diproses = conn.execute(
            "SELECT COUNT(*) FROM laporan WHERE status='Diproses'"
        ).fetchone()[0]

    else:

        total = conn.execute(
            "SELECT COUNT(*) FROM laporan WHERE user_id=?",
            (current_user.id,)
        ).fetchone()[0]

        menunggu = conn.execute(
            """
            SELECT COUNT(*) FROM laporan
            WHERE user_id=? AND status='Menunggu'
            """,
            (current_user.id,)
        ).fetchone()[0]

        diproses = conn.execute(
            """
            SELECT COUNT(*) FROM laporan
            WHERE user_id=? AND status='Diproses'
            """,
            (current_user.id,)
        ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        total=total,
        menunggu=menunggu,
        diproses=diproses
    )


# ==============================
# REGISTER AKUN
# ==============================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        nama = request.form["nama"]

        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO pengguna
                (username, password, nama, role)
                VALUES (?, ?, ?, ?)
            """, (
                username,
                hashed_password,
                nama,
                "user"
            ))

            conn.commit()

            flash(
                "Akun berhasil dibuat. Silakan login.",
                "success"
            )

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            conn.rollback()
            flash("Username sudah digunakan.", "danger")
        finally:
            conn.close()

    return render_template("register.html")


# ==============================
# BUAT LAPORAN
# ==============================

@app.route("/laporan", methods=["GET", "POST"])
@login_required
def laporan():

    if request.method == "POST":

        judul = request.form["judul"]
        deskripsi = request.form["deskripsi"]

        tanggal = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()

        conn.execute("""
            INSERT INTO laporan
            (user_id, judul, deskripsi, status, tanggal)
            VALUES (?, ?, ?, ?, ?)
        """, (
            current_user.id,
            judul,
            deskripsi,
            "Menunggu",
            tanggal
        ))

        conn.commit()
        conn.close()

        flash("Laporan berhasil dikirim.","success")

        return redirect(url_for("index"))

    return render_template("laporan.html")


# ==============================
# ADMIN
# ==============================

@app.route("/admin")

@admin_laporan_required
def admin():

    conn = get_db()

    laporan_data = conn.execute("""
        SELECT
            laporan.id,
            laporan.user_id,
            laporan.judul,
            laporan.deskripsi,
            laporan.status,
            laporan.tanggal,
            pengguna.nama,
            pengguna.username
        FROM laporan
        LEFT JOIN pengguna
        ON laporan.user_id = pengguna.id
        ORDER BY laporan.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        laporan=laporan_data
    )

@app.route("/update_status/<int:id>", methods=["POST"])
@admin_laporan_required
def update_status(id):

    status = request.form.get("status")

    #Status yang diperbolehkan
    status_valid = [
        "Menunggu",
        "Diproses",
        "Selesai",
        "Ditolak"
    ]

    if status not in status_valid:
        flash("Status tidak valid.", "danger")
        return redirect(url_for("admin"))

    conn = get_db()

    #Cek apakah laporan tersedia
    laporan = conn.execute("""
        SELECT id
        FROM laporan
        WHERE id = ?
    """, (id,)).fetchone()

    if laporan is None:
        conn.close()
        flash("Laporan tidak ditemukan.", "danger")
        return redirect(url_for("admin"))
        
    #update status laporan
    conn.execute("""
        UPDATE laporan
        SET status = ? 
        WHERE id = ?
    """, (status, id))

    conn.commit()
    conn.close()

    flash("Status laporan berhasil diperbarui.", "success")

    return redirect(url_for("admin"))

    

    conn = get_db()

    laporan_data = conn.execute("""
        SELECT
            laporan.*,
            pengguna.nama,
            pengguna.username
        FROM laporan
        JOIN pengguna
        ON laporan.user_id = pengguna.id
        ORDER BY laporan.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        laporan=laporan_data
    )
@app.route("/hapus_laporan/<int:id>", methods=["POST"])
@admin_laporan_required
def hapus_laporan(id):
    conn = get_db()

    try:
        # Cek apakah laporan ada
        laporan = conn.execute(
            "SELECT id FROM laporan WHERE id = ?",
            (id,)
        ).fetchone()

        if laporan is None:
            flash("Laporan tidak ditemukan.", "danger")
            return redirect(url_for("admin"))

        # Hapus laporan
        conn.execute(
            "DELETE FROM laporan WHERE id = ?",
            (id,)
        )

        conn.commit()

        flash("Laporan berhasil dihapus.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Gagal menghapus laporan: {e}", "danger")

    finally:
        conn.close()

    return redirect(url_for("admin"))


# ==============================
# JALANKAN APLIKASI
# ==============================

if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS laporan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            kategori TEXT NOT NULL,
            judul TEXT NOT NULL,
            deskripsi TEXT NOT NULL,
            prioritas TEXT NOT NULL,
            status TEXT DEFAULT 'Menunggu',
            tanggal TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM laporan"
    ).fetchone()[0]

    menunggu = conn.execute(
        "SELECT COUNT(*) FROM laporan WHERE status = 'Menunggu'"
    ).fetchone()[0]

    diproses = conn.execute(
        "SELECT COUNT(*) FROM laporan WHERE status = 'Diproses'"
    ).fetchone()[0]

    selesai = conn.execute(
        "SELECT COUNT(*) FROM laporan WHERE status = 'Selesai'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        total=total,
        menunggu=menunggu,
        diproses=diproses,
        selesai=selesai
    )


@app.route("/laporan", methods=["GET", "POST"])
def laporan():
    if request.method == "POST":
        nama = request.form["nama"]
        kategori = request.form["kategori"]
        judul = request.form["judul"]
        deskripsi = request.form["deskripsi"]
        prioritas = request.form["prioritas"]

        tanggal = datetime.now().strftime("%d-%m-%Y %H:%M")

        conn = get_db_connection()

        conn.execute("""
            INSERT INTO laporan
            (nama, kategori, judul, deskripsi, prioritas, status, tanggal)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            nama,
            kategori,
            judul,
            deskripsi,
            prioritas,
            "Menunggu",
            tanggal
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("laporan"))

    return render_template("laporan.html")


@app.route("/admin")
@login_required
def admin():
    conn = get_db()

    laporan_data = conn.execute("""
        SELECT
            laporan.id,
            laporan.user_id,
            laporan.judul,
            laporan.deskripsi,
            laporan.kategori,
            laporan.prioritas,
            laporan.status,
            laporan.tanggal,
            pengguna.nama,
            pengguna.username
        FROM laporan
        LEFT JOIN pengguna
            ON laporan.user_id = pengguna.id
        ORDER BY laporan.id ASC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        laporan_data=laporan_data
    )


@app.route("/update_status/<int:id>", methods=["POST"])
def update_status(id):
    status = request.form["status"]

    conn = get_db_connection()

    conn.execute(
        "UPDATE laporan SET status = ? WHERE id = ?",
        (status, id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

@app.route("/hapus_laporan/<int:id>", methods=["POST"])
@login_required
def hapus_laporan(id):
    conn = get_db()

    try:
        # Hapus laporan berdasarkan ID
        conn.execute(
            "DELETE FROM laporan WHERE id = ?",
            (id,)
        )

        conn.commit()

        flash("Laporan berhasil dihapus.", "success")

    except Exception as e:
        conn.rollback()

        flash(
            "Gagal menghapus laporan: " + str(e),
            "danger"
        )

    finally:
        conn.close()

    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )