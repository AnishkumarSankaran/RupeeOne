import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import sqlite3
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
import shutil # For file operations in backup/restore

# --- Database Management Class ---
class DatabaseManager:
    """Handles all interactions with the SQLite database."""
    def __init__(self, db_name="expenses.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            print(f"Connected to database: {self.db_name}")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to connect to database: {e}")
            self.conn = None
            self.cursor = None

    def _create_tables(self):
        """Creates the 'expenses', 'budgets', 'income', and 'categories' tables if they don't already exist."""
        if self.cursor:
            try:
                # Expenses table
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS expenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        category TEXT NOT NULL,
                        amount REAL NOT NULL,
                        description TEXT
                    )
                ''')
                # Overall Monthly Budgets table
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS budgets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        month_year TEXT UNIQUE NOT NULL, -- e.g., '2025-07'
                        budget_amount REAL NOT NULL
                    )
                ''')
                # Income table
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS income (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        source TEXT NOT NULL,
                        amount REAL NOT NULL,
                        description TEXT
                    )
                ''')
                # Categories table
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL
                    )
                ''')
                self.conn.commit()
                print("Tables 'expenses', 'budgets', 'income', 'categories' checked/created successfully.")

                # Add some default categories if the table is empty
                self.cursor.execute("SELECT COUNT(*) FROM categories")
                if self.cursor.fetchone()[0] == 0:
                    default_categories = [
                        ("Food",), ("Transport",), ("Utilities",), ("Rent",),
                        ("Entertainment",), ("Shopping",), ("Healthcare",),
                        ("Education",), ("Salary",), ("Freelance",), ("Investments",)
                    ]
                    self.cursor.executemany("INSERT INTO categories (name) VALUES (?)", default_categories)
                    self.conn.commit()
                    print("Default categories added.")

            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to create tables: {e}")
        else:
            print("No database connection to create tables.")

    def add_expense(self, date, category, amount, description):
        """Inserts a new expense record into the database."""
        if not self.cursor: return False
        try:
            self.cursor.execute('''
                INSERT INTO expenses (date, category, amount, description)
                VALUES (?, ?, ?, ?)
            ''', (date, category, amount, description))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to add expense: {e}")
            return False

    def fetch_expenses(self, start_date=None, end_date=None, category=None, year=None, month_year=None, keyword=None):
        """Fetches expense records with optional date, category, year, month_year, and keyword filters."""
        if not self.cursor: return []
        query = "SELECT * FROM expenses WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if category and category != "All Categories": # Filter by specific category
            query += " AND category = ?"
            params.append(category)
        if year and year != "All Years": # Filter by specific year
            query += " AND STRFTIME('%Y', date) = ?"
            params.append(str(year))
        if month_year: # For specific YYYY-MM
            query += " AND STRFTIME('%Y-%m', date) = ?"
            params.append(month_year)
        if keyword:
            query += " AND (description LIKE ? OR category LIKE ?)"
            params.append(f"%{keyword}%")
            params.append(f"%{keyword}%")


        query += " ORDER BY date DESC"

        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch expenses: {e}")
            return []

    def fetch_expenses_by_month_year(self, month_year):
        """Fetches expenses for a specific 'YYYY-MM' period."""
        return self.fetch_expenses(month_year=month_year)

    def update_expense(self, expense_id, date, category, amount, description):
        """Updates an existing expense record."""
        if not self.cursor: return False
        try:
            self.cursor.execute('''
                UPDATE expenses
                SET date=?, category=?, amount=?, description=?
                WHERE id=?
            ''', (date, category, amount, description, expense_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to update expense: {e}")
            return False

    def delete_expense(self, expense_id):
        """Deletes an expense record by its ID."""
        if not self.cursor: return False
        try:
            self.cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete expense: {e}")
            return False

    def set_monthly_budget(self, month_year, amount):
        """Sets or updates the budget for a given month and year."""
        if not self.cursor: return False
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO budgets (month_year, budget_amount)
                VALUES (?, ?)
            ''', (month_year, amount))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to set budget: {e}")
            return False

    def get_monthly_budget(self, month_year):
        """Retrieves the budget for a given month and year."""
        if not self.cursor: return 0.0
        try:
            self.cursor.execute("SELECT budget_amount FROM budgets WHERE month_year = ?", (month_year,))
            result = self.cursor.fetchone()
            return result[0] if result else 0.0
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to get budget: {e}")
            return 0.0

    # Income Management
    def add_income(self, date, source, amount, description):
        """Inserts a new income record into the database."""
        if not self.cursor: return False
        try:
            self.cursor.execute('''
                INSERT INTO income (date, source, amount, description)
                VALUES (?, ?, ?, ?)
            ''', (date, source, amount, description))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to add income: {e}")
            return False

    def fetch_income(self, start_date=None, end_date=None, source=None, year=None, month_year=None, keyword=None):
        """Fetches income records with optional filters."""
        if not self.cursor: return []
        query = "SELECT * FROM income WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if source:
            query += " AND source LIKE ?"
            params.append(f"%{source}%")
        if year:
            query += " AND STRFTIME('%Y', date) = ?"
            params.append(str(year))
        if month_year:
            query += " AND STRFTIME('%Y-%m', date) = ?"
            params.append(month_year)
        if keyword:
            query += " AND (description LIKE ? OR source LIKE ?)"
            params.append(f"%{keyword}%")
            params.append(f"%{keyword}%")

        query += " ORDER BY date DESC"
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch income: {e}")
            return []

    def update_income(self, income_id, date, source, amount, description):
        """Updates an existing income record."""
        if not self.cursor: return False
        try:
            self.cursor.execute('''
                UPDATE income
                SET date=?, source=?, amount=?, description=?
                WHERE id=?
            ''', (date, source, amount, description, income_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to update income: {e}")
            return False

    def delete_income(self, income_id):
        """Deletes an income record by its ID."""
        if not self.cursor: return False
        try:
            self.cursor.execute("DELETE FROM income WHERE id = ?", (income_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete income: {e}")
            return False

    # Category Management
    def add_category(self, category_name):
        """Adds a new category to the categories table."""
        if not self.cursor: return False
        try:
            self.cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError: # Category already exists
            messagebox.showwarning("Duplicate Category", f"Category '{category_name}' already exists.")
            return False
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to add category: {e}")
            return False

    def get_categories(self):
        """Fetches all categories from the categories table."""
        if not self.cursor: return []
        try:
            self.cursor.execute("SELECT name FROM categories ORDER BY name ASC")
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch categories: {e}")
            return []

    def update_category(self, old_name, new_name):
        """Updates an existing category name and cascades the change to expenses."""
        if not self.cursor: return False
        try:
            self.conn.execute("BEGIN TRANSACTION") # Start transaction
            self.cursor.execute("UPDATE categories SET name = ? WHERE name = ?", (new_name, old_name))
            self.cursor.execute("UPDATE expenses SET category = ? WHERE category = ?", (new_name, old_name))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            messagebox.showwarning("Duplicate Category", f"Category '{new_name}' already exists. Cannot rename.")
            self.conn.rollback()
            return False
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to update category: {e}")
            self.conn.rollback()
            return False

    def delete_category(self, category_name):
        """Deletes a category and sets associated expenses to 'Uncategorized'."""
        if not self.cursor: return False
        try:
            self.conn.execute("BEGIN TRANSACTION") # Start transaction
            # First, update expenses that use this category to 'Uncategorized'
            self.cursor.execute("UPDATE expenses SET category = 'Uncategorized' WHERE category = ?", (category_name,))
            # Then delete the category itself
            self.cursor.execute("DELETE FROM categories WHERE name = ?", (category_name,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete category: {e}")
            self.conn.rollback()
            return False

    def get_all_expense_years(self):
        """Fetches all unique years present in the expenses table."""
        if not self.cursor: return []
        try:
            self.cursor.execute("SELECT DISTINCT STRFTIME('%Y', date) FROM expenses ORDER BY date DESC")
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch expense years: {e}")
            return []

    def get_all_income_years(self):
        """Fetches all unique years present in the income table."""
        if not self.cursor: return []
        try:
            self.cursor.execute("SELECT DISTINCT STRFTIME('%Y', date) FROM income ORDER BY date DESC")
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch income years: {e}")
            return []

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

# --- Expense Tracker GUI Application Class ---
class ExpenseTrackerApp:
    """Main application class for the GUI Expense Tracker."""
    def __init__(self, master):
        self.master = master
        master.title("Personal Finance Tracker") # Updated title
        master.geometry("1200x800") # Increased size for more features
        master.minsize(900, 700) # Minimum size to prevent layout issues

        self.db = DatabaseManager()
        if not self.db.conn:
            messagebox.showerror("Initialization Error", "Could not connect to database. Exiting application.")
            master.destroy()
            return

        # --- Styling for a modern and clean look ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Colors
        self.primary_bg = "#f0f0f0" # Light gray
        self.secondary_bg = "#ffffff" # White
        self.text_color = "#333333" # Dark gray
        self.accent_green = "#4CAF50" # Green for Add/Save
        self.accent_blue = "#2196F3" # Blue for Edit
        self.accent_red = "#f44336" # Red for Delete
        self.accent_orange = "#FFC107" # Orange for Budget
        self.accent_purple = "#9C27B0" # Purple for Income
        self.accent_dark_blue = "#1976D2" # Darker blue for some buttons

        self.style.configure(".", background=self.primary_bg, foreground=self.text_color, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=self.primary_bg)
        self.style.configure("TLabelFrame", background=self.secondary_bg, foreground=self.text_color, font=("Segoe UI", 11, "bold"))
        self.style.configure("TLabel", background=self.secondary_bg, foreground=self.text_color)
        self.style.configure("TEntry", fieldbackground=self.secondary_bg, foreground=self.text_color, padding=3)
        self.style.configure("TCombobox", fieldbackground=self.secondary_bg, foreground=self.text_color)
        self.style.configure("DateEntry", fieldbackground=self.secondary_bg, foreground=self.text_color)

        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, background=self.primary_bg, foreground=self.text_color)
        self.style.map("TButton", background=[('active', '#e0e0e0')])

        # Specific button styles
        self.style.configure("Accent.TButton", background=self.accent_green, foreground="white")
        self.style.map("Accent.TButton", background=[('active', '#45a049')])

        self.style.configure("Edit.TButton", background=self.accent_blue, foreground="white")
        self.style.map("Edit.TButton", background=[('active', '#1976D2')])

        self.style.configure("Delete.TButton", background=self.accent_red, foreground="white")
        self.style.map("Delete.TButton", background=[('active', '#d32f2f')])

        self.style.configure("Budget.TButton", background=self.accent_orange, foreground="#333333")
        self.style.map("Budget.TButton", background=[('active', '#FFB300')])

        self.style.configure("Income.TButton", background=self.accent_purple, foreground="white")
        self.style.map("Income.TButton", background=[('active', '#7B1FA2')])

        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e0e0e0", foreground=self.text_color)
        self.style.configure("Treeview", font=("Segoe UI", 9), background=self.secondary_bg, foreground=self.text_color, fieldbackground=self.secondary_bg)
        self.style.map("Treeview", background=[('selected', self.accent_blue)], foreground=[('selected', 'white')])

        # Style for the chart display frame and no data message
        self.style.configure("ChartDisplay.TFrame", background=self.secondary_bg)
        self.style.configure("NoData.TLabel", background=self.secondary_bg, foreground="#666666", font=("Segoe UI", 12, "italic")) # Darker gray for no data

        self.selected_expense_id = None # To keep track of expense being edited
        self.selected_income_id = None  # To keep track of income being edited

        self.create_widgets()
        self.view_expenses() # Load expenses on startup
        self.update_summary_and_budget_display()
        self.update_status_bar("Welcome to your Personal Finance Tracker!")

    # --- Status Bar ---
    def update_status_bar(self, message, color="black"):
        """Updates the status bar with a message and optional color."""
        self.status_label.config(text=message, foreground=color)
        # Clear message after a few seconds
        if hasattr(self, '_status_timer'):
            self.master.after_cancel(self._status_timer)
        self._status_timer = self.master.after(5000, lambda: self.status_label.config(text=""))


    # --- GUI Creation Methods ---
    def create_widgets(self):
        """Creates and arranges all GUI elements using a tabbed interface."""
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # --- Tab 1: Expenses ---
        self.expenses_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.expenses_tab, text="Expenses")
        self._create_expenses_tab_widgets(self.expenses_tab)

        # --- Tab 2: Income ---
        self.income_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.income_tab, text="Income")
        self._create_income_tab_widgets(self.income_tab)

        # --- Tab 3: Analytics ---
        self.analytics_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_tab, text="Analytics") # Renamed from Reports
        self._create_analytics_tab_widgets(self.analytics_tab)

        # --- Tab 4: Data Management ---
        self.data_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.data_tab, text="Data")
        self._create_data_tab_widgets(self.data_tab)

        # Status Bar at the bottom
        self.status_label = ttk.Label(self.master, text="", anchor="w", background=self.primary_bg, font=("Segoe UI", 9, "italic"))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def _create_expenses_tab_widgets(self, parent_frame):
        """Widgets for the Expenses tab (Add, View, Edit, Delete, Summary, Budget)."""
        # Configure grid for parent_frame to allow expansion
        parent_frame.grid_rowconfigure(1, weight=3) # Expense list gets more space
        parent_frame.grid_rowconfigure(2, weight=1) # Summary/Budget gets less space
        parent_frame.grid_columnconfigure(0, weight=1)

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(parent_frame, text="Add/Edit Expense", padding="15 10")
        input_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1) # Allow entry widgets to expand

        # Labels and Entries
        ttk.Label(input_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", pady=4, padx=5)
        self.expense_date_entry = DateEntry(input_frame, width=27, background='darkblue',
                                    foreground='white', borderwidth=2,
                                    year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                                    date_pattern='yyyy-mm-dd', selectmode='day', font=("Segoe UI", 10))
        self.expense_date_entry.grid(row=0, column=1, pady=4, padx=5, sticky="ew")

        ttk.Label(input_frame, text="Category:").grid(row=1, column=0, sticky="w", pady=4, padx=5)
        self.expense_category_combobox = ttk.Combobox(input_frame, values=self.db.get_categories(), state="normal", font=("Segoe UI", 10))
        self.expense_category_combobox.grid(row=1, column=1, pady=4, padx=5, sticky="ew")
        self.expense_category_combobox.bind("<FocusIn>", lambda e: self.expense_category_combobox.config(values=self.db.get_categories()))
        
        ttk.Label(input_frame, text="Amount (₹):").grid(row=2, column=0, sticky="w", pady=4, padx=5)
        self.expense_amount_entry = ttk.Entry(input_frame, validate="key", validatecommand=(self.master.register(self._validate_numeric_input), '%P'))
        self.expense_amount_entry.grid(row=2, column=1, pady=4, padx=5, sticky="ew")

        ttk.Label(input_frame, text="Description:").grid(row=3, column=0, sticky="w", pady=4, padx=5)
        self.expense_description_entry = ttk.Entry(input_frame)
        self.expense_description_entry.grid(row=3, column=1, pady=4, padx=5, sticky="ew")

        # Buttons for Add/Update and Cancel Edit
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.add_update_expense_button = ttk.Button(button_frame, text="Add Expense", command=self.add_expense_gui, style="Accent.TButton")
        self.add_update_expense_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.cancel_expense_edit_button = ttk.Button(button_frame, text="Cancel Edit", command=self.cancel_expense_edit, style="TButton")
        self.cancel_expense_edit_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.cancel_expense_edit_button.grid_remove() # Hide it by default

        # --- Expense List Frame with Filters ---
        list_filter_frame = ttk.LabelFrame(parent_frame, text="All Expenses", padding="15 10")
        list_filter_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        list_filter_frame.grid_rowconfigure(2, weight=1) # Treeview row
        list_filter_frame.grid_columnconfigure(1, weight=1) # For search entry

        # Filter Controls
        filter_row = 0
        ttk.Label(list_filter_frame, text="Start Date:").grid(row=filter_row, column=0, sticky="w", padx=5, pady=2)
        self.expense_filter_start_date = DateEntry(list_filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', selectmode='day', font=("Segoe UI", 9))
        self.expense_filter_start_date.grid(row=filter_row, column=1, sticky="ew", padx=5, pady=2)
        self.expense_filter_start_date.set_date(None) # Clear initial date

        ttk.Label(list_filter_frame, text="End Date:").grid(row=filter_row, column=2, sticky="w", padx=5, pady=2)
        self.expense_filter_end_date = DateEntry(list_filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', selectmode='day', font=("Segoe UI", 9))
        self.expense_filter_end_date.grid(row=filter_row, column=3, sticky="ew", padx=5, pady=2)
        self.expense_filter_end_date.set_date(None) # Clear initial date

        filter_row += 1
        ttk.Label(list_filter_frame, text="Category:").grid(row=filter_row, column=0, sticky="w", padx=5, pady=2)
        self.expense_filter_category_combobox = ttk.Combobox(list_filter_frame, values=["All Categories"] + self.db.get_categories(), state="readonly", font=("Segoe UI", 9))
        self.expense_filter_category_combobox.set("All Categories")
        self.expense_filter_category_combobox.grid(row=filter_row, column=1, sticky="ew", padx=5, pady=2)
        self.expense_filter_category_combobox.bind("<FocusIn>", lambda e: self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories()))


        ttk.Label(list_filter_frame, text="Search:").grid(row=filter_row, column=2, sticky="w", padx=5, pady=2)
        self.expense_filter_keyword_entry = ttk.Entry(list_filter_frame, font=("Segoe UI", 9))
        self.expense_filter_keyword_entry.grid(row=filter_row, column=3, sticky="ew", padx=5, pady=2)
        self.expense_filter_keyword_entry.bind("<Return>", lambda e: self.apply_expense_filters()) # Apply on Enter

        filter_row += 1
        apply_filter_button = ttk.Button(list_filter_frame, text="Apply Filters", command=self.apply_expense_filters, style="TButton")
        apply_filter_button.grid(row=filter_row, column=0, columnspan=2, pady=5, padx=5, sticky="ew")
        clear_filter_button = ttk.Button(list_filter_frame, text="Clear Filters", command=self.clear_expense_filters, style="TButton")
        clear_filter_button.grid(row=filter_row, column=2, columnspan=2, pady=5, padx=5, sticky="ew")


        # Treeview (Table) to display expenses
        columns = ("ID", "Date", "Category", "Amount", "Description")
        self.expense_tree = ttk.Treeview(list_filter_frame, columns=columns, show="headings", selectmode="browse")

        self.expense_tree.heading("ID", text="ID", anchor=tk.CENTER)
        self.expense_tree.heading("Date", text="Date", anchor=tk.CENTER)
        self.expense_tree.heading("Category", text="Category", anchor=tk.CENTER)
        self.expense_tree.heading("Amount", text="Amount (₹)", anchor=tk.CENTER)
        self.expense_tree.heading("Description", text="Description", anchor=tk.CENTER)

        self.expense_tree.column("ID", width=60, anchor=tk.CENTER, stretch=tk.NO)
        self.expense_tree.column("Date", width=110, anchor=tk.CENTER, stretch=tk.NO)
        self.expense_tree.column("Category", width=130, anchor=tk.W, stretch=tk.NO)
        self.expense_tree.column("Amount", width=100, anchor=tk.E, stretch=tk.NO)
        self.expense_tree.column("Description", minwidth=150, width=250, anchor=tk.W, stretch=tk.YES) # Dynamic stretch

        self.expense_tree.grid(row=filter_row + 1, column=0, columnspan=4, sticky="nsew", pady=(10,0)) # Adjusted row
        list_filter_frame.grid_rowconfigure(filter_row + 1, weight=1) # Allow treeview to expand

        # Scrollbar for Treeview
        scrollbar = ttk.Scrollbar(list_filter_frame, orient=tk.VERTICAL, command=self.expense_tree.yview)
        self.expense_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=filter_row + 1, column=4, sticky="ns", pady=(10,0)) # Adjusted row

        # Buttons for Edit and Delete
        action_button_frame = ttk.Frame(list_filter_frame)
        action_button_frame.grid(row=filter_row + 2, column=0, columnspan=5, pady=10, sticky="ew") # Adjusted row, columnspan
        action_button_frame.grid_columnconfigure(0, weight=1)
        action_button_frame.grid_columnconfigure(1, weight=1)

        edit_button = ttk.Button(action_button_frame, text="✏️ Edit Selected", command=self.edit_expense_gui, style="Edit.TButton")
        edit_button.grid(row=0, column=0, padx=5, sticky="ew")

        delete_button = ttk.Button(action_button_frame, text="🗑️ Delete Selected", command=self.delete_expense_gui, style="Delete.TButton")
        delete_button.grid(row=0, column=1, padx=5, sticky="ew")

        # --- Summary and Overall Budget Frame ---
        summary_overall_budget_frame = ttk.LabelFrame(parent_frame, text="Monthly Summary & Overall Budget (Current Month)", padding="15 10")
        summary_overall_budget_frame.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="nsew")
        summary_overall_budget_frame.grid_columnconfigure(0, weight=1) # Category summary column
        summary_overall_budget_frame.grid_columnconfigure(1, weight=1) # Budget column

        # Overall Budget Section
        ttk.Label(summary_overall_budget_frame, text="Overall Budget for This Month:").grid(row=0, column=0, sticky="w", pady=2, padx=5, columnspan=2)
        self.budget_amount_label = ttk.Label(summary_overall_budget_frame, text="₹0.00", font=("Segoe UI", 12, "bold"))
        self.budget_amount_label.grid(row=1, column=0, sticky="w", pady=2, padx=5, columnspan=2)

        ttk.Label(summary_overall_budget_frame, text="Total Spent This Month:").grid(row=2, column=0, sticky="w", pady=2, padx=5, columnspan=2)
        self.spent_amount_label = ttk.Label(summary_overall_budget_frame, text="₹0.00", font=("Segoe UI", 12, "bold"))
        self.spent_amount_label.grid(row=3, column=0, sticky="w", pady=2, padx=5, columnspan=2)

        ttk.Label(summary_overall_budget_frame, text="Net Balance (Income - Expenses):").grid(row=4, column=0, sticky="w", pady=2, padx=5, columnspan=2)
        self.net_balance_label = ttk.Label(summary_overall_budget_frame, text="₹0.00", font=("Segoe UI", 12, "bold"))
        self.net_balance_label.grid(row=5, column=0, sticky="w", pady=2, padx=5, columnspan=2)

        ttk.Label(summary_overall_budget_frame, text="Remaining Overall Budget:").grid(row=6, column=0, sticky="w", pady=2, padx=5, columnspan=2)
        self.remaining_budget_label = ttk.Label(summary_overall_budget_frame, text="₹0.00", font=("Segoe UI", 12, "bold", "italic"))
        self.remaining_budget_label.grid(row=7, column=0, sticky="w", pady=2, padx=5, columnspan=2)
        
        # Set Overall Monthly Budget input and button
        ttk.Label(summary_overall_budget_frame, text="Set Overall Monthly Budget (₹):").grid(row=8, column=0, sticky="w", pady=5, padx=5, columnspan=2)
        set_budget_frame = ttk.Frame(summary_overall_budget_frame, style="TFrame")
        set_budget_frame.grid(row=9, column=0, sticky="ew", padx=5, columnspan=2)
        set_budget_frame.grid_columnconfigure(0, weight=1)

        self.set_budget_entry = ttk.Entry(set_budget_frame, width=20, validate="key", validatecommand=(self.master.register(self._validate_numeric_input), '%P'))
        self.set_budget_entry.grid(row=0, column=0, sticky="ew", padx=(0,5))
        set_budget_button = ttk.Button(set_budget_frame, text="Set Budget", command=self.set_budget_gui, style="Budget.TButton")
        set_budget_button.grid(row=0, column=1, sticky="ew")

        # Category Spending Breakdown (without individual budgets)
        ttk.Label(summary_overall_budget_frame, text="Category Spending This Month:").grid(row=0, column=1, sticky="nw", pady=2, padx=5) # Moved to column 1
        self.category_summary_text = tk.Text(summary_overall_budget_frame, height=10, width=40, state=tk.DISABLED, wrap=tk.WORD,
                                             background=self.secondary_bg, foreground=self.text_color, font=("Segoe UI", 9))
        self.category_summary_text.grid(row=1, column=1, rowspan=8, sticky="nsew", pady=2, padx=5) # Spans multiple rows
        summary_overall_budget_frame.grid_rowconfigure(1, weight=1) # Allow text widget to expand


    def _create_income_tab_widgets(self, parent_frame):
        """Widgets for the Income tab (Add, View, Edit, Delete Income)."""
        parent_frame.grid_rowconfigure(1, weight=3)
        parent_frame.grid_columnconfigure(0, weight=1)

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(parent_frame, text="Add/Edit Income", padding="15 10")
        input_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", pady=4, padx=5)
        self.income_date_entry = DateEntry(input_frame, width=27, background='darkblue', foreground='white', borderwidth=2,
                                    year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                                    date_pattern='yyyy-mm-dd', selectmode='day', font=("Segoe UI", 10))
        self.income_date_entry.grid(row=0, column=1, pady=4, padx=5, sticky="ew")

        ttk.Label(input_frame, text="Source:").grid(row=1, column=0, sticky="w", pady=4, padx=5)
        self.income_source_entry = ttk.Entry(input_frame)
        self.income_source_entry.grid(row=1, column=1, pady=4, padx=5, sticky="ew")
        
        ttk.Label(input_frame, text="Amount (₹):").grid(row=2, column=0, sticky="w", pady=4, padx=5)
        self.income_amount_entry = ttk.Entry(input_frame, validate="key", validatecommand=(self.master.register(self._validate_numeric_input), '%P'))
        self.income_amount_entry.grid(row=2, column=1, pady=4, padx=5, sticky="ew")

        ttk.Label(input_frame, text="Description:").grid(row=3, column=0, sticky="w", pady=4, padx=5)
        self.income_description_entry = ttk.Entry(input_frame)
        self.income_description_entry.grid(row=3, column=1, pady=4, padx=5, sticky="ew")

        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.add_update_income_button = ttk.Button(button_frame, text="Add Income", command=self.add_income_gui, style="Income.TButton")
        self.add_update_income_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.cancel_income_edit_button = ttk.Button(button_frame, text="Cancel Edit", command=self.cancel_income_edit, style="TButton")
        self.cancel_income_edit_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.cancel_income_edit_button.grid_remove()

        # --- Income List Frame with Filters ---
        income_list_filter_frame = ttk.LabelFrame(parent_frame, text="All Income", padding="15 10")
        income_list_filter_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        income_list_filter_frame.grid_rowconfigure(2, weight=1)
        income_list_filter_frame.grid_columnconfigure(1, weight=1)

        # Filter Controls for Income
        filter_row = 0
        ttk.Label(income_list_filter_frame, text="Start Date:").grid(row=filter_row, column=0, sticky="w", padx=5, pady=2)
        self.income_filter_start_date = DateEntry(income_list_filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', selectmode='day', font=("Segoe UI", 9))
        self.income_filter_start_date.grid(row=filter_row, column=1, sticky="ew", padx=5, pady=2)
        self.income_filter_start_date.set_date(None)

        ttk.Label(income_list_filter_frame, text="End Date:").grid(row=filter_row, column=2, sticky="w", padx=5, pady=2)
        self.income_filter_end_date = DateEntry(income_list_filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', selectmode='day', font=("Segoe UI", 9))
        self.income_filter_end_date.grid(row=filter_row, column=3, sticky="ew", padx=5, pady=2)
        self.income_filter_end_date.set_date(None)

        filter_row += 1
        ttk.Label(income_list_filter_frame, text="Source:").grid(row=filter_row, column=0, sticky="w", padx=5, pady=2)
        self.income_filter_source_entry = ttk.Entry(income_list_filter_frame, font=("Segoe UI", 9))
        self.income_filter_source_entry.grid(row=filter_row, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(income_list_filter_frame, text="Search:").grid(row=filter_row, column=2, sticky="w", padx=5, pady=2)
        self.income_filter_keyword_entry = ttk.Entry(income_list_filter_frame, font=("Segoe UI", 9))
        self.income_filter_keyword_entry.grid(row=filter_row, column=3, sticky="ew", padx=5, pady=2)
        self.income_filter_keyword_entry.bind("<Return>", lambda e: self.apply_income_filters())

        filter_row += 1
        apply_filter_button = ttk.Button(income_list_filter_frame, text="Apply Filters", command=self.apply_income_filters, style="TButton")
        apply_filter_button.grid(row=filter_row, column=0, columnspan=2, pady=5, padx=5, sticky="ew")
        clear_filter_button = ttk.Button(income_list_filter_frame, text="Clear Filters", command=self.clear_income_filters, style="TButton")
        clear_filter_button.grid(row=filter_row, column=2, columnspan=2, pady=5, padx=5, sticky="ew")

        # Treeview for Income
        columns = ("ID", "Date", "Source", "Amount", "Description")
        self.income_tree = ttk.Treeview(income_list_filter_frame, columns=columns, show="headings", selectmode="browse")

        self.income_tree.heading("ID", text="ID", anchor=tk.CENTER)
        self.income_tree.heading("Date", text="Date", anchor=tk.CENTER)
        self.income_tree.heading("Source", text="Source", anchor=tk.CENTER)
        self.income_tree.heading("Amount", text="Amount (₹)", anchor=tk.CENTER)
        self.income_tree.heading("Description", text="Description", anchor=tk.CENTER)

        self.income_tree.column("ID", width=60, anchor=tk.CENTER, stretch=tk.NO)
        self.income_tree.column("Date", width=110, anchor=tk.CENTER, stretch=tk.NO)
        self.income_tree.column("Source", width=130, anchor=tk.W, stretch=tk.NO)
        self.income_tree.column("Amount", width=100, anchor=tk.E, stretch=tk.NO)
        self.income_tree.column("Description", minwidth=150, width=250, anchor=tk.W, stretch=tk.YES)

        self.income_tree.grid(row=filter_row + 1, column=0, columnspan=4, sticky="nsew", pady=(10,0))
        income_list_filter_frame.grid_rowconfigure(filter_row + 1, weight=1)

        scrollbar = ttk.Scrollbar(income_list_filter_frame, orient=tk.VERTICAL, command=self.income_tree.yview)
        self.income_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=filter_row + 1, column=4, sticky="ns", pady=(10,0))

        action_button_frame = ttk.Frame(income_list_filter_frame)
        action_button_frame.grid(row=filter_row + 2, column=0, columnspan=5, pady=10, sticky="ew")
        action_button_frame.grid_columnconfigure(0, weight=1)
        action_button_frame.grid_columnconfigure(1, weight=1)

        edit_button = ttk.Button(action_button_frame, text="✏️ Edit Selected", command=self.edit_income_gui, style="Edit.TButton")
        edit_button.grid(row=0, column=0, padx=5, sticky="ew")

        delete_button = ttk.Button(action_button_frame, text="🗑️ Delete Selected", command=self.delete_income_gui, style="Delete.TButton")
        delete_button.grid(row=0, column=1, padx=5, sticky="ew")


    def _create_analytics_tab_widgets(self, parent_frame):
        """Widgets for the Analytics tab (Charts and Filters)."""
        parent_frame.grid_rowconfigure(1, weight=1) # Chart area
        parent_frame.grid_columnconfigure(0, weight=1)

        # --- Filter Frame for Analytics ---
        filter_frame = ttk.LabelFrame(parent_frame, text="Analytics Filters", padding="15 10")
        filter_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        filter_frame.grid_columnconfigure(1, weight=1)
        filter_frame.grid_columnconfigure(3, weight=1)

        current_year = datetime.now().year
        # Generate years from 2000 to current year + 1 (for future data entry)
        self.analytics_years = sorted(list(set(self.db.get_all_expense_years() + self.db.get_all_income_years() + [str(current_year)])), reverse=True)
        self.analytics_years.insert(0, "All Years")

        self.analytics_months = [f"{i:02d}" for i in range(1, 13)] # 01, 02, ..., 12

        ttk.Label(filter_frame, text="Select Year:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.analytics_year_combobox = ttk.Combobox(filter_frame, values=self.analytics_years, state="readonly", font=("Segoe UI", 10))
        self.analytics_year_combobox.set(current_year) # Default to current year
        self.analytics_year_combobox.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_frame, text="Select Month:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.analytics_month_combobox = ttk.Combobox(filter_frame, values=["All"] + self.analytics_months, state="readonly", font=("Segoe UI", 10))
        self.analytics_month_combobox.set("All") # Default to all months
        self.analytics_month_combobox.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        
        # New: Category filter for Category Trend Chart
        ttk.Label(filter_frame, text="Select Category (for Trend):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.analytics_category_combobox = ttk.Combobox(filter_frame, values=["All Categories"] + self.db.get_categories(), state="readonly", font=("Segoe UI", 10))
        self.analytics_category_combobox.set("All Categories")
        self.analytics_category_combobox.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        self.analytics_category_combobox.bind("<FocusIn>", lambda e: self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories()))


        # Chart Type Buttons
        chart_buttons_frame = ttk.Frame(filter_frame)
        chart_buttons_frame.grid(row=3, column=0, columnspan=4, pady=10, sticky="ew")
        chart_buttons_frame.grid_columnconfigure(0, weight=1)
        chart_buttons_frame.grid_columnconfigure(1, weight=1)
        chart_buttons_frame.grid_columnconfigure(2, weight=1)
        chart_buttons_frame.grid_columnconfigure(3, weight=1) # For new category trend button

        ttk.Button(chart_buttons_frame, text="📊 Category Pie Chart", command=self.generate_pie_chart_filtered, style="Accent.TButton").grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(chart_buttons_frame, text="📈 Monthly Bar Chart", command=self.generate_bar_chart_filtered, style="Accent.TButton").grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(chart_buttons_frame, text="📉 Overall Trend Chart", command=self.generate_monthly_spending_trend_chart, style="Accent.TButton").grid(row=0, column=2, padx=5, sticky="ew")
        ttk.Button(chart_buttons_frame, text="📈 Category Trend Chart", command=self.generate_category_spending_trend_chart, style="Accent.TButton").grid(row=0, column=3, padx=5, sticky="ew")


        # --- Chart Display Frame ---
        self.chart_display_frame = ttk.Frame(parent_frame, relief="sunken", borderwidth=2, style="ChartDisplay.TFrame")
        self.chart_display_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.chart_display_frame.grid_rowconfigure(0, weight=1)
        self.chart_display_frame.grid_columnconfigure(0, weight=1)

        # Initialize figure and canvas once
        self.figure = plt.Figure(figsize=(6, 5), dpi=100, facecolor=self.secondary_bg)
        self.canvas_widget = FigureCanvasTkAgg(self.figure, master=self.chart_display_frame)
        self.canvas_widget.get_tk_widget().pack(expand=True, fill="both")
        self.no_data_label = None # To manage the "No data" label

        # Initial chart display
        self.generate_pie_chart_filtered()


    def _create_data_tab_widgets(self, parent_frame):
        """Widgets for the Data Management tab (Categories, Backup/Restore)."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(1, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1) # Allow category treeview to expand

        # --- Categories Management Frame ---
        category_frame = ttk.LabelFrame(parent_frame, text="Manage Categories", padding="15 10")
        category_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="nsew")
        category_frame.grid_columnconfigure(1, weight=1)
        category_frame.grid_rowconfigure(3, weight=1) # Treeview row

        ttk.Label(category_frame, text="Category Name:").grid(row=0, column=0, sticky="w", pady=4, padx=5)
        self.category_name_entry = ttk.Entry(category_frame)
        self.category_name_entry.grid(row=0, column=1, pady=4, padx=5, sticky="ew")

        cat_button_frame = ttk.Frame(category_frame)
        cat_button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")
        cat_button_frame.grid_columnconfigure(0, weight=1)
        cat_button_frame.grid_columnconfigure(1, weight=1)
        cat_button_frame.grid_columnconfigure(2, weight=1)

        ttk.Button(cat_button_frame, text="➕ Add Category", command=self.add_category_gui, style="Accent.TButton").grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(cat_button_frame, text="✏️ Edit Category", command=self.edit_category_gui, style="Edit.TButton").grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(cat_button_frame, text="🗑️ Delete Category", command=self.delete_category_gui, style="Delete.TButton").grid(row=0, column=2, padx=5, sticky="ew")

        # Category List Treeview
        self.category_tree = ttk.Treeview(category_frame, columns=("CategoryName",), show="headings", selectmode="browse")
        self.category_tree.heading("CategoryName", text="Category Name", anchor=tk.W)
        self.category_tree.column("CategoryName", width=200, stretch=tk.YES)
        self.category_tree.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=10)

        cat_scrollbar = ttk.Scrollbar(category_frame, orient=tk.VERTICAL, command=self.category_tree.yview)
        self.category_tree.configure(yscrollcommand=cat_scrollbar.set)
        cat_scrollbar.grid(row=3, column=2, sticky="ns", pady=10)

        # --- Backup/Restore Frame ---
        backup_restore_frame = ttk.LabelFrame(parent_frame, text="Backup / Restore Data", padding="15 10")
        backup_restore_frame.grid(row=1, column=0, padx=10, pady=(10, 5), sticky="nsew")
        backup_restore_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(backup_restore_frame, text="Backup your current data:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        ttk.Button(backup_restore_frame, text="💾 Backup Database", command=self.backup_database, style="TButton").grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(backup_restore_frame, text="Restore data from a backup file:").grid(row=2, column=0, sticky="w", pady=10, padx=5)
        ttk.Button(backup_restore_frame, text="↩️ Restore Database", command=self.restore_database, style="TButton").grid(row=3, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(backup_restore_frame, text="Note: Restoring will overwrite current data.", foreground="red", font=("Segoe UI", 9, "italic")).grid(row=4, column=0, sticky="w", padx=5, pady=2)


    # --- Event Handlers and Logic Methods ---
    def on_tab_change(self, event):
        """Handles actions when the tab is changed."""
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if selected_tab == "Analytics":
            self.update_analytics_filters_and_chart()
        elif selected_tab == "Expenses":
            self.update_summary_and_budget_display()
            self.view_expenses()
            self.expense_category_combobox.config(values=self.db.get_categories()) # Update category list
        elif selected_tab == "Income":
            self.view_income()
            self.update_summary_and_budget_display()
        elif selected_tab == "Data":
            self.view_categories() # Refresh category list in Data tab

    def _validate_numeric_input(self, P):
        """Validates if the input is a valid number (float or empty string)."""
        if P == "" or P.replace('.', '', 1).isdigit():
            return True
        return False

    def clear_expense_entries(self):
        """Clears the expense input fields and resets the add/update state."""
        self.expense_date_entry.set_date(datetime.now().date())
        self.expense_category_combobox.set('')
        self.expense_amount_entry.delete(0, tk.END)
        self.expense_description_entry.delete(0, tk.END)
        self.add_update_expense_button.config(text="➕ Add Expense", command=self.add_expense_gui, style="Accent.TButton")
        self.cancel_expense_edit_button.grid_remove()
        self.selected_expense_id = None
        self.update_status_bar("Ready to add new expense.")

    def add_expense_gui(self):
        """Handles adding a new expense from the GUI."""
        date = self.expense_date_entry.get_date().strftime("%Y-%m-%d")
        category = self.expense_category_combobox.get().strip()
        amount_str = self.expense_amount_entry.get().strip()
        description = self.expense_description_entry.get().strip()

        if not date or not category or not amount_str:
            self.update_status_bar("Error: Date, Category, and Amount are required.", "red")
            messagebox.showwarning("Input Error", "Date, Category, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.update_status_bar("Error: Amount must be positive.", "red")
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid amount.", "red")
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if self.db.add_expense(date, category, amount, description):
            self.update_status_bar("Expense added successfully!", "green")
            self.clear_expense_entries()
            self.view_expenses()
            self.update_summary_and_budget_display()
            self.update_analytics_filters_and_chart() # Update report filters with new data's years
            self.expense_category_combobox.config(values=self.db.get_categories()) # Update category list
        else:
            self.update_status_bar("Failed to add expense.", "red")
            messagebox.showerror("Error", "Failed to add expense.")

    def edit_expense_gui(self):
        """Populates input fields with selected expense for editing."""
        selected_item = self.expense_tree.selection()
        if not selected_item:
            self.update_status_bar("Please select an expense to edit.", "orange")
            messagebox.showwarning("Selection Error", "Please select an expense to edit.")
            return

        item_values = self.expense_tree.item(selected_item, 'values')
        self.selected_expense_id = item_values[0]

        self.expense_date_entry.set_date(datetime.strptime(item_values[1], "%Y-%m-%d").date())
        self.expense_category_combobox.set(item_values[2])
        self.expense_amount_entry.delete(0, tk.END)
        self.expense_amount_entry.insert(0, item_values[3].replace('₹', '').replace(',', ''))
        self.expense_description_entry.delete(0, tk.END)
        self.expense_description_entry.insert(0, item_values[4])

        self.add_update_expense_button.config(text="✔️ Save Changes", command=self.update_expense_gui, style="Edit.TButton")
        self.cancel_expense_edit_button.grid()
        self.update_status_bar(f"Editing expense ID: {self.selected_expense_id}")

    def update_expense_gui(self):
        """Handles updating an existing expense from the GUI."""
        if self.selected_expense_id is None:
            self.update_status_bar("No expense selected for update.", "red")
            messagebox.showerror("Error", "No expense selected for update.")
            return

        date = self.expense_date_entry.get_date().strftime("%Y-%m-%d")
        category = self.expense_category_combobox.get().strip()
        amount_str = self.expense_amount_entry.get().strip()
        description = self.expense_description_entry.get().strip()

        if not date or not category or not amount_str:
            self.update_status_bar("Error: Date, Category, and Amount are required.", "red")
            messagebox.showwarning("Input Error", "Date, Category, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.update_status_bar("Error: Amount must be positive.", "red")
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid amount.", "red")
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if messagebox.askyesno("Confirm Update", f"Are you sure you want to update expense ID: {self.selected_expense_id}?"):
            if self.db.update_expense(self.selected_expense_id, date, category, amount, description):
                self.update_status_bar("Expense updated successfully!", "green")
                self.clear_expense_entries()
                self.view_expenses()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.expense_category_combobox.config(values=self.db.get_categories())
            else:
                self.update_status_bar("Failed to update expense.", "red")
                messagebox.showerror("Error", "Failed to update expense.")
        else:
            self.cancel_expense_edit()

    def cancel_expense_edit(self):
        """Cancels the edit operation and reverts to add expense mode."""
        self.clear_expense_entries()
        self.update_status_bar("Expense edit canceled. Ready to add new expense.")

    def delete_expense_gui(self):
        """Handles deleting the selected expense from the GUI."""
        selected_item = self.expense_tree.selection()
        if not selected_item:
            self.update_status_bar("Please select an expense to delete.", "orange")
            messagebox.showwarning("Selection Error", "Please select an expense to delete.")
            return

        item_values = self.expense_tree.item(selected_item, 'values')
        expense_id = item_values[0]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete expense ID: {expense_id}?\nThis action cannot be undone."):
            if self.db.delete_expense(expense_id):
                self.update_status_bar("Expense deleted successfully!", "green")
                self.clear_expense_entries()
                self.view_expenses()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.expense_category_combobox.config(values=self.db.get_categories())
            else:
                self.update_status_bar("Failed to delete expense.", "red")
                messagebox.showerror("Error", "Failed to delete expense.")

    def apply_expense_filters(self):
        """Applies filters to the expense Treeview."""
        start_date_obj = self.expense_filter_start_date.get_date()
        end_date_obj = self.expense_filter_end_date.get_date()
        category = self.expense_filter_category_combobox.get()
        keyword = self.expense_filter_keyword_entry.get().strip()

        start_date = start_date_obj.strftime("%Y-%m-%d") if start_date_obj else None
        end_date = end_date_obj.strftime("%Y-%m-%d") if end_date_obj else None

        # Clear existing items
        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        expenses = self.db.fetch_expenses(start_date=start_date, end_date=end_date, category=category, keyword=keyword)

        if not expenses:
            self.expense_tree.insert("", tk.END, values=("", "", "No expenses found with these filters.", "", ""), tags=('center_text',))
            self.expense_tree.tag_configure('center_text', anchor='center')
            self.update_status_bar("No expenses found with applied filters.", "orange")
            return

        for exp in expenses:
            formatted_amount = f"₹{exp[3]:,.2f}"
            self.expense_tree.insert("", tk.END, values=(exp[0], exp[1], exp[2], formatted_amount, exp[4]))
        self.update_status_bar(f"Displayed {len(expenses)} expenses with applied filters.")

    def clear_expense_filters(self):
        """Clears all expense filters and reloads all expenses."""
        self.expense_filter_start_date.set_date(None)
        self.expense_filter_end_date.set_date(None)
        self.expense_filter_category_combobox.set("All Categories")
        self.expense_filter_keyword_entry.delete(0, tk.END)
        self.view_expenses()
        self.update_status_bar("Expense filters cleared. Showing all expenses.")


    def view_expenses(self):
        """Populates the Treeview with all expenses from the database."""
        # Clear existing items in the treeview
        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        expenses = self.db.fetch_expenses()
        if not expenses:
            self.expense_tree.insert("", tk.END, values=("", "", "No expenses recorded yet.", "", ""), tags=('center_text',))
            self.expense_tree.tag_configure('center_text', anchor='center')
            return

        for exp in expenses:
            # exp[0]=id, exp[1]=date, exp[2]=category, exp[3]=amount, exp[4]=description
            formatted_amount = f"₹{exp[3]:,.2f}" # Format amount for display
            self.expense_tree.insert("", tk.END, values=(exp[0], exp[1], exp[2], formatted_amount, exp[4]))


    def clear_income_entries(self):
        """Clears the income input fields and resets the add/update state."""
        self.income_date_entry.set_date(datetime.now().date())
        self.income_source_entry.delete(0, tk.END)
        self.income_amount_entry.delete(0, tk.END)
        self.income_description_entry.delete(0, tk.END)
        self.add_update_income_button.config(text="➕ Add Income", command=self.add_income_gui, style="Income.TButton")
        self.cancel_income_edit_button.grid_remove()
        self.selected_income_id = None
        self.update_status_bar("Ready to add new income.")

    def add_income_gui(self):
        """Handles adding new income from the GUI."""
        date = self.income_date_entry.get_date().strftime("%Y-%m-%d")
        source = self.income_source_entry.get().strip()
        amount_str = self.income_amount_entry.get().strip()
        description = self.income_description_entry.get().strip()

        if not date or not source or not amount_str:
            self.update_status_bar("Error: Date, Source, and Amount are required.", "red")
            messagebox.showwarning("Input Error", "Date, Source, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.update_status_bar("Error: Amount must be positive.", "red")
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid amount.", "red")
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if self.db.add_income(date, source, amount, description):
            self.update_status_bar("Income added successfully!", "green")
            self.clear_income_entries()
            self.view_income()
            self.update_summary_and_budget_display()
            self.update_analytics_filters_and_chart()
        else:
            self.update_status_bar("Failed to add income.", "red")
            messagebox.showerror("Error", "Failed to add income.")

    def edit_income_gui(self):
        """Populates input fields with selected income for editing."""
        selected_item = self.income_tree.selection()
        if not selected_item:
            self.update_status_bar("Please select an income entry to edit.", "orange")
            messagebox.showwarning("Selection Error", "Please select an income entry to edit.")
            return

        item_values = self.income_tree.item(selected_item, 'values')
        self.selected_income_id = item_values[0]

        self.income_date_entry.set_date(datetime.strptime(item_values[1], "%Y-%m-%d").date())
        self.income_source_entry.delete(0, tk.END)
        self.income_source_entry.insert(0, item_values[2])
        self.income_amount_entry.delete(0, tk.END)
        self.income_amount_entry.insert(0, item_values[3].replace('₹', '').replace(',', ''))
        self.income_description_entry.delete(0, tk.END)
        self.income_description_entry.insert(0, item_values[4])

        self.add_update_income_button.config(text="✔️ Save Changes", command=self.update_income_gui, style="Income.TButton")
        self.cancel_income_edit_button.grid()
        self.update_status_bar(f"Editing income ID: {self.selected_income_id}")

    def update_income_gui(self):
        """Handles updating an existing income from the GUI."""
        if self.selected_income_id is None:
            self.update_status_bar("No income selected for update.", "red")
            messagebox.showerror("Error", "No income selected for update.")
            return

        date = self.income_date_entry.get_date().strftime("%Y-%m-%d")
        source = self.income_source_entry.get().strip()
        amount_str = self.income_amount_entry.get().strip()
        description = self.income_description_entry.get().strip()

        if not date or not source or not amount_str:
            self.update_status_bar("Error: Date, Source, and Amount are required.", "red")
            messagebox.showwarning("Input Error", "Date, Source, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.update_status_bar("Error: Amount must be positive.", "red")
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid amount.", "red")
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if messagebox.askyesno("Confirm Update", f"Are you sure you want to update income ID: {self.selected_income_id}?"):
            if self.db.update_income(self.selected_income_id, date, source, amount, description):
                self.update_status_bar("Income updated successfully!", "green")
                self.clear_income_entries()
                self.view_income()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
            else:
                self.update_status_bar("Failed to update income.", "red")
                messagebox.showerror("Error", "Failed to update income.")
        else:
            self.cancel_income_edit()

    def cancel_income_edit(self):
        """Cancels the edit operation and reverts to add income mode."""
        self.clear_income_entries()
        self.update_status_bar("Income edit canceled. Ready to add new income.")

    def delete_income_gui(self):
        """Handles deleting the selected income from the GUI."""
        selected_item = self.income_tree.selection()
        if not selected_item:
            self.update_status_bar("Please select an income entry to delete.", "orange")
            messagebox.showwarning("Selection Error", "Please select an income entry to delete.")
            return

        item_values = self.income_tree.item(selected_item, 'values')
        income_id = item_values[0]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete income ID: {income_id}?\nThis action cannot be undone."):
            if self.db.delete_income(income_id):
                self.update_status_bar("Income deleted successfully!", "green")
                self.clear_income_entries()
                self.view_income()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
            else:
                self.update_status_bar("Failed to delete income.", "red")
                messagebox.showerror("Error", "Failed to delete income.")

    def apply_income_filters(self):
        """Applies filters to the income Treeview."""
        start_date_obj = self.income_filter_start_date.get_date()
        end_date_obj = self.income_filter_end_date.get_date()
        source = self.income_filter_source_entry.get().strip()
        keyword = self.income_filter_keyword_entry.get().strip()

        start_date = start_date_obj.strftime("%Y-%m-%d") if start_date_obj else None
        end_date = end_date_obj.strftime("%Y-%m-%d") if end_date_obj else None

        for item in self.income_tree.get_children():
            self.income_tree.delete(item)

        income_entries = self.db.fetch_income(start_date=start_date, end_date=end_date, source=source, keyword=keyword)

        if not income_entries:
            self.income_tree.insert("", tk.END, values=("", "", "No income found with these filters.", "", ""), tags=('center_text',))
            self.income_tree.tag_configure('center_text', anchor='center')
            self.update_status_bar("No income found with applied filters.", "orange")
            return

        for inc in income_entries:
            formatted_amount = f"₹{inc[3]:,.2f}"
            self.income_tree.insert("", tk.END, values=(inc[0], inc[1], inc[2], formatted_amount, inc[4]))
        self.update_status_bar(f"Displayed {len(income_entries)} income entries with applied filters.")

    def clear_income_filters(self):
        """Clears all income filters and reloads all income."""
        self.income_filter_start_date.set_date(None)
        self.income_filter_end_date.set_date(None)
        self.income_filter_source_entry.delete(0, tk.END)
        self.income_filter_keyword_entry.delete(0, tk.END)
        self.view_income()
        self.update_status_bar("Income filters cleared. Showing all income.")

    def view_income(self):
        """Populates the Treeview with all income from the database."""
        for item in self.income_tree.get_children():
            self.income_tree.delete(item)

        income_entries = self.db.fetch_income()
        if not income_entries:
            self.income_tree.insert("", tk.END, values=("", "", "No income recorded yet.", "", ""), tags=('center_text',))
            self.income_tree.tag_configure('center_text', anchor='center')
            return

        for inc in income_entries:
            formatted_amount = f"₹{inc[3]:,.2f}"
            self.income_tree.insert("", tk.END, values=(inc[0], inc[1], inc[2], formatted_amount, inc[4]))


    def update_summary_and_budget_display(self):
        """Updates the category summary, overall budget, and net balance information."""
        current_month_year = datetime.now().strftime("%Y-%m")
        expenses_this_month = self.db.fetch_expenses_by_month_year(current_month_year)
        income_this_month = self.db.fetch_income(month_year=current_month_year)
        
        # --- Overall Monthly Budget ---
        total_spent_this_month = sum(exp[3] for exp in expenses_this_month)
        monthly_budget = self.db.get_monthly_budget(current_month_year)
        remaining_overall_budget = monthly_budget - total_spent_this_month

        self.budget_amount_label.config(text=f"₹{monthly_budget:,.2f}")
        self.spent_amount_label.config(text=f"₹{total_spent_this_month:,.2f}")

        if remaining_overall_budget >= 0:
            self.remaining_budget_label.config(text=f"₹{remaining_overall_budget:,.2f}", foreground="green")
        else:
            self.remaining_budget_label.config(text=f"₹{remaining_overall_budget:,.2f} (Over Budget)", foreground="red")

        # --- Net Balance ---
        total_income_this_month = sum(inc[3] for inc in income_this_month)
        net_balance = total_income_this_month - total_spent_this_month
        self.net_balance_label.config(text=f"₹{net_balance:,.2f}", foreground="blue" if net_balance >= 0 else "red")


        # --- Category Spending Breakdown ---
        category_spending_this_month = collections.defaultdict(float)
        for exp in expenses_this_month:
            category_spending_this_month[exp[2].capitalize()] += exp[3]

        category_summary_content = ""
        if not category_spending_this_month:
            category_summary_content = "No categorized expenses for this month."
        else:
            header = f"{'Category'.ljust(15)} {'Spent'}\n"
            category_summary_content += header
            category_summary_content += "-" * len(header) + "\n"

            for category, spent in sorted(category_spending_this_month.items()):
                spent_str = f"₹{spent:,.2f}"
                category_summary_content += f"{category.ljust(15)[:15]} {spent_str}\n"

        self.category_summary_text.config(state=tk.NORMAL)
        self.category_summary_text.delete(1.0, tk.END)
        self.category_summary_text.insert(tk.END, category_summary_content)
        self.category_summary_text.config(state=tk.DISABLED)


    def set_budget_gui(self):
        """Handles setting the overall monthly budget from the GUI."""
        budget_amount_str = self.set_budget_entry.get().strip()
        if not budget_amount_str:
            self.update_status_bar("Error: Please enter a budget amount.", "red")
            messagebox.showwarning("Input Error", "Please enter a budget amount.")
            return

        try:
            budget_amount = float(budget_amount_str)
            if budget_amount < 0:
                self.update_status_bar("Error: Budget amount cannot be negative.", "red")
                messagebox.showwarning("Input Error", "Budget amount cannot be negative.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid budget amount.", "red")
            messagebox.showwarning("Input Error", "Invalid budget amount. Please enter a number.")
            return

        current_month_year = datetime.now().strftime("%Y-%m")
        if self.db.set_monthly_budget(current_month_year, budget_amount):
            self.update_status_bar(f"Overall monthly budget for {current_month_year} set to ₹{budget_amount:,.2f}!", "green")
            self.set_budget_entry.delete(0, tk.END)
            self.update_summary_and_budget_display()
        else:
            self.update_status_bar("Failed to set budget.", "red")
            messagebox.showerror("Error", "Failed to set budget.")

    # --- Category Management Methods ---
    def view_categories(self):
        """Populates the category Treeview in the Data tab."""
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        
        categories = self.db.get_categories()
        if not categories:
            self.category_tree.insert("", tk.END, values=("No categories defined.",), tags=('center_text',))
            self.category_tree.tag_configure('center_text', anchor='center')
            return

        for cat in categories:
            self.category_tree.insert("", tk.END, values=(cat,))
        self.update_status_bar(f"Displayed {len(categories)} categories.")

    def add_category_gui(self):
        """Adds a new category from the GUI."""
        category_name = self.category_name_entry.get().strip()
        if not category_name:
            self.update_status_bar("Error: Category name cannot be empty.", "red")
            messagebox.showwarning("Input Error", "Category name cannot be empty.")
            return
        
        if self.db.add_category(category_name):
            self.update_status_bar(f"Category '{category_name}' added successfully!", "green")
            self.category_name_entry.delete(0, tk.END)
            self.view_categories()
            # Update comboboxes that use categories
            self.expense_category_combobox.config(values=self.db.get_categories())
            self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories())
            self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories())
        else:
            self.update_status_bar(f"Failed to add category '{category_name}'.", "red")

    def edit_category_gui(self):
        """Initiates editing of a selected category."""
        selected_item = self.category_tree.selection()
        if not selected_item:
            self.update_status_bar("Please select a category to edit.", "orange")
            messagebox.showwarning("Selection Error", "Please select a category to edit.")
            return
        
        old_category_name = self.category_tree.item(selected_item, 'values')[0]
        new_category_name = self.category_name_entry.get().strip()

        if not new_category_name:
            self.update_status_bar("Error: New category name cannot be empty.", "red")
            messagebox.showwarning("Input Error", "New category name cannot be empty.")
            return

        if new_category_name == old_category_name:
            self.update_status_bar("No change in category name.", "orange")
            messagebox.showinfo("No Change", "The new category name is the same as the old one.")
            return

        if messagebox.askyesno("Confirm Edit", f"Are you sure you want to rename '{old_category_name}' to '{new_category_name}'?\nThis will also update all related expenses."):
            if self.db.update_category(old_category_name, new_category_name):
                self.update_status_bar(f"Category '{old_category_name}' renamed to '{new_category_name}' successfully!", "green")
                self.category_name_entry.delete(0, tk.END)
                self.view_categories()
                # Refresh all relevant lists/comboboxes
                self.view_expenses()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.expense_category_combobox.config(values=self.db.get_categories())
                self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories())
                self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories())
            else:
                self.update_status_bar(f"Failed to rename category '{old_category_name}'.", "red")

    def delete_category_gui(self):
        """Deletes a selected category."""
        selected_item = self.category_tree.selection()
        if not selected_item:
            self.update_status_bar("Please select a category to delete.", "orange")
            messagebox.showwarning("Selection Error", "Please select a category to delete.")
            return
        
        category_name = self.category_tree.item(selected_item, 'values')[0]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete category '{category_name}'?\nAll expenses under this category will be set to 'Uncategorized'."):
            if self.db.delete_category(category_name):
                self.update_status_bar(f"Category '{category_name}' deleted successfully!", "green")
                self.view_categories()
                # Refresh all relevant lists/comboboxes
                self.view_expenses()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.expense_category_combobox.config(values=self.db.get_categories())
                self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories())
                self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories())
            else:
                self.update_status_bar(f"Failed to delete category '{category_name}'.", "red")

    # --- Backup/Restore Methods ---
    def backup_database(self):
        """Backs up the current database file."""
        try:
            default_filename = f"expenses_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            file_path = filedialog.asksaveasfilename(
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                initialfile=default_filename
            )
            if file_path:
                self.db.close() # Close connection before copying
                shutil.copyfile(self.db.db_name, file_path)
                self.db._connect() # Re-establish connection
                self.update_status_bar(f"Database backed up to: {file_path}", "green")
            else:
                self.update_status_bar("Database backup canceled.", "orange")
        except Exception as e:
            self.update_status_bar(f"Error backing up database: {e}", "red")
            messagebox.showerror("Backup Error", f"Failed to backup database: {e}")

    def restore_database(self):
        """Restores the database from a selected backup file."""
        if not messagebox.askyesno("Confirm Restore", "WARNING: Restoring will OVERWRITE your current data. Are you sure you want to proceed?"):
            self.update_status_bar("Database restore canceled.", "orange")
            return

        try:
            file_path = filedialog.askopenfilename(
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")]
            )
            if file_path:
                self.db.close() # Close current connection
                shutil.copyfile(file_path, self.db.db_name) # Overwrite current db
                self.db._connect() # Re-establish connection
                self.update_status_bar(f"Database restored from: {file_path}", "green")
                # Refresh all data displays
                self.view_expenses()
                self.view_income()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.view_categories()
                self.expense_category_combobox.config(values=self.db.get_categories())
                self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories())
                self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories())
            else:
                self.update_status_bar("Database restore canceled.", "orange")
        except Exception as e:
            self.update_status_bar(f"Error restoring database: {e}", "red")
            messagebox.showerror("Restore Error", f"Failed to restore database: {e}")
            # Attempt to reconnect to potentially corrupted/missing original DB
            self.db._connect()


    # --- Charting Methods ---
    def _prepare_chart_area(self):
        """Clears the existing Matplotlib figure and prepares it for new plotting."""
        # Clear any existing "No data" label
        if self.no_data_label:
            self.no_data_label.destroy()
            self.no_data_label = None
        
        # Clear all axes from the figure
        if self.figure:
            self.figure.clear()
            # Ensure the canvas widget is visible if it was hidden (e.g., by a no_data_label)
            if not self.canvas_widget.get_tk_widget().winfo_ismapped():
                self.canvas_widget.get_tk_widget().pack(expand=True, fill="both")
            self.canvas_widget.draw_idle() # Redraw to show blank canvas

    def display_no_chart_data_message(self, message):
        """Displays a message when no data is available for charts by drawing on the figure."""
        self._prepare_chart_area() # Clear any existing plot
        
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, message, horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=12, color=self.text_color, style='italic')
        ax.set_xticks([]) # Hide ticks
        ax.set_yticks([])
        ax.set_frame_on(False) # Hide frame
        self.canvas_widget.draw()

    def get_filtered_data_for_charts(self, data_type="expenses"):
        """Fetches expenses or income based on the selected year/month filters."""
        selected_year = self.analytics_year_combobox.get()
        selected_month = self.analytics_month_combobox.get()
        selected_category = self.analytics_category_combobox.get() # For category trend chart

        fetch_func = self.db.fetch_expenses if data_type == "expenses" else self.db.fetch_income

        if selected_year == "All Years":
            if selected_month == "All":
                data = fetch_func() # All data
            else:
                # This case is less common for general charts, but for completeness:
                # Sum for specific month across all years
                data = fetch_func(month_year=f"%-{selected_month}") # Fetch all entries where month matches
        else: # Specific Year selected
            if selected_month == "All":
                data = fetch_func(year=selected_year)
            else:
                month_year_filter = f"{selected_year}-{selected_month}"
                data = fetch_func(month_year=month_year_filter)

        # For category trend chart, we also need to filter by category
        if data_type == "expenses" and selected_category != "All Categories":
            data = [d for d in data if d[2] == selected_category] # d[2] is category for expenses
            
        return data

    def generate_pie_chart_filtered(self):
        """Generates and displays a pie chart of expenses by category, filtered by month/year."""
        self._prepare_chart_area() # Use the new method

        selected_year = self.analytics_year_combobox.get()
        selected_month = self.analytics_month_combobox.get()

        if selected_year == "All Years":
            self.display_no_chart_data_message("Please select a specific year for a meaningful Pie Chart.")
            return
        
        expenses = self.get_filtered_data_for_charts(data_type="expenses")

        if not expenses:
            self.display_no_chart_data_message("No expenses recorded for the selected period to generate charts.")
            return

        category_totals = collections.defaultdict(float)
        for exp in expenses:
            category_totals[exp[2].capitalize()] += exp[3]

        if not category_totals:
            self.display_no_chart_data_message("No categorized expenses for the selected period to generate a pie chart.")
            return

        labels = list(category_totals.keys())
        sizes = list(category_totals.values())

        # Use the existing figure, add a subplot
        ax = self.figure.add_subplot(111) # Add a new subplot to the cleared figure
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, wedgeprops={'edgecolor': 'black'})
        ax.axis('equal')
        
        chart_title_suffix = f" for {selected_month}/{selected_year}" if selected_month != "All" else f" for {selected_year}"
        ax.set_title(f"Expense Distribution by Category{chart_title_suffix}", fontsize=12)

        self.canvas_widget.draw() # Draw on the existing canvas

    def generate_bar_chart_filtered(self):
        """Generates and displays a bar chart of monthly spending, filtered by selected year."""
        self._prepare_chart_area() # Use the new method
        
        selected_year = self.analytics_year_combobox.get()
        selected_month = self.analytics_month_combobox.get()

        if selected_year == "All Years":
            self.display_no_chart_data_message("Monthly bar chart displays trends within a specific year. Please select a specific year.")
            return

        if selected_month != "All":
            self.display_no_chart_data_message("Monthly bar chart visualizes spending trends across months. For this chart, please ensure 'Select Month' is set to 'All'.")
            return

        expenses = self.get_filtered_data_for_charts(data_type="expenses")

        if not expenses:
            self.display_no_chart_data_message("No expenses recorded for the selected year to generate charts.")
            return

        monthly_totals = collections.defaultdict(float)
        all_months = [f"{i:02d}" for i in range(1, 13)]
        
        for exp in expenses:
            exp_date = datetime.strptime(exp[1], "%Y-%m-%d")
            if str(exp_date.year) == selected_year:
                month_year_str = exp_date.strftime("%Y-%m")
                monthly_totals[month_year_str] += exp[3]
        
        labels_full_year = [f"{selected_year}-{m}" for m in all_months]
        amounts = [monthly_totals.get(month_label, 0.0) for month_label in labels_full_year]
        
        display_labels = [datetime.strptime(m, "%Y-%m").strftime("%b") for m in labels_full_year]

        if not any(amounts):
             self.display_no_chart_data_message(f"No monthly expenses for {selected_year} to generate a bar chart.")
             return

        ax = self.figure.add_subplot(111) # Use the existing figure, add a subplot
        ax.bar(display_labels, amounts, color=self.accent_blue)
        ax.set_xlabel("Month")
        ax.set_ylabel("Total Amount (₹)")
        ax.set_title(f"Monthly Spending Overview for {selected_year}", fontsize=12)
        ax.tick_params(axis='x', rotation=45, labelsize=9)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        self.canvas_widget.draw() # Draw on the existing canvas

    def generate_monthly_spending_trend_chart(self):
        """Generates and displays a line chart of overall spending trend across months/years."""
        self._prepare_chart_area() # Use the new method

        selected_year = self.analytics_year_combobox.get()
        selected_month = self.analytics_month_combobox.get()

        if selected_month != "All":
            self.display_no_chart_data_message("The Overall Trend Chart shows spending across months/years. Please set 'Select Month' to 'All'.")
            return

        expenses_data = self.get_filtered_data_for_charts(data_type="expenses")

        if not expenses_data:
            self.display_no_chart_data_message("No expenses recorded for the selected period to generate a trend chart.")
            return

        monthly_spending = collections.defaultdict(float)
        for exp in expenses_data:
            exp_date = datetime.strptime(exp[1], "%Y-%m-%d")
            month_year_key = exp_date.strftime("%Y-%m")
            monthly_spending[month_year_key] += exp[3]

        if not monthly_spending:
            self.display_no_chart_data_message("No monthly spending data available for the trend chart.")
            return

        sorted_months = sorted(monthly_spending.keys())
        amounts = [monthly_spending[month] for month in sorted_months]
        
        display_labels = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in sorted_months]

        ax = self.figure.add_subplot(111) # Use the existing figure, add a subplot
        ax.plot(display_labels, amounts, marker='o', linestyle='-', color=self.accent_blue)
        ax.set_xlabel("Month and Year")
        ax.set_ylabel("Total Amount (₹)")
        
        chart_title = "Overall Monthly Spending Trend"
        if selected_year != "All Years":
            chart_title += f" for {selected_year}"
        
        ax.set_title(chart_title, fontsize=14)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()

        self.canvas_widget.draw() # Draw on the existing canvas

    def generate_category_spending_trend_chart(self):
        """Generates a line chart showing spending trend for a specific category over time."""
        self._prepare_chart_area() # Use the new method

        selected_category = self.analytics_category_combobox.get()
        selected_year = self.analytics_year_combobox.get()
        selected_month = self.analytics_month_combobox.get()

        if selected_category == "All Categories":
            self.display_no_chart_data_message("Please select a specific category to generate a category trend chart.")
            return
        if selected_month != "All":
            self.display_no_chart_data_message("Category Trend Chart shows spending across months/years. Please set 'Select Month' to 'All'.")
            return

        # Fetch expenses for the selected category, filtered by year if specified
        expenses_data = self.db.fetch_expenses(category=selected_category, year=selected_year if selected_year != "All Years" else None)

        if not expenses_data:
            self.display_no_chart_data_message(f"No expenses recorded for '{selected_category}' in the selected period to generate a trend chart.")
            return

        monthly_category_spending = collections.defaultdict(float)
        for exp in expenses_data:
            exp_date = datetime.strptime(exp[1], "%Y-%m-%d")
            month_year_key = exp_date.strftime("%Y-%m")
            monthly_category_spending[month_year_key] += exp[3]

        if not monthly_category_spending:
            self.display_no_chart_data_message(f"No monthly spending data for '{selected_category}' to generate a trend chart.")
            return

        sorted_months = sorted(monthly_category_spending.keys())
        amounts = [monthly_category_spending[month] for month in sorted_months]

        display_labels = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in sorted_months]

        ax = self.figure.add_subplot(111) # Use the existing figure, add a subplot
        ax.plot(display_labels, amounts, marker='o', linestyle='-', color=self.accent_red)
        ax.set_xlabel("Month and Year")
        ax.set_ylabel(f"Amount Spent in {selected_category} (₹)")
        
        chart_title = f"Spending Trend for '{selected_category}'"
        if selected_year != "All Years":
            chart_title += f" in {selected_year}"
        
        ax.set_title(chart_title, fontsize=14)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()

        self.canvas_widget.draw() # Draw on the existing canvas


    def update_analytics_filters_and_chart(self):
        """Updates the available years/categories in the analytics filter comboboxes based on actual data,
           and refreshes the default chart."""
        current_year = datetime.now().year
        
        # Update Years Combobox
        all_expense_years = self.db.get_all_expense_years()
        all_income_years = self.db.get_all_income_years()
        all_years_in_db = sorted(list(set(all_expense_years + all_income_years + [str(current_year)])), reverse=True)
        updated_analytics_years = ["All Years"] + all_years_in_db

        self.analytics_year_combobox['values'] = updated_analytics_years
        if str(current_year) in updated_analytics_years:
            self.analytics_year_combobox.set(str(current_year))
        elif updated_analytics_years:
            self.analytics_year_combobox.set(updated_analytics_years[0])
        else:
            self.analytics_year_combobox.set("All Years")

        self.analytics_month_combobox.set("All") # Reset month to All

        # Update Categories Combobox
        all_categories = self.db.get_categories()
        updated_categories_for_analytics = ["All Categories"] + all_categories
        self.analytics_category_combobox['values'] = updated_categories_for_analytics
        self.analytics_category_combobox.set("All Categories") # Default to All Categories

        # Regenerate the default chart (e.g., pie chart for selected year/all)
        self.generate_pie_chart_filtered()


    def display_no_chart_data_message(self, message):
        """Displays a message when no data is available for charts by drawing on the figure."""
        self._prepare_chart_area() # Ensure any previous chart or message is cleared
        
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, message, horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=12, color=self.text_color, style='italic')
        ax.set_xticks([]) # Hide ticks
        ax.set_yticks([])
        ax.set_frame_on(False) # Hide frame
        self.canvas_widget.draw()


def run_app():
    """Initializes and runs the Tkinter application."""
    root = tk.Tk()
    app = ExpenseTrackerApp(root)
    root.mainloop()
    # Ensure database connection is closed when the app window is closed
    if app.db.conn:
        app.db.close()

if __name__ == "__main__":
    run_app()
