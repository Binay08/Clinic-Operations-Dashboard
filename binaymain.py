"""
CE 4 - Clinic Operations: Doctor Rostering, Patient Consultations & Clinical Log Dashboard
Registration Number: 25SSDS415012

Single-file Tkinter + SQLite application.
Run: python main.py
The database file is created automatically in the same folder as this script.
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).resolve().with_name("Clinical_Operations.db")


# ============================================================
# DATABASE LAYER
# ============================================================

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self.create_tables()
        self.seed_if_empty()

    def connect(self):
        # SQLite foreign keys must be enabled on every connection.
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_tables(self):
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS doctors (
                    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    specialty TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS consultations (
                    consultation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doctor_id INTEGER NOT NULL,
                    patient_name TEXT NOT NULL,
                    visit_date TEXT NOT NULL,
                    FOREIGN KEY (doctor_id)
                        REFERENCES doctors(doctor_id)
                        ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clinical_notes (
                    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consultation_id INTEGER NOT NULL,
                    diagnosis TEXT NOT NULL,
                    consultation_fee REAL NOT NULL CHECK (consultation_fee >= 0),
                    FOREIGN KEY (consultation_id)
                        REFERENCES consultations(consultation_id)
                        ON DELETE CASCADE
                )
            """)

    def seed_if_empty(self):
        with self.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
            if count == 0:
                doctors = [
                    ("Dr. Aditi Sharma", "Cardiology"),
                    ("Dr. Rahul Mehta", "Orthopedics"),
                    ("Dr. Neha Iyer", "Dermatology"),
                ]
                conn.executemany(
                    "INSERT INTO doctors (name, specialty) VALUES (?, ?)", doctors
                )
                doctor_ids = {
                    name: doctor_id
                    for doctor_id, name in conn.execute(
                        "SELECT doctor_id, name FROM doctors"
                    ).fetchall()
                }
                consultations = [
                    (doctor_ids["Dr. Aditi Sharma"], "Arjun Rao", "2026-11-10"),
                    (doctor_ids["Dr. Rahul Mehta"], "Meera Nair", "2026-11-10"),
                    (doctor_ids["Dr. Neha Iyer"], "Kabir Singh", "2026-11-11"),
                ]
                conn.executemany(
                    """INSERT INTO consultations
                       (doctor_id, patient_name, visit_date)
                       VALUES (?, ?, ?)""",
                    consultations,
                )
                consultation_ids = [
                    row[0] for row in conn.execute(
                        "SELECT consultation_id FROM consultations ORDER BY consultation_id"
                    ).fetchall()
                ]
                notes = [
                    (consultation_ids[0], "Routine cardiac evaluation", 800.00),
                    (consultation_ids[1], "Knee pain assessment", 650.00),
                    (consultation_ids[2], "Skin allergy review", 500.00),
                ]
                conn.executemany(
                    """INSERT INTO clinical_notes
                       (consultation_id, diagnosis, consultation_fee)
                       VALUES (?, ?, ?)""",
                    notes,
                )

    def add_record(self, doctor_name, specialty, patient_name, diagnosis, fee):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT doctor_id FROM doctors WHERE name = ?",
                (doctor_name,)
            ).fetchone()

            if row:
                doctor_id = row[0]
                # Update specialty only when a non-empty new value is provided.
                conn.execute(
                    "UPDATE doctors SET specialty = ? WHERE doctor_id = ?",
                    (specialty, doctor_id)
                )
            else:
                cur = conn.execute(
                    "INSERT INTO doctors (name, specialty) VALUES (?, ?)",
                    (doctor_name, specialty)
                )
                doctor_id = cur.lastrowid

            cur = conn.execute(
                """INSERT INTO consultations
                   (doctor_id, patient_name, visit_date)
                   VALUES (?, ?, ?)""",
                (doctor_id, patient_name, date.today().isoformat())
            )
            consultation_id = cur.lastrowid

            conn.execute(
                """INSERT INTO clinical_notes
                   (consultation_id, diagnosis, consultation_fee)
                   VALUES (?, ?, ?)""",
                (consultation_id, diagnosis, fee)
            )

    def fetch_joined(self):
        with self.connect() as conn:
            return conn.execute("""
                SELECT c.consultation_id, d.name, d.specialty,
                       c.patient_name, c.visit_date,
                       n.note_id, n.diagnosis, n.consultation_fee
                FROM consultations c
                JOIN doctors d ON d.doctor_id = c.doctor_id
                JOIN clinical_notes n ON n.consultation_id = c.consultation_id
                ORDER BY c.consultation_id
            """).fetchall()

    def fetch_table(self, table):
        allowed = {"doctors", "consultations", "clinical_notes"}
        if table not in allowed:
            raise ValueError("Invalid table name")
        with self.connect() as conn:
            return conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()

    def get_delete_options(self, target):
        queries = {
            "Doctor": """
                SELECT doctor_id, 'ID ' || doctor_id || ' - ' || name
                FROM doctors ORDER BY doctor_id
            """,
            "Consultation": """
                SELECT consultation_id,
                       'ID ' || consultation_id || ' - ' || patient_name
                       || ' (' || visit_date || ')'
                FROM consultations ORDER BY consultation_id
            """,
            "Clinical Note": """
                SELECT note_id,
                       'ID ' || note_id || ' - ' || diagnosis
                FROM clinical_notes ORDER BY note_id
            """,
        }
        with self.connect() as conn:
            return conn.execute(queries[target]).fetchall()

    def delete_record(self, target, record_id):
        table_and_key = {
            "Doctor": ("doctors", "doctor_id"),
            "Consultation": ("consultations", "consultation_id"),
            "Clinical Note": ("clinical_notes", "note_id"),
        }
        table, key = table_and_key[target]
        with self.connect() as conn:
            conn.execute(f"DELETE FROM {table} WHERE {key} = ?", (record_id,))


# ============================================================
# TKINTER GUI
# ============================================================

class ClinicDashboard:
    def __init__(self, root):
        self.root = root
        self.db = Database()
        self.root.title("Clinic Operations Dashboard")
        self.root.geometry("1320x820")
        self.root.minsize(1050, 680)
        self.root.configure(bg="#edf2f7")

        self.doctor_var = tk.StringVar()
        self.specialty_var = tk.StringVar()
        self.patient_var = tk.StringVar()
        self.diagnosis_var = tk.StringVar()
        self.fee_var = tk.StringVar()
        self.delete_type_var = tk.StringVar(value="Doctor")
        self.delete_record_var = tk.StringVar()
        self.delete_options = []

        self.build_interface()
        self.refresh_all()

    def build_interface(self):
        header = tk.Frame(self.root, bg="#17365d", height=72)
        header.pack(fill="x")
        tk.Label(
            header,
            text="CLINIC OPERATIONS DASHBOARD",
            font=("Arial", 21, "bold"),
            bg="#17365d",
            fg="white",
        ).pack(side="left", padx=24, pady=18)
        tk.Label(
            header,
            text="CE 4  |  Reg. No.: 25SSDS415012",
            font=("Arial", 11, "bold"),
            bg="#17365d",
            fg="#dbeafe",
        ).pack(side="right", padx=24)

        content = tk.Frame(self.root, bg="#edf2f7")
        content.pack(fill="both", expand=True, padx=14, pady=12)

        # ---------------- Insert panel ----------------
        insert = ttk.LabelFrame(content, text="Operations Insert Panel", padding=12)
        insert.pack(fill="x", pady=(0, 10))

        fields = [
            ("Doctor Name", self.doctor_var),
            ("Specialty", self.specialty_var),
            ("Patient Name", self.patient_var),
            ("Diagnosis / Clinical Note", self.diagnosis_var),
            ("Consultation Fee (₹)", self.fee_var),
        ]
        for index, (label, variable) in enumerate(fields):
            row, col = divmod(index, 3)
            cell = tk.Frame(insert)
            cell.grid(row=row, column=col, padx=10, pady=7, sticky="ew")
            ttk.Label(cell, text=label).pack(anchor="w")
            ttk.Entry(cell, textvariable=variable, width=34).pack(fill="x", pady=(3, 0))
            insert.columnconfigure(col, weight=1)

        ttk.Button(
            insert, text="Add Record", command=self.add_record
        ).grid(row=2, column=0, padx=10, pady=8, sticky="w")
        ttk.Button(
            insert, text="Clear Inputs", command=self.clear_inputs
        ).grid(row=2, column=1, padx=10, pady=8, sticky="w")

        # ---------------- Delete panel ----------------
        delete = ttk.LabelFrame(content, text="Operations Delete Panel", padding=12)
        delete.pack(fill="x", pady=(0, 10))

        ttk.Label(delete, text="Select record type:").grid(
            row=0, column=0, padx=8, pady=6, sticky="w"
        )
        self.delete_type_combo = ttk.Combobox(
            delete,
            textvariable=self.delete_type_var,
            values=("Doctor", "Consultation", "Clinical Note"),
            state="readonly",
            width=22,
        )
        self.delete_type_combo.grid(row=0, column=1, padx=8, pady=6, sticky="w")
        self.delete_type_combo.bind("<<ComboboxSelected>>", self.update_delete_options)

        ttk.Label(delete, text="Select record:").grid(
            row=0, column=2, padx=8, pady=6, sticky="w"
        )
        self.delete_record_combo = ttk.Combobox(
            delete, textvariable=self.delete_record_var, state="readonly", width=48
        )
        self.delete_record_combo.grid(row=0, column=3, padx=8, pady=6, sticky="w")
        ttk.Button(
            delete, text="Delete Selected", command=self.delete_selected
        ).grid(row=0, column=4, padx=10, pady=6)

        # ---------------- Tabbed display ----------------
        display = ttk.LabelFrame(content, text="Live Database Views", padding=8)
        display.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(display)
        self.notebook.pack(fill="both", expand=True)

        self.tree_specs = {
            "Master Clinical Operations Desk": (
                "joined",
                ("Consultation ID", "Doctor Name", "Specialty", "Patient Name",
                 "Visit Date", "Note ID", "Diagnosis", "Consultation Fee"),
                (100, 170, 130, 150, 110, 75, 260, 130),
            ),
            "Doctors": (
                "doctors",
                ("Doctor ID", "Name", "Specialty"),
                (100, 240, 220),
            ),
            "Consultations": (
                "consultations",
                ("Consultation ID", "Doctor ID", "Patient Name", "Visit Date"),
                (130, 100, 230, 150),
            ),
            "Clinical Notes": (
                "clinical_notes",
                ("Note ID", "Consultation ID", "Diagnosis", "Consultation Fee"),
                (100, 140, 300, 150),
            ),
        }
        self.trees = {}
        for tab_name, (source, columns, widths) in self.tree_specs.items():
            frame = ttk.Frame(self.notebook, padding=6)
            self.notebook.add(frame, text=tab_name)
            tree = ttk.Treeview(frame, columns=columns, show="headings")
            yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
            for col, width in zip(columns, widths):
                tree.heading(col, text=col)
                tree.column(col, width=width, minwidth=70, anchor="center")
            tree.grid(row=0, column=0, sticky="nsew")
            yscroll.grid(row=0, column=1, sticky="ns")
            xscroll.grid(row=1, column=0, sticky="ew")
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            self.trees[source] = tree

        footer = tk.Label(
            self.root,
            text="SQLite database with foreign keys and cascading deletes enabled",
            bg="#17365d",
            fg="white",
            font=("Arial", 9),
            pady=6,
        )
        footer.pack(fill="x")

    def add_record(self):
        doctor = self.doctor_var.get().strip()
        specialty = self.specialty_var.get().strip()
        patient = self.patient_var.get().strip()
        diagnosis = self.diagnosis_var.get().strip()
        fee_text = self.fee_var.get().strip()

        if not all((doctor, specialty, patient, diagnosis, fee_text)):
            messagebox.showerror("Input Error", "Please fill in all fields.")
            return

        try:
            fee = float(fee_text)
            if fee < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid Fee",
                "Consultation fee must be a valid non-negative number."
            )
            return

        try:
            self.db.add_record(doctor, specialty, patient, diagnosis, fee)
            messagebox.showinfo("Success", "Consultation and clinical note added.")
            self.clear_inputs()
            self.refresh_all()
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", str(error))

    def clear_inputs(self):
        for variable in (
            self.doctor_var, self.specialty_var, self.patient_var,
            self.diagnosis_var, self.fee_var
        ):
            variable.set("")

    def update_delete_options(self, _event=None):
        target = self.delete_type_var.get()
        self.delete_options = self.db.get_delete_options(target)
        labels = [label for _record_id, label in self.delete_options]
        self.delete_record_combo["values"] = labels
        self.delete_record_var.set(labels[0] if labels else "")

    def delete_selected(self):
        target = self.delete_type_var.get()
        selected_label = self.delete_record_var.get()
        selected_id = next(
            (record_id for record_id, label in self.delete_options
             if label == selected_label),
            None
        )
        if selected_id is None:
            messagebox.showwarning("Selection Required", "Please select a valid record.")
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete the selected {target.lower()}?\n"
            "Dependent records will also be deleted when cascading rules apply."
        )
        if not confirm:
            return

        try:
            self.db.delete_record(target, selected_id)
            messagebox.showinfo("Success", f"{target} deleted successfully.")
            self.refresh_all()
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", str(error))

    def populate_tree(self, tree, rows):
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", "end", values=row)

    def refresh_all(self):
        self.populate_tree(self.trees["joined"], self.db.fetch_joined())
        for table in ("doctors", "consultations", "clinical_notes"):
            self.populate_tree(self.trees[table], self.db.fetch_table(table))
        self.update_delete_options()


if __name__ == "__main__":
    root = tk.Tk()
    app = ClinicDashboard(root)
    root.mainloop()
