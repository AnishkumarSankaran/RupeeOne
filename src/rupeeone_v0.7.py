import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import sqlite3
from datetime import datetime, timedelta
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
import shutil # For file operations in backup/restore
import os # For deleting files
import numpy as np # Added for trigonometric calculations for donut chart labels

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
        """
        Creates the 'expenses', 'budgets', 'income', and 'categories' tables if they don't already exist.
        Initializes with default categories and a default budget (set to 0.00).
        """
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
                        ("Education",), ("Salary",), ("Freelance",), ("Investments",),
                        ("Travel",), ("Fuel",), ("Books",), ("Gym",), ("Gifts",)
                    ]
                    self.cursor.executemany("INSERT INTO categories (name) VALUES (?)", default_categories)
                    self.conn.commit()
                    print("Default categories added.")

                # Add a default budget for the current month if the table is empty
                # Changed default amount to 0.00 as per request
                self.cursor.execute("SELECT COUNT(*) FROM budgets")
                if self.cursor.fetchone()[0] == 0:
                    current_month_year = datetime.now().strftime("%Y-%m")
                    self.cursor.execute("INSERT INTO budgets (month_year, budget_amount) VALUES (?, ?)", (current_month_year, 0.00)) # Default to 0.00
                    self.conn.commit()
                    print("Default budget for current month added (0.00).")

            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to create tables or add default data: {e}")
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
        if month_year: # For specificYYYY-MM
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
        master.title("RupeeOne - Personal Finance Tracker") # Updated title
        master.geometry("1200x800") # Increased size for more features
        master.minsize(900, 700) # Minimum size to prevent layout issues
        master.option_add("*tearOff", False) # Disable tear-off for menus

        # --- Database Initialization ---
        # Initialize DB first, as it's critical for data operations
        self.db = DatabaseManager()
        if not self.db.conn:
            messagebox.showerror("Initialization Error", "Could not connect to database. Exiting application.")
            master.destroy()
            return

        # --- Styling for a modern and clean look ---
        self.style = ttk.Style()
        try:
            # Try 'clam' as a good cross-platform theme for dark mode
            self.style.theme_use("clam")
        except tk.TclError:
            print("Warning: 'clam' theme not found. Falling back to 'default'.")
            self.style.theme_use("default")
        
        # Define Color Palette
        self.master_bg = "#2C3E50" # Dark Blue-Gray
        self.frame_bg = "#34495E" # Slightly Lighter Dark Blue-Gray
        self.input_bg = "#ECF0F1" # Light Gray/Off-white
        self.text_color = "#E0E0E0" # Soft white for main text
        self.accent_primary = "#1ABC9C" # Highlight/accent (Emerald Green)
        self.accent_danger = "#E74C3C" # Danger (Alizarin Red)
        self.accent_info = "#3498DB" # Peter River Blue - for Edit/Info
        self.accent_orange = "#F39C12" # Orange - for Budget
        self.accent_purple = "#9B59B6" # Amethyst - for Income

        # Chart Colors (more distinct and visually appealing on dark background)
        self.chart_colors = [
            "#8E7CC3",  # Medium Purple
            "#6EC4A8",  # Teal Green
            "#F7B846",  # Goldenrod
            "#E07A5F",  # Coral/Salmon
            "#52B2BF",  # Sky Blue
            "#A8DADC",  # Light Cyan
            "#FFC1CC",  # Soft Pink
            "#7D8C9D",  # Desaturated Blue-Gray
            "#C3A0D7",  # Lavender-ish
            "#B5EAD7"   # Pale Green
        ]

        # Font Configuration - Using Segoe UI or Helvetica as fallback
        self.font_family = "Segoe UI"
        # Corrected font family existence check
        available_fonts = self.master.tk.call("font", "families")
        if self.font_family not in available_fonts:
            self.font_family = "Helvetica" # Fallback

        # Configure general styles
        self.style.configure(".", background=self.master_bg, foreground=self.text_color, font=(self.font_family, 10))
        self.style.configure("TFrame", background=self.master_bg)
        
        # TLabelframe (for cards/sections)
        self.style.configure("TLabelframe", 
                             background=self.frame_bg,
                             foreground=self.text_color,
                             font=(self.font_family, 11, "bold"), # Titles: large, bold
                             relief="flat", 
                             borderwidth=0, 
                             padding=15) 
        self.style.configure("TLabelframe.Label", 
                             background=self.frame_bg, 
                             foreground=self.text_color, 
                             font=(self.font_family, 11, "bold"))

        # Labels
        self.style.configure("TLabel", background=self.frame_bg, foreground=self.text_color, padding=2, font=(self.font_family, 10)) # Labels: regular font
        self.style.configure("Value.TLabel", font=(self.font_family, 12, "bold"), foreground=self.text_color) # Value displays
        self.style.configure("DashboardValue.TLabel", font=(self.font_family, 20, "bold")) # Larger for dashboard cards
        self.style.configure("DashboardStatus.TLabel", font=(self.font_family, 16, "bold")) # For budget status

        # Input fields
        self.style.configure("TEntry", fieldbackground=self.input_bg, foreground="#333333", padding=5, relief="flat", borderwidth=2, font=(self.font_family, 10))
        self.style.map("TEntry", fieldbackground=[('focus', '#DDEEFF')]) # Light blue on focus
        self.style.configure("TCombobox", fieldbackground=self.input_bg, foreground="#333333", padding=5, relief="flat", borderwidth=2, font=(self.font_family, 10))
        self.style.map("TCombobox", fieldbackground=[('focus', '#DDEEFF')])
        self.style.configure("DateEntry", fieldbackground=self.input_bg, foreground="#333333", padding=5, borderwidth=2, relief="flat", font=(self.font_family, 10))
        
        # Button styles
        self.style.configure("TButton", font=(self.font_family, 10, "bold"), padding=(15, 8), relief="flat", borderwidth=0,
                             background=self.accent_info, foreground="white")
        self.style.map("TButton", background=[('active', self.accent_info)]) # Hover effect

        self.style.configure("Accent.TButton", background=self.accent_primary, foreground="white")
        self.style.map("Accent.TButton", background=[('active', '#16A085')]) # Darker shade on hover

        self.style.configure("Edit.TButton", background=self.accent_info, foreground="white")
        self.style.map("Edit.TButton", background=[('active', '#2980B9')])

        self.style.configure("Delete.TButton", background=self.accent_danger, foreground="white")
        self.style.map("Delete.TButton", background=[('active', '#C0392B')])

        self.style.configure("Budget.TButton", background=self.accent_orange, foreground="white") # Changed foreground to white
        self.style.map("Budget.TButton", background=[('active', '#E67E22')])

        self.style.configure("Income.TButton", background=self.accent_purple, foreground="white")
        self.style.map("Income.TButton", background=[('active', '#8E44AD')])

        # Treeview styles
        self.style.configure("Treeview.Heading", font=(self.font_family, 10, "bold"), background="#4A6070", foreground="white", padding=8)
        self.style.configure("Treeview", font=(self.font_family, 9), background=self.frame_bg, foreground=self.text_color, fieldbackground=self.frame_bg,
                             rowheight=28) # Increased row height for better readability
        self.style.map("Treeview", background=[('selected', self.accent_info)], foreground=[('selected', 'white')])
        
        # Notebook (Tab) styles
        self.style.configure("TNotebook", background=self.master_bg, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=self.frame_bg, foreground=self.text_color, padding=[15, 8], font=(self.font_family, 10, "bold"))
        self.style.map("TNotebook.Tab", background=[('selected', self.accent_info)], foreground=[('selected', 'white')])

        # Chart display frame and no data message
        self.style.configure("ChartDisplay.TFrame", background=self.frame_bg, relief="flat", borderwidth=0, padding=10)
        self.style.configure("NoData.TLabel", background=self.frame_bg, foreground="#BDC3C7", font=(self.font_family, 12, "italic")) # Light gray for no data


        self.selected_expense_id = None # To keep track of expense being edited
        self.selected_income_id = None  # To keep track of income being edited

        self.create_widgets()
        self.view_expenses() # Load expenses on startup
        self.update_summary_and_budget_display()
        self.update_status_bar("Welcome to your Personal Finance Tracker! ✨")

    # --- Status Bar ---
    def update_status_bar(self, message, color="white"):
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

        # --- Tab 0: Dashboard ---
        self.dashboard_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.dashboard_tab, text="Dashboard 📊")
        self._create_dashboard_tab_widgets(self.dashboard_tab)

        # --- Tab 1: Expenses ---
        self.expenses_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.expenses_tab, text="Expenses 💸")
        self._create_expenses_tab_widgets(self.expenses_tab)

        # --- Tab 2: Income ---
        self.income_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.income_tab, text="Income 💰")
        self._create_income_tab_widgets(self.income_tab)

        # --- Tab 3: Analytics ---
        self.analytics_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.analytics_tab, text="Analytics 📈") # Renamed from Reports
        self._create_analytics_tab_widgets(self.analytics_tab)

        # --- Tab 4: Data Management ---
        self.data_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.data_tab, text="Data 🗄️")
        self._create_data_tab_widgets(self.data_tab)

        # Status Bar at the bottom
        self.status_label = ttk.Label(self.master, text="", anchor="w", background=self.master_bg, font=(self.font_family, 9, "italic"))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def _create_dashboard_tab_widgets(self, parent_frame):
        """Widgets for the new Dashboard tab."""
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)
        parent_frame.grid_rowconfigure(2, weight=3) # Chart area gets more space
        parent_frame.grid_columnconfigure(0, weight=1)

        main_dashboard_frame = ttk.Frame(parent_frame, style="TFrame", padding="20")
        main_dashboard_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_dashboard_frame.grid_columnconfigure(0, weight=1)
        main_dashboard_frame.grid_columnconfigure(1, weight=1)
        main_dashboard_frame.grid_columnconfigure(2, weight=1)
        main_dashboard_frame.grid_rowconfigure(0, weight=1)
        main_dashboard_frame.grid_rowconfigure(1, weight=1)
        main_dashboard_frame.grid_rowconfigure(2, weight=3)


        # Summary Cards - using TLabelframe style
        card_style = "TLabelframe" 

        # Total Income Card
        income_card = ttk.LabelFrame(main_dashboard_frame, text="Total Income (This Month)", style=card_style)
        income_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        income_card.grid_columnconfigure(0, weight=1)
        self.dashboard_income_label = ttk.Label(income_card, text="₹0.00", style="DashboardValue.TLabel", background=self.frame_bg, foreground=self.accent_primary)
        self.dashboard_income_label.grid(row=0, column=0, pady=10)

        # Total Expenses Card
        expenses_card = ttk.LabelFrame(main_dashboard_frame, text="Total Expenses (This Month)", style=card_style)
        expenses_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        expenses_card.grid_columnconfigure(0, weight=1)
        self.dashboard_expenses_label = ttk.Label(expenses_card, text="₹0.00", style="DashboardValue.TLabel", background=self.frame_bg, foreground=self.accent_danger)
        self.dashboard_expenses_label.grid(row=0, column=0, pady=10)

        # Net Balance Card
        net_balance_card = ttk.LabelFrame(main_dashboard_frame, text="Net Balance (This Month)", style=card_style)
        net_balance_card.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        net_balance_card.grid_columnconfigure(0, weight=1)
        self.dashboard_net_balance_label = ttk.Label(net_balance_card, text="₹0.00", style="DashboardValue.TLabel", background=self.frame_bg, foreground=self.accent_info)
        self.dashboard_net_balance_label.grid(row=0, column=0, pady=10)

        # Budget Status Card
        budget_card = ttk.LabelFrame(main_dashboard_frame, text="Budget Status (This Month)", style=card_style)
        budget_card.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        budget_card.grid_columnconfigure(0, weight=1)
        self.dashboard_budget_label = ttk.Label(budget_card, text="Budget: ₹0.00 | Spent: ₹0.00 | Remaining: ₹0.00", font=(self.font_family, 14), background=self.frame_bg, foreground=self.text_color)
        self.dashboard_budget_label.grid(row=0, column=0, pady=5)
        self.dashboard_budget_status_label = ttk.Label(budget_card, text="On Track! ✅", style="DashboardStatus.TLabel", background=self.frame_bg)
        self.dashboard_budget_status_label.grid(row=1, column=0, pady=5)

        # Placeholder for a quick chart (e.g., small bar chart of top categories)
        self.dashboard_chart_frame = ttk.Frame(main_dashboard_frame, style="ChartDisplay.TFrame") # Apply ChartDisplay.TFrame style
        self.dashboard_chart_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.dashboard_chart_frame.grid_rowconfigure(0, weight=1)
        self.dashboard_chart_frame.grid_columnconfigure(0, weight=1)

        # Initialize Matplotlib Figure and Canvas for Dashboard
        self.dashboard_figure = plt.Figure(figsize=(10, 5), dpi=100, facecolor=self.frame_bg) 
        self.dashboard_canvas_widget = FigureCanvasTkAgg(self.dashboard_figure, master=self.dashboard_chart_frame)
        self.dashboard_canvas_widget.get_tk_widget().pack(expand=True, fill="both")
        self.dashboard_no_data_label = None # To manage "No data" label for dashboard chart

        self.update_dashboard_summary() # Initial load

    def _create_expenses_tab_widgets(self, parent_frame):
        """Widgets for the Expenses tab (Add, View, Edit, Delete, Summary, Budget)."""
        parent_frame.grid_rowconfigure(1, weight=3) # Expense list gets more space
        parent_frame.grid_rowconfigure(2, weight=1) # Summary/Budget gets less space
        parent_frame.grid_columnconfigure(0, weight=1)

        # --- Input Frame (Compact Layout) ---
        input_frame = ttk.LabelFrame(parent_frame, text="Add/Edit Expense", padding="15 10", style="TLabelframe") 
        input_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1) # Make entry fields stretch
        input_frame.grid_columnconfigure(3, weight=1) # Make entry fields stretch

        # Row 0: Date and Category
        ttk.Label(input_frame, text="Date (YYYY-MM-DD):", background=self.frame_bg).grid(row=0, column=0, sticky="w", pady=4, padx=5)
        self.expense_date_entry = DateEntry(input_frame, width=15, background='darkblue',
                                    foreground='white', borderwidth=2,
                                    year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                                    date_pattern='yyyy-mm-dd', selectmode='day', font=(self.font_family, 10))
        self.expense_date_entry.grid(row=0, column=1, pady=4, padx=5, sticky="ew")

        ttk.Label(input_frame, text="Category:", background=self.frame_bg).grid(row=0, column=2, sticky="w", pady=4, padx=5)
        self.expense_category_combobox = ttk.Combobox(input_frame, values=self.db.get_categories(), state="normal", font=(self.font_family, 10))
        self.expense_category_combobox.grid(row=0, column=3, pady=4, padx=5, sticky="ew")
        self.expense_category_combobox.bind("<FocusIn>", lambda e: self.expense_category_combobox.config(values=self.db.get_categories()))
        
        # Row 1: Amount and Description
        ttk.Label(input_frame, text="Amount (₹):", background=self.frame_bg).grid(row=1, column=0, sticky="w", pady=4, padx=5)
        self.expense_amount_entry = ttk.Entry(input_frame, validate="key", validatecommand=(self.master.register(self._validate_numeric_input), '%P'))
        self.expense_amount_entry.grid(row=1, column=1, pady=4, padx=5, sticky="ew")

        ttk.Label(input_frame, text="Description:", background=self.frame_bg).grid(row=1, column=2, sticky="w", pady=4, padx=5)
        self.expense_description_entry = ttk.Entry(input_frame)
        self.expense_description_entry.grid(row=1, column=3, pady=4, padx=5, sticky="ew")

        # Buttons Frame (Centered)
        button_frame = ttk.Frame(input_frame, style="TFrame")
        button_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1) # For centering

        self.add_update_expense_button = ttk.Button(button_frame, text="➕ Add Expense", command=self.add_expense_gui, style="Accent.TButton")
        self.add_update_expense_button.grid(row=0, column=1, padx=5, sticky="ew") # Centered
        self.cancel_expense_edit_button = ttk.Button(button_frame, text="✖️ Cancel Edit", command=self.cancel_expense_edit, style="TButton")
        self.cancel_expense_edit_button.grid(row=0, column=2, padx=5, sticky="ew")
        self.cancel_expense_edit_button.grid_remove() # Hidden initially

        # --- Expense List Frame with Filters ---
        list_filter_frame = ttk.LabelFrame(parent_frame, text="All Expenses", padding="15 10", style="TLabelframe") 
        list_filter_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        list_filter_frame.grid_rowconfigure(3, weight=1) # Treeview gets more space
        list_filter_frame.grid_columnconfigure(1, weight=1)
        list_filter_frame.grid_columnconfigure(3, weight=1)

        filter_row = 0
        ttk.Label(list_filter_frame, text="Start Date:", background=self.frame_bg).grid(row=filter_row, column=0, sticky="w", padx=5, pady=2)
        self.expense_filter_start_date = DateEntry(list_filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', selectmode='day', font=(self.font_family, 9))
        self.expense_filter_start_date.grid(row=filter_row, column=1, sticky="ew", padx=5, pady=2)
        self.expense_filter_start_date.set_date(None)

        ttk.Label(list_filter_frame, text="End Date:", background=self.frame_bg).grid(row=filter_row, column=2, sticky="w", padx=5, pady=2)
        self.expense_filter_end_date = DateEntry(list_filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', selectmode='day', font=(self.font_family, 9))
        self.expense_filter_end_date.grid(row=filter_row, column=3, sticky="ew", padx=5, pady=2)
        self.expense_filter_end_date.set_date(None)

        filter_row += 1
        ttk.Label(list_filter_frame, text="Category:", background=self.frame_bg).grid(row=filter_row, column=0, sticky="w", padx=5, pady=2)
        self.expense_filter_category_combobox = ttk.Combobox(list_filter_frame, values=["All Categories"] + self.db.get_categories(), state="readonly", font=(self.font_family, 9))
        self.expense_filter_category_combobox.set("All Categories")
        self.expense_filter_category_combobox.grid(row=filter_row, column=1, sticky="ew", padx=5, pady=2)
        self.expense_filter_category_combobox.bind("<FocusIn>", lambda e: self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories()))

        ttk.Label(list_filter_frame, text="Search:", background=self.frame_bg).grid(row=filter_row, column=2, sticky="w", padx=5, pady=2)
        self.expense_filter_keyword_entry = ttk.Entry(list_filter_frame, font=(self.font_family, 9))
        self.expense_filter_keyword_entry.grid(row=filter_row, column=3, sticky="ew", padx=5, pady=2)
        self.expense_filter_keyword_entry.bind("<Return>", lambda e: self.apply_expense_filters())

        filter_row += 1
        apply_filter_button = ttk.Button(list_filter_frame, text="🔍 Apply Filters", command=self.apply_expense_filters, style="TButton")
        apply_filter_button.grid(row=filter_row, column=0, columnspan=2, pady=5, padx=5, sticky="ew")
        clear_filter_button = ttk.Button(list_filter_frame, text="🧹 Clear Filters", command=self.clear_expense_filters, style="TButton")
        clear_filter_button.grid(row=filter_row, column=2, columnspan=2, pady=5, padx=5, sticky="ew")

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
        self.expense_tree.column("Description", minwidth=150, width=250, anchor=tk.W, stretch=tk.YES)

        self.expense_tree.grid(row=filter_row + 1, column=0, columnspan=4, sticky="nsew", pady=(10,0))
        list_filter_frame.grid_rowconfigure(filter_row + 1, weight=1)

        scrollbar = ttk.Scrollbar(list_filter_frame, orient=tk.VERTICAL, command=self.expense_tree.yview)
        self.expense_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=filter_row + 1, column=4, sticky="ns", pady=(10,0))

        action_button_frame = ttk.Frame(list_filter_frame, style="TFrame")
        action_button_frame.grid(row=filter_row + 2, column=0, columnspan=5, pady=10, sticky="ew")
        action_button_frame.grid_columnconfigure(0, weight=1)
        action_button_frame.grid_columnconfigure(1, weight=1)

        edit_button = ttk.Button(action_button_frame, text="✏️ Edit Selected", command=self.edit_expense_gui, style="Edit.TButton")
        edit_button.grid(row=0, column=0, padx=5, sticky="ew")

        delete_button = ttk.Button(action_button_frame, text="🗑️ Delete Selected", command=self.delete_expense_gui, style="Delete.TButton")
        delete_button.grid(row=0, column=1, padx=5, sticky="ew")

        # --- Summary and Overall Budget Frame ---
        summary_overall_budget_frame = ttk.LabelFrame(parent_frame, text="Monthly Summary & Budget", padding="15 10", style="TLabelframe") 
        summary_overall_budget_frame.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="nsew")
        summary_overall_budget_frame.grid_columnconfigure(0, weight=1)
        summary_overall_budget_frame.grid_columnconfigure(1, weight=1)
        summary_overall_budget_frame.grid_rowconfigure(1, weight=1) # Allow category summary text to expand

        # Left Column: Summary
        ttk.Label(summary_overall_budget_frame, text="Overall Budget for Selected Month:", background=self.frame_bg).grid(row=0, column=0, sticky="w", pady=2, padx=5)
        self.budget_amount_label = ttk.Label(summary_overall_budget_frame, text="₹0.00", style="Value.TLabel", background=self.frame_bg)
        self.budget_amount_label.grid(row=1, column=0, sticky="w", pady=2, padx=5)

        ttk.Label(summary_overall_budget_frame, text="Total Spent This Month:", background=self.frame_bg).grid(row=2, column=0, sticky="w", pady=2, padx=5)
        self.spent_amount_label = ttk.Label(summary_overall_budget_frame, text="₹0.00", style="Value.TLabel", background=self.frame_bg)
        self.spent_amount_label.grid(row=3, column=0, sticky="w", pady=2, padx=5)

        ttk.Label(summary_overall_budget_frame, text="Net Balance (Income - Expenses):", background=self.frame_bg).grid(row=4, column=0, sticky="w", pady=2, padx=5)
        self.net_balance_label = ttk.Label(summary_overall_budget_frame, text="₹0.00", style="Value.TLabel", background=self.frame_bg)
        self.net_balance_label.grid(row=5, column=0, sticky="w", pady=2, padx=5)

        ttk.Label(summary_overall_budget_frame, text="Remaining Overall Budget:", background=self.frame_bg).grid(row=6, column=0, sticky="w", pady=2, padx=5)
        self.remaining_budget_label = ttk.Label(summary_overall_budget_frame, text="₹0.00", font=(self.font_family, 12, "bold", "italic"), background=self.frame_bg)
        self.remaining_budget_label.grid(row=7, column=0, sticky="w", pady=2, padx=5)
        
        # Budget Setting Controls (Manual MM-YYYY)
        ttk.Label(summary_overall_budget_frame, text="Set Budget For (MM-YYYY):", background=self.frame_bg).grid(row=8, column=0, sticky="w", pady=(10,0), padx=5)
        
        budget_month_year_frame = ttk.Frame(summary_overall_budget_frame, style="TFrame")
        budget_month_year_frame.grid(row=9, column=0, sticky="ew", padx=5)
        budget_month_year_frame.grid_columnconfigure(0, weight=1)
        budget_month_year_frame.grid_columnconfigure(1, weight=1)

        self.set_budget_month_combobox = ttk.Combobox(budget_month_year_frame, values=[f"{i:02d}" for i in range(1, 13)], state="readonly", font=(self.font_family, 10), width=5)
        self.set_budget_month_combobox.set(datetime.now().strftime("%m"))
        self.set_budget_month_combobox.grid(row=0, column=0, sticky="ew", padx=(0,5))

        current_year = datetime.now().year
        years = [str(y) for y in range(current_year - 5, current_year + 6)] # +/- 5 years
        self.set_budget_year_combobox = ttk.Combobox(budget_month_year_frame, values=years, state="readonly", font=(self.font_family, 10), width=7)
        self.set_budget_year_combobox.set(str(current_year))
        self.set_budget_year_combobox.grid(row=0, column=1, sticky="ew")

        ttk.Label(summary_overall_budget_frame, text="New Budget Amount (₹):", background=self.frame_bg).grid(row=10, column=0, sticky="w", pady=5, padx=5)
        set_budget_entry_frame = ttk.Frame(summary_overall_budget_frame, style="TFrame")
        set_budget_entry_frame.grid(row=11, column=0, sticky="ew", padx=5)
        set_budget_entry_frame.grid_columnconfigure(0, weight=1)

        self.set_budget_entry = ttk.Entry(set_budget_entry_frame, validate="key", validatecommand=(self.master.register(self._validate_numeric_input), '%P'))
        self.set_budget_entry.grid(row=0, column=0, sticky="ew", padx=(0,5))
        set_budget_button = ttk.Button(set_budget_entry_frame, text="Set Budget", command=self.set_budget_gui, style="Budget.TButton")
        set_budget_button.grid(row=0, column=1, sticky="ew")


        # Right Column: Category Spending Summary
        ttk.Label(summary_overall_budget_frame, text="Category Spending This Month:", background=self.frame_bg, font=(self.font_family, 11, "bold")).grid(row=0, column=1, sticky="nw", pady=2, padx=5)
        self.category_summary_text = tk.Text(summary_overall_budget_frame, height=10, width=40, state=tk.DISABLED, wrap=tk.WORD,
                                             background=self.input_bg, foreground="#333333", font=(self.font_family, 9), relief="flat", borderwidth=1)
        self.category_summary_text.grid(row=1, column=1, rowspan=11, sticky="nsew", pady=2, padx=5)
        summary_overall_budget_frame.grid_rowconfigure(1, weight=1)


    def _create_income_tab_widgets(self, parent_frame):
        """Widgets for the Income tab (Add, View, Edit, Delete Income)."""
        parent_frame.grid_rowconfigure(1, weight=3)
        parent_frame.grid_columnconfigure(0, weight=1)

        # --- Input Frame (Compact Layout) ---
        input_frame = ttk.LabelFrame(parent_frame, text="Add/Edit Income", padding="15 10", style="TLabelframe") 
        input_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)
        input_frame.grid_columnconfigure(3, weight=1)

        # Row 0: Date and Source
        ttk.Label(input_frame, text="Date (YYYY-MM-DD):", background=self.frame_bg).grid(row=0, column=0, sticky="w", pady=4, padx=5)
        self.income_date_entry = DateEntry(input_frame, width=15, background='darkblue', foreground='white', borderwidth=2,
                                    year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                                    date_pattern='yyyy-mm-dd', selectmode='day', font=(self.font_family, 10))
        self.income_date_entry.grid(row=0, column=1, pady=4, padx=5, sticky="ew")

        ttk.Label(input_frame, text="Source:", background=self.frame_bg).grid(row=0, column=2, sticky="w", pady=4, padx=5)
        self.income_source_entry = ttk.Entry(input_frame)
        self.income_source_entry.grid(row=0, column=3, pady=4, padx=5, sticky="ew")
        
        # Row 1: Amount and Description
        ttk.Label(input_frame, text="Amount (₹):", background=self.frame_bg).grid(row=1, column=0, sticky="w", pady=4, padx=5)
        self.income_amount_entry = ttk.Entry(input_frame, validate="key", validatecommand=(self.master.register(self._validate_numeric_input), '%P'))
        self.income_amount_entry.grid(row=1, column=1, pady=4, padx=5, sticky="ew")

        ttk.Label(input_frame, text="Description:", background=self.frame_bg).grid(row=1, column=2, sticky="w", pady=4, padx=5)
        self.income_description_entry = ttk.Entry(input_frame)
        self.income_description_entry.grid(row=1, column=3, pady=4, padx=5, sticky="ew")

        # Buttons Frame (Centered)
        button_frame = ttk.Frame(input_frame, style="TFrame")
        button_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1) # For centering

        self.add_update_income_button = ttk.Button(button_frame, text="➕ Add Income", command=self.add_income_gui, style="Income.TButton")
        self.add_update_income_button.grid(row=0, column=1, padx=5, sticky="ew")

        self.cancel_income_edit_button = ttk.Button(button_frame, text="✖️ Cancel Edit", command=self.cancel_income_edit, style="TButton")
        self.cancel_income_edit_button.grid(row=0, column=2, padx=5, sticky="ew")
        self.cancel_income_edit_button.grid_remove()

        # --- Income List Frame with Filters ---
        income_list_filter_frame = ttk.LabelFrame(parent_frame, text="All Income", padding="15 10", style="TLabelframe") 
        income_list_filter_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        income_list_filter_frame.grid_rowconfigure(3, weight=1)
        income_list_filter_frame.grid_columnconfigure(1, weight=1)
        income_list_filter_frame.grid_columnconfigure(3, weight=1)

        filter_row = 0
        ttk.Label(income_list_filter_frame, text="Start Date:", background=self.frame_bg).grid(row=filter_row, column=0, sticky="w", padx=5, pady=2)
        self.income_filter_start_date = DateEntry(income_list_filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', selectmode='day', font=(self.font_family, 9))
        self.income_filter_start_date.grid(row=filter_row, column=1, sticky="ew", padx=5, pady=2)
        self.income_filter_start_date.set_date(None)

        ttk.Label(income_list_filter_frame, text="End Date:", background=self.frame_bg).grid(row=filter_row, column=2, sticky="w", padx=5, pady=2)
        self.income_filter_end_date = DateEntry(income_list_filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', selectmode='day', font=(self.font_family, 9))
        self.income_filter_end_date.grid(row=filter_row, column=3, sticky="ew", padx=5, pady=2)
        self.income_filter_end_date.set_date(None)

        filter_row += 1
        ttk.Label(income_list_filter_frame, text="Source:", background=self.frame_bg).grid(row=filter_row, column=0, sticky="w", padx=5, pady=2)
        self.income_filter_source_entry = ttk.Entry(income_list_filter_frame, font=(self.font_family, 9))
        self.income_filter_source_entry.grid(row=filter_row, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(income_list_filter_frame, text="Search:", background=self.frame_bg).grid(row=filter_row, column=2, sticky="w", padx=5, pady=2)
        self.income_filter_keyword_entry = ttk.Entry(income_list_filter_frame, font=(self.font_family, 9))
        self.income_filter_keyword_entry.grid(row=filter_row, column=3, sticky="ew", padx=5, pady=2)
        self.income_filter_keyword_entry.bind("<Return>", lambda e: self.apply_income_filters())

        filter_row += 1
        apply_filter_button = ttk.Button(income_list_filter_frame, text="🔍 Apply Filters", command=self.apply_income_filters, style="TButton")
        apply_filter_button.grid(row=filter_row, column=0, columnspan=2, pady=5, padx=5, sticky="ew")
        clear_filter_button = ttk.Button(income_list_filter_frame, text="🧹 Clear Filters", command=self.clear_income_filters, style="TButton")
        clear_filter_button.grid(row=filter_row, column=2, columnspan=2, pady=5, padx=5, sticky="ew")

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

        action_button_frame = ttk.Frame(income_list_filter_frame, style="TFrame")
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
        filter_frame = ttk.LabelFrame(parent_frame, text="Analytics Filters", padding="15 10", style="TLabelframe") 
        filter_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        filter_frame.grid_columnconfigure(1, weight=1)
        filter_frame.grid_columnconfigure(3, weight=1)

        current_year = datetime.now().year
        self.analytics_years = sorted(list(set(self.db.get_all_expense_years() + self.db.get_all_income_years() + [str(current_year)])), reverse=True)
        self.analytics_years.insert(0, "All Years")

        self.analytics_months = [f"{i:02d}" for i in range(1, 13)]

        ttk.Label(filter_frame, text="Select Year:", background=self.frame_bg).grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.analytics_year_combobox = ttk.Combobox(filter_frame, values=self.analytics_years, state="readonly", font=(self.font_family, 10))
        self.analytics_year_combobox.set(str(current_year)) # Set to current year by default
        self.analytics_year_combobox.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(filter_frame, text="Select Month:", background=self.frame_bg).grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.analytics_month_combobox = ttk.Combobox(filter_frame, values=["All"] + self.analytics_months, state="readonly", font=(self.font_family, 10))
        self.analytics_month_combobox.set("All")
        self.analytics_month_combobox.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        
        ttk.Label(filter_frame, text="Select Category (for Trend):", background=self.frame_bg).grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.analytics_category_combobox = ttk.Combobox(filter_frame, values=["All Categories"] + self.db.get_categories(), state="readonly", font=(self.font_family, 10))
        self.analytics_category_combobox.set("All Categories")
        self.analytics_category_combobox.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        self.analytics_category_combobox.bind("<FocusIn>", lambda e: self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories()))


        # Chart Type Buttons
        chart_buttons_frame = ttk.Frame(filter_frame, style="TFrame")
        chart_buttons_frame.grid(row=3, column=0, columnspan=4, pady=10, sticky="ew")
        chart_buttons_frame.grid_columnconfigure(0, weight=1)
        chart_buttons_frame.grid_columnconfigure(1, weight=1)
        chart_buttons_frame.grid_columnconfigure(2, weight=1)
        chart_buttons_frame.grid_columnconfigure(3, weight=1)

        ttk.Button(chart_buttons_frame, text="📊 Category Pie Chart", command=self.generate_pie_chart_filtered, style="Accent.TButton").grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(chart_buttons_frame, text="📈 Monthly Bar Chart", command=self.generate_bar_chart_filtered, style="Accent.TButton").grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(chart_buttons_frame, text="📉 Overall Trend Chart", command=self.generate_monthly_spending_trend_chart, style="Accent.TButton").grid(row=0, column=2, padx=5, sticky="ew")
        ttk.Button(chart_buttons_frame, text="📈 Category Trend Chart", command=self.generate_category_spending_trend_chart, style="Accent.TButton").grid(row=0, column=3, padx=5, sticky="ew")


        # --- Chart Display Frame ---
        self.chart_display_frame = ttk.Frame(parent_frame, style="ChartDisplay.TFrame")
        self.chart_display_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.chart_display_frame.grid_rowconfigure(0, weight=1)
        self.chart_display_frame.grid_columnconfigure(0, weight=1)

        # Initialize figure and canvas once
        plt.style.use('dark_background') # Matplotlib dark theme
        self.figure = plt.Figure(figsize=(10, 8), dpi=100, facecolor=self.frame_bg) 
        self.canvas_widget = FigureCanvasTkAgg(self.figure, master=self.chart_display_frame)
        self.canvas_widget.get_tk_widget().pack(expand=True, fill="both")
        self.no_data_label_chart = None # To manage the "No data" label for charts specifically

        # Initial chart display
        self.generate_pie_chart_filtered()


    def _create_data_tab_widgets(self, parent_frame):
        """Widgets for the Data Management tab (Categories, Backup/Restore, Erase)."""
        parent_frame.grid_columnconfigure(0, weight=1) 
        parent_frame.grid_rowconfigure(0, weight=1) 
        parent_frame.grid_rowconfigure(1, weight=1) 

        # Use a main frame to hold content and center it
        main_data_frame = ttk.Frame(parent_frame, style="TFrame", padding="20")
        main_data_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_data_frame.grid_columnconfigure(0, weight=1) 
        main_data_frame.grid_rowconfigure(0, weight=1)
        main_data_frame.grid_rowconfigure(1, weight=1)


        # --- Categories Management Frame ---
        category_frame = ttk.LabelFrame(main_data_frame, text="Manage Categories", padding="15 10", style="TLabelframe") 
        category_frame.grid(row=0, column=0, padx=10, pady=(5, 10), sticky="ew")
        category_frame.grid_columnconfigure(0, weight=1) 

        ttk.Label(category_frame, text="Use the button below to open the Category Manager window.", background=self.frame_bg, font=(self.font_family, 10)).grid(row=0, column=0, sticky="ew", pady=10, padx=5)
        ttk.Button(category_frame, text="📂 Open Category Manager", command=self.open_category_manager, style="TButton").grid(row=1, column=0, sticky="ew", padx=5, pady=5)


        # --- Backup/Restore/Erase Frame ---
        backup_restore_frame = ttk.LabelFrame(main_data_frame, text="Data Management", padding="15 10", style="TLabelframe") 
        backup_restore_frame.grid(row=1, column=0, padx=10, pady=(10, 5), sticky="ew")
        backup_restore_frame.grid_columnconfigure(0, weight=1)

        # Safe Actions Section
        safe_actions_frame = ttk.LabelFrame(backup_restore_frame, text="Safe Actions", padding="10", style="TLabelframe")
        safe_actions_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        safe_actions_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(safe_actions_frame, text="Backup your current data:", background=self.frame_bg, font=(self.font_family, 10)).grid(row=0, column=0, sticky="ew", pady=5, padx=5)
        ttk.Button(safe_actions_frame, text="💾 Backup Database", command=self.backup_database, style="TButton").grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(safe_actions_frame, text="Import data from another database file (merges):", background=self.frame_bg, font=(self.font_family, 10)).grid(row=2, column=0, sticky="ew", pady=10, padx=5)
        ttk.Button(safe_actions_frame, text="📥 Import Database", command=self.import_database, style="TButton").grid(row=3, column=0, sticky="ew", padx=5, pady=5)

        # Danger Zone Section
        danger_zone_frame = ttk.LabelFrame(backup_restore_frame, text="Danger Zone", padding="10", style="TLabelframe")
        danger_zone_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=15)
        danger_zone_frame.grid_columnconfigure(0, weight=1)
        # Apply a distinct background for danger zone if desired, or rely on title
        # self.style.configure("DangerZone.TLabelframe", background="#5C3A3A") # Example if different color desired

        ttk.Label(danger_zone_frame, text="Restore data from a backup file (overwrites current data):", background=self.frame_bg, font=(self.font_family, 10)).grid(row=0, column=0, sticky="ew", pady=5, padx=5)
        ttk.Button(danger_zone_frame, text="↩️ Restore Database", command=self.restore_database, style="Delete.TButton").grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(danger_zone_frame, text="Completely erase all data (PERMANENT):", background=self.frame_bg, font=(self.font_family, 10)).grid(row=2, column=0, sticky="ew", pady=10, padx=5)
        ttk.Button(danger_zone_frame, text="⚠️ Erase Database", command=self.erase_database, style="Delete.TButton").grid(row=3, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(backup_restore_frame, text="Note: Restoring/Importing/Eraseing are powerful actions. Proceed with caution.", foreground=self.accent_danger, font=(self.font_family, 9, "italic"), background=self.frame_bg).grid(row=2, column=0, sticky="ew", padx=5, pady=2)


    # --- Event Handlers and Logic Methods ---
    def on_tab_change(self, event):
        """Handles actions when the tab is changed."""
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if "Analytics" in selected_tab: 
            self.update_analytics_filters_and_chart()
        elif "Expenses" in selected_tab:
            self.update_summary_and_budget_display()
            self.view_expenses()
            self.expense_category_combobox.config(values=self.db.get_categories()) 
            self._update_budget_month_year_comboboxes() # Update budget selectors
        elif "Income" in selected_tab:
            self.view_income()
            self.update_summary_and_budget_display()
        elif "Data" in selected_tab:
            pass 
        elif "Dashboard" in selected_tab:
            self.update_dashboard_summary()

    def _validate_numeric_input(self, P):
        """Validates if the input is a valid number (float or empty string)."""
        if P == "" or (P.replace('.', '', 1).isdigit() and P.count('.') <= 1):
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
            self.update_status_bar("Error: Date, Category, and Amount are required.", self.accent_danger)
            messagebox.showwarning("Input Error", "Date, Category, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.update_status_bar("Error: Amount must be positive.", self.accent_danger)
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid amount.", self.accent_danger)
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if self.db.add_expense(date, category, amount, description):
            self.update_status_bar("Expense added successfully! 🎉", self.accent_primary)
            self.clear_expense_entries()
            self.view_expenses()
            self.update_summary_and_budget_display()
            self.update_analytics_filters_and_chart()
            self.update_dashboard_summary()
            self.expense_category_combobox.config(values=self.db.get_categories())
        else:
            self.update_status_bar("Failed to add expense.", self.accent_danger)
            messagebox.showerror("Error", "Failed to add expense.")

    def edit_expense_gui(self):
        """Populates input fields with selected expense for editing."""
        selected_item = self.expense_tree.selection()
        if not selected_item:
            self.update_status_bar("Please select an expense to edit.", self.accent_orange)
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
            self.update_status_bar("No expense selected for update.", self.accent_danger)
            messagebox.showerror("Error", "No expense selected for update.")
            return

        date = self.expense_date_entry.get_date().strftime("%Y-%m-%d")
        category = self.expense_category_combobox.get().strip()
        amount_str = self.expense_amount_entry.get().strip()
        description = self.expense_description_entry.get().strip()

        if not date or not category or not amount_str:
            self.update_status_bar("Error: Date, Category, and Amount are required.", self.accent_danger)
            messagebox.showwarning("Input Error", "Date, Category, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.update_status_bar("Error: Amount must be positive.", self.accent_danger)
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid amount.", self.accent_danger)
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if messagebox.askyesno("Confirm Update", f"Are you sure you want to update expense ID: {self.selected_expense_id}?"):
            if self.db.update_expense(self.selected_expense_id, date, category, amount, description):
                self.update_status_bar("Expense updated successfully! ✨", self.accent_primary)
                self.clear_expense_entries()
                self.view_expenses()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.update_dashboard_summary()
                self.expense_category_combobox.config(values=self.db.get_categories())
            else:
                self.update_status_bar("Failed to update expense.", self.accent_danger)
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
            self.update_status_bar("Please select an expense to delete.", self.accent_orange)
            messagebox.showwarning("Selection Error", "Please select an expense to delete.")
            return

        item_values = self.expense_tree.item(selected_item, 'values')
        expense_id = item_values[0]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete expense ID: {expense_id}?\nThis action cannot be undone."):
            if self.db.delete_expense(expense_id):
                self.update_status_bar("Expense deleted successfully! 🗑️", self.accent_primary)
                self.clear_expense_entries()
                self.view_expenses()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.update_dashboard_summary()
                self.expense_category_combobox.config(values=self.db.get_categories())
            else:
                self.update_status_bar("Failed to delete expense.", self.accent_danger)
                messagebox.showerror("Error", "Failed to delete expense.")

    def apply_expense_filters(self):
        """Applies filters to the expense Treeview."""
        start_date_obj = self.expense_filter_start_date.get_date()
        end_date_obj = self.expense_filter_end_date.get_date()
        category = self.expense_filter_category_combobox.get()
        keyword = self.expense_filter_keyword_entry.get().strip()

        start_date = start_date_obj.strftime("%Y-%m-%d") if start_date_obj else None
        end_date = end_date_obj.strftime("%Y-%m-%d") if end_date_obj else None

        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        expenses = self.db.fetch_expenses(start_date=start_date, end_date=end_date, category=category, keyword=keyword)

        if not expenses:
            self.expense_tree.insert("", tk.END, values=("", "", "No expenses found with these filters.", "", ""), tags=('center_text',))
            self.expense_tree.tag_configure('center_text', anchor='center')
            self.update_status_bar("No expenses found with applied filters.", self.accent_orange)
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
        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        expenses = self.db.fetch_expenses()
        if not expenses:
            self.expense_tree.insert("", tk.END, values=("", "", "No expenses recorded yet.", "", ""), tags=('center_text',))
            self.expense_tree.tag_configure('center_text', anchor='center')
            return

        for exp in expenses:
            formatted_amount = f"₹{exp[3]:,.2f}"
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
            self.update_status_bar("Error: Date, Source, and Amount are required.", self.accent_danger)
            messagebox.showwarning("Input Error", "Date, Source, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.update_status_bar("Error: Amount must be positive.", self.accent_danger)
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid amount.", self.accent_danger)
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if self.db.add_income(date, source, amount, description):
            self.update_status_bar("Income added successfully! 🎉", self.accent_primary)
            self.clear_income_entries()
            self.view_income()
            self.update_summary_and_budget_display()
            self.update_analytics_filters_and_chart()
            self.update_dashboard_summary()
        else:
            self.update_status_bar("Failed to add income.", self.accent_danger)
            messagebox.showerror("Error", "Failed to add income.")

    def edit_income_gui(self):
        """Populates input fields with selected income for editing."""
        selected_item = self.income_tree.selection()
        if not selected_item:
            self.update_status_bar("Please select an income entry to edit.", self.accent_orange)
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
            self.update_status_bar("No income selected for update.", self.accent_danger)
            messagebox.showerror("Error", "No income selected for update.")
            return

        date = self.income_date_entry.get_date().strftime("%Y-%m-%d")
        source = self.income_source_entry.get().strip()
        amount_str = self.income_amount_entry.get().strip()
        description = self.income_description_entry.get().strip()

        if not date or not source or not amount_str:
            self.update_status_bar("Error: Date, Source, and Amount are required.", self.accent_danger)
            messagebox.showwarning("Input Error", "Date, Source, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.update_status_bar("Error: Amount must be positive.", self.accent_danger)
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid amount.", self.accent_danger)
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if messagebox.askyesno("Confirm Update", f"Are you sure you want to update income ID: {self.selected_income_id}?"):
            if self.db.update_income(self.selected_income_id, date, source, amount, description):
                self.update_status_bar("Income updated successfully! ✨", self.accent_primary)
                self.clear_income_entries()
                self.view_income()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.update_dashboard_summary()
            else:
                self.update_status_bar("Failed to update income.", self.accent_danger)
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
            self.update_status_bar("Please select an income entry to delete.", self.accent_orange)
            messagebox.showwarning("Selection Error", "Please select an income entry to delete.")
            return

        item_values = self.income_tree.item(selected_item, 'values')
        income_id = item_values[0]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete income ID: {income_id}?\nThis action cannot be undone."):
            if self.db.delete_income(income_id):
                self.update_status_bar("Income deleted successfully! 🗑️", self.accent_primary)
                self.clear_income_entries()
                self.view_income()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.update_dashboard_summary()
            else:
                self.update_status_bar("Failed to delete income.", self.accent_danger)
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
            self.update_status_bar("No income found with applied filters.", self.accent_orange)
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


    def update_dashboard_summary(self):
        """Updates the summary cards on the Dashboard tab."""
        current_month_year = datetime.now().strftime("%Y-%m")
        expenses_this_month = self.db.fetch_expenses_by_month_year(current_month_year)
        income_this_month = self.db.fetch_income(month_year=current_month_year)

        total_spent = sum(exp[3] for exp in expenses_this_month)
        total_income = sum(inc[3] for inc in income_this_month)
        net_balance = total_income - total_spent
        monthly_budget = self.db.get_monthly_budget(current_month_year)
        remaining_budget = monthly_budget - total_spent

        self.dashboard_income_label.config(text=f"₹{total_income:,.2f}")
        self.dashboard_expenses_label.config(text=f"₹{total_spent:,.2f}")
        self.dashboard_net_balance_label.config(text=f"₹{net_balance:,.2f}",
                                                 foreground=self.accent_primary if net_balance >= 0 else self.accent_danger)
        
        self.dashboard_budget_label.config(text=f"Budget: ₹{monthly_budget:,.2f} | Spent: ₹{total_spent:,.2f} | Remaining: ₹{remaining_budget:,.2f}")
        
        if remaining_budget >= 0:
            self.dashboard_budget_status_label.config(text="On Track! ✅", foreground=self.accent_primary)
        else:
            self.dashboard_budget_status_label.config(text="Over Budget! ⚠️", foreground=self.accent_danger)

        # Update dashboard chart (e.g., small bar chart of top categories)
        self._prepare_chart_area(is_dashboard=True)

        category_totals = collections.defaultdict(float)
        for exp in expenses_this_month:
            category_totals[exp[2].capitalize()] += exp[3]

        if not category_totals:
            self.display_no_chart_data_message("No expenses this month for dashboard chart.", is_dashboard=True)
            return

        # Get top 5 categories
        sorted_categories = sorted(category_totals.items(), key=lambda item: item[1], reverse=True)[:5]
        labels = [item[0] for item in sorted_categories]
        sizes = [item[1] for item in sorted_categories]

        ax = self.dashboard_figure.add_subplot(111)
        # Using a subset of chart_colors for the dashboard bar chart
        ax.bar(labels, sizes, color=self.chart_colors[:len(labels)]) 
        ax.set_title("Top 5 Expense Categories (This Month)", fontsize=10, color=self.text_color)
        ax.set_ylabel("Amount (₹)", fontsize=8, color=self.text_color)
        # Apply bold font weight to x-tick labels and adjust rotation for better visibility
        ax.tick_params(axis='x', rotation=0, labelsize=8, colors=self.text_color) # Set rotation to 0
        plt.setp(ax.get_xticklabels(), ha="center") # Align horizontally
        for label in ax.get_xticklabels():
            label.set_fontweight('bold')
        ax.tick_params(axis='y', labelsize=8, colors=self.text_color)
        ax.set_facecolor(self.frame_bg) # Set subplot background
        self.dashboard_figure.set_facecolor(self.frame_bg) # Set figure background
        plt.tight_layout() # Adjust layout to prevent labels overlapping
        self.dashboard_canvas_widget.draw()


    def update_summary_and_budget_display(self):
        """Updates the category summary, overall budget, and net balance information."""
        # Get selected month/year for budget display
        selected_month = self.set_budget_month_combobox.get()
        selected_year = self.set_budget_year_combobox.get()
        
        # Ensure a month and year are selected for budget display
        if not selected_month or not selected_year:
            current_month_year = datetime.now().strftime("%Y-%m")
        else:
            current_month_year = f"{selected_year}-{selected_month}"

        expenses_this_month = self.db.fetch_expenses_by_month_year(current_month_year)
        income_this_month = self.db.fetch_income(month_year=current_month_year)
        
        total_spent_this_month = sum(exp[3] for exp in expenses_this_month)
        monthly_budget = self.db.get_monthly_budget(current_month_year)
        remaining_overall_budget = monthly_budget - total_spent_this_month

        self.budget_amount_label.config(text=f"₹{monthly_budget:,.2f}")
        self.spent_amount_label.config(text=f"₹{total_spent_this_month:,.2f}")

        if remaining_overall_budget >= 0:
            self.remaining_budget_label.config(text=f"₹{remaining_overall_budget:,.2f}", foreground=self.accent_primary)
        else:
            self.remaining_budget_label.config(text=f"₹{remaining_overall_budget:,.2f} (Over Budget)", foreground=self.accent_danger)

        total_income_this_month = sum(inc[3] for inc in income_this_month)
        net_balance = total_income_this_month - total_spent_this_month
        self.net_balance_label.config(text=f"₹{net_balance:,.2f}", foreground=self.accent_info if net_balance >= 0 else self.accent_danger)


        category_spending_this_month = collections.defaultdict(float)
        for exp in expenses_this_month:
            category_spending_this_month[exp[2].capitalize()] += exp[3]

        category_summary_content = ""
        if not category_spending_this_month:
            category_summary_content = "No categorized expenses for this month."
        else:
            # Format for better alignment in Text widget
            header = f"{'Category'.ljust(15)} {'Spent (₹)'}\n"
            category_summary_content += header
            category_summary_content += "-" * len(header) + "\n"

            for category, spent in sorted(category_spending_this_month.items()):
                spent_str = f"{spent:,.2f}" # Format without currency symbol here for alignment
                category_summary_content += f"{category.ljust(15)[:15]} {spent_str}\n"

        self.category_summary_text.config(state=tk.NORMAL)
        self.category_summary_text.delete(1.0, tk.END)
        self.category_summary_text.insert(tk.END, category_summary_content)
        self.category_summary_text.config(state=tk.DISABLED)

    def _update_budget_month_year_comboboxes(self):
        """Updates the year combobox for budget setting with available years."""
        current_year = datetime.now().year
        # Get all years from expenses and income, add current year, sort and make unique
        all_expense_years = self.db.get_all_expense_years()
        all_income_years = self.db.get_all_income_years()
        all_years_in_db = sorted(list(set(all_expense_years + all_income_years + [str(current_year)])), reverse=True)
        
        # Add a range of years around current year if no data exists
        if not all_years_in_db:
            years_range = [str(y) for y in range(current_year - 5, current_year + 6)]
            self.set_budget_year_combobox['values'] = years_range
            self.set_budget_year_combobox.set(str(current_year))
        else:
            self.set_budget_year_combobox['values'] = all_years_in_db
            if str(current_year) in all_years_in_db:
                self.set_budget_year_combobox.set(str(current_year))
            else:
                self.set_budget_year_combobox.set(all_years_in_db[0]) # Set to most recent year if current not found

        self.set_budget_month_combobox.set(datetime.now().strftime("%m")) # Always default to current month


    def set_budget_gui(self):
        """Handles setting the overall monthly budget from the GUI for a selected MM-YYYY."""
        budget_amount_str = self.set_budget_entry.get().strip()
        selected_month = self.set_budget_month_combobox.get()
        selected_year = self.set_budget_year_combobox.get()

        if not selected_month or not selected_year:
            self.update_status_bar("Error: Please select a month and year for the budget.", self.accent_danger)
            messagebox.showwarning("Input Error", "Please select a month and year for the budget.")
            return

        if not budget_amount_str:
            self.update_status_bar("Error: Please enter a budget amount.", self.accent_danger)
            messagebox.showwarning("Input Error", "Please enter a budget amount.")
            return

        try:
            budget_amount = float(budget_amount_str)
            if budget_amount < 0:
                self.update_status_bar("Error: Budget amount cannot be negative.", self.accent_danger)
                messagebox.showwarning("Input Error", "Budget amount cannot be negative.")
                return
        except ValueError:
            self.update_status_bar("Error: Invalid amount.", self.accent_danger)
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        month_year_to_set = f"{selected_year}-{selected_month}"
        if self.db.set_monthly_budget(month_year_to_set, budget_amount):
            self.update_status_bar(f"Monthly budget for {month_year_to_set} set to ₹{budget_amount:,.2f}! 💰", self.accent_primary)
            self.set_budget_entry.delete(0, tk.END)
            self.update_summary_and_budget_display()
            self.update_dashboard_summary()
        else:
            self.update_status_bar("Failed to set budget.", self.accent_danger)
            messagebox.showerror("Error", "Failed to set budget.")

    # --- Category Management Methods ---
    def open_category_manager(self):
        """Opens a new Toplevel window for managing categories."""
        category_manager_window = tk.Toplevel(self.master)
        category_manager_window.title("Category Manager")
        category_manager_window.geometry("450x400")
        category_manager_window.transient(self.master) # Make it appear on top of the main window
        category_manager_window.grab_set() # Disable interaction with main window until this is closed
        category_manager_window.protocol("WM_DELETE_WINDOW", lambda: self._on_category_manager_close(category_manager_window)) # Handle close button

        # Apply styles to the new window
        category_manager_window.config(bg=self.master_bg)
        
        cat_frame = ttk.Frame(category_manager_window, style="TFrame", padding="15")
        cat_frame.pack(expand=True, fill="both", padx=10, pady=10)
        cat_frame.grid_columnconfigure(1, weight=1)
        cat_frame.grid_rowconfigure(2, weight=1)

        ttk.Label(cat_frame, text="Category Name:", background=self.frame_bg, font=(self.font_family, 10)).grid(row=0, column=0, sticky="w", pady=4, padx=5)
        self.category_name_entry_mgr = ttk.Entry(cat_frame)
        self.category_name_entry_mgr.grid(row=0, column=1, pady=4, padx=5, sticky="ew")

        cat_button_frame_mgr = ttk.Frame(cat_frame, style="TFrame")
        cat_button_frame_mgr.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")
        cat_button_frame_mgr.grid_columnconfigure(0, weight=1)
        cat_button_frame_mgr.grid_columnconfigure(1, weight=1)
        cat_button_frame_mgr.grid_columnconfigure(2, weight=1)

        ttk.Button(cat_button_frame_mgr, text="➕ Add", command=self.add_category_gui_mgr, style="Accent.TButton").grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(cat_button_frame_mgr, text="✏️ Edit", command=self.edit_category_gui_mgr, style="Edit.TButton").grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(cat_button_frame_mgr, text="🗑️ Delete", command=self.delete_category_gui_mgr, style="Delete.TButton").grid(row=0, column=2, padx=5, sticky="ew")

        self.category_tree_mgr = ttk.Treeview(cat_frame, columns=("CategoryName",), show="headings", selectmode="browse", style="Treeview")
        self.category_tree_mgr.heading("CategoryName", text="Category Name", anchor=tk.W)
        self.category_tree_mgr.column("CategoryName", width=200, stretch=tk.YES)
        self.category_tree_mgr.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=10)

        cat_scrollbar_mgr = ttk.Scrollbar(cat_frame, orient=tk.VERTICAL, command=self.category_tree_mgr.yview)
        self.category_tree_mgr.configure(yscrollcommand=cat_scrollbar_mgr.set)
        cat_scrollbar_mgr.grid(row=2, column=2, sticky="ns", pady=10)

        self.category_tree_mgr.bind("<<TreeviewSelect>>", self._on_category_select_mgr)

        self.view_categories_mgr() # Populate the list in the manager window

    def _on_category_manager_close(self, window):
        """Actions to perform when the category manager window is closed."""
        self.update_status_bar("Category manager closed. Refreshing category lists.")
        # Refresh all comboboxes that use categories
        self.expense_category_combobox.config(values=self.db.get_categories())
        self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories())
        self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories())
        window.destroy()
        self.master.grab_release() # Release grab on main window

    def _on_category_select_mgr(self, event):
        """Populates the entry with the selected category name in the manager window."""
        selected_item = self.category_tree_mgr.selection()
        if selected_item:
            category_name = self.category_tree_mgr.item(selected_item, 'values')[0]
            self.category_name_entry_mgr.delete(0, tk.END)
            self.category_name_entry_mgr.insert(0, category_name)

    def view_categories_mgr(self):
        """Populates the category Treeview in the Category Manager window."""
        for item in self.category_tree_mgr.get_children():
            self.category_tree_mgr.delete(item)
        
        categories = self.db.get_categories()
        if not categories:
            self.category_tree_mgr.insert("", tk.END, values=("No categories defined.",), tags=('center_text',))
            self.category_tree_mgr.tag_configure('center_text', anchor='center')
            return

        for cat in categories:
            self.category_tree_mgr.insert("", tk.END, values=(cat,))
        # No status bar update here, as it's a sub-window operation

    def add_category_gui_mgr(self):
        """Adds a new category from the Category Manager GUI."""
        category_name = self.category_name_entry_mgr.get().strip()
        if not category_name:
            messagebox.showwarning("Input Error", "Category name cannot be empty.")
            return
        
        if self.db.add_category(category_name):
            messagebox.showinfo("Success", f"Category '{category_name}' added successfully!")
            self.category_name_entry_mgr.delete(0, tk.END)
            self.view_categories_mgr()
        # No else block needed as DBManager already shows error/warning

    def edit_category_gui_mgr(self):
        """Initiates editing of a selected category from the Category Manager GUI."""
        selected_item = self.category_tree_mgr.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a category to edit.")
            return
        
        old_category_name = self.category_tree_mgr.item(selected_item, 'values')[0]
        new_category_name = self.category_name_entry_mgr.get().strip()

        if not new_category_name:
            messagebox.showwarning("Input Error", "New category name cannot be empty.")
            return

        if new_category_name == old_category_name:
            messagebox.showinfo("No Change", "The new category name is the same as the old one.")
            return

        if messagebox.askyesno("Confirm Edit", f"Are you sure you want to rename '{old_category_name}' to '{new_category_name}'?\nThis will also update all related expenses."):
            if self.db.update_category(old_category_name, new_category_name):
                messagebox.showinfo("Success", f"Category '{old_category_name}' renamed to '{new_category_name}' successfully!")
                self.category_name_entry_mgr.delete(0, tk.END)
                self.view_categories_mgr()
                self.view_expenses() # Refresh main expense list
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.update_dashboard_summary()
            # No else block needed as DBManager already shows error/warning

    def delete_category_gui_mgr(self):
        """Deletes a selected category from the Category Manager GUI."""
        selected_item = self.category_tree_mgr.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a category to delete.")
            return
        
        category_name = self.category_tree_mgr.item(selected_item, 'values')[0]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete category '{category_name}'?\nAll expenses under this category will be set to 'Uncategorized'."):
            if self.db.delete_category(category_name):
                messagebox.showinfo("Success", f"Category '{category_name}' deleted successfully!")
                self.view_categories_mgr()
                self.view_expenses() # Refresh main expense list
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.update_dashboard_summary()
            # No else block needed as DBManager already shows error/warning

    # --- Backup/Restore Methods ---
    def backup_database(self):
        """Backs up the current database file."""
        try:
            default_filename = f"finance_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            file_path = filedialog.asksaveasfilename(
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                initialfile=default_filename
            )
            if file_path:
                self.db.close() # Close connection before copying
                shutil.copyfile(self.db.db_name, file_path)
                self.db._connect() # Re-establish connection
                self.update_status_bar(f"Database backed up to: {file_path} ✅", self.accent_primary)
            else:
                self.update_status_bar("Database backup canceled.", self.accent_orange)
        except Exception as e:
            self.update_status_bar(f"Error backing up database: {e}", self.accent_danger)
            messagebox.showerror("Backup Error", f"Failed to backup database: {e}")

    def restore_database(self):
        """Restores the database from a selected backup file. Overwrites current data."""
        if not messagebox.askyesno("Confirm Restore", "WARNING: Restoring will OVERWRITE your current data. Are you sure you want to proceed?"):
            self.update_status_bar("Database restore canceled.", self.accent_orange)
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
                self.update_status_bar(f"Database restored from: {file_path} ✅", self.accent_primary)
                # Refresh all data displays across tabs
                self.view_expenses()
                self.view_income()
                self.update_summary_and_budget_display()
                self.update_analytics_filters_and_chart()
                self.update_dashboard_summary()
                # Update all comboboxes that use categories
                self.expense_category_combobox.config(values=self.db.get_categories())
                self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories())
                self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories())
                self._update_budget_month_year_comboboxes() # Update budget selectors
            else:
                self.update_status_bar("Database restore canceled.", self.accent_orange)
        except Exception as e:
            self.update_status_bar(f"Error restoring database: {e}", self.accent_danger)
            messagebox.showerror("Restore Error", f"Failed to restore database: {e}")
            # Attempt to reconnect to potentially corrupted/missing original DB
            self.db._connect()

    def import_database(self):
        """Imports data from another database file, merging it with the current database."""
        if not messagebox.askyesno("Confirm Import", "WARNING: Importing will MERGE data from the selected file into your current database. Existing entries with the same ID might be overwritten. Are you sure you want to proceed?"):
            self.update_status_bar("Database import canceled.", self.accent_orange)
            return

        try:
            file_path = filedialog.askopenfilename(
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")]
            )
            if file_path:
                # Create a temporary connection to the selected database
                temp_conn = sqlite3.connect(file_path)
                temp_cursor = temp_conn.cursor()

                # Fetch all data from the temporary database
                temp_cursor.execute("SELECT * FROM expenses")
                temp_expenses = temp_cursor.fetchall()

                temp_cursor.execute("SELECT * FROM income")
                temp_income = temp_cursor.fetchall()

                temp_cursor.execute("SELECT * FROM categories")
                temp_categories = temp_cursor.fetchall()

                temp_cursor.execute("SELECT * FROM budgets")
                temp_budgets = temp_cursor.fetchall()

                temp_conn.close() # Close temp connection

                # Now, insert/replace into the main database
                self.db.conn.execute("BEGIN TRANSACTION")
                try:
                    # Insert or replace expenses
                    for exp in temp_expenses:
                        self.db.cursor.execute('''
                            INSERT OR REPLACE INTO expenses (id, date, category, amount, description)
                            VALUES (?, ?, ?, ?, ?)
                        ''', exp)
                    
                    # Insert or replace income
                    for inc in temp_income:
                        self.db.cursor.execute('''
                            INSERT OR REPLACE INTO income (id, date, source, amount, description)
                            VALUES (?, ?, ?, ?, ?)
                        ''', inc)

                    # Insert or ignore categories (to avoid duplicates, existing categories are not overwritten)
                    for cat in temp_categories:
                        self.db.cursor.execute('''
                            INSERT OR IGNORE INTO categories (name) VALUES (?)
                        ''', (cat[1],)) # cat[1] is the name column

                    # Insert or replace budgets
                    for budget in temp_budgets:
                        self.db.cursor.execute('''
                            INSERT OR REPLACE INTO budgets (id, month_year, budget_amount)
                            VALUES (?, ?, ?)
                        ''', budget)

                    self.db.conn.commit()
                    self.update_status_bar(f"Data imported successfully from: {file_path} ✅", self.accent_primary)
                    # Refresh all data displays across tabs
                    self.view_expenses()
                    self.view_income()
                    self.update_summary_and_budget_display()
                    self.update_analytics_filters_and_chart()
                    self.update_dashboard_summary()
                    # Update all comboboxes that use categories
                    self.expense_category_combobox.config(values=self.db.get_categories())
                    self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories())
                    self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories())
                    self._update_budget_month_year_comboboxes() # Update budget selectors

                except sqlite3.Error as e:
                    self.db.conn.rollback() # Rollback if any error occurs during transaction
                    raise e # Re-raise to be caught by outer except block

            else:
                self.update_status_bar("Database import canceled.", self.accent_orange)
        except Exception as e:
            self.update_status_bar(f"Error importing database: {e}", self.accent_danger)
            messagebox.showerror("Import Error", f"Failed to import database: {e}")

    def erase_database(self):
        """Completely erases the database file."""
        if not messagebox.askyesno("Confirm Erase", "DANGER: This will PERMANENTLY DELETE ALL your financial data. This action cannot be undone. Are you absolutely sure you want to proceed?"):
            self.update_status_bar("Database erase canceled.", self.accent_orange)
            return
        
        try:
            self.db.close() # Close connection first
            if os.path.exists(self.db.db_name):
                os.remove(self.db.db_name)
                self.update_status_bar("Database erased successfully! 💥", self.accent_primary)
            else:
                self.update_status_bar("Database file not found, nothing to erase.", self.accent_orange)
            
            # Reinitialize the database (will create a new empty one with default categories and 0.00 budget)
            self.db = DatabaseManager()
            # Refresh all UI elements
            self.view_expenses()
            self.view_income()
            self.update_summary_and_budget_display()
            self.update_analytics_filters_and_chart()
            self.update_dashboard_summary()
            self.expense_category_combobox.config(values=self.db.get_categories())
            self.expense_filter_category_combobox.config(values=["All Categories"] + self.db.get_categories())
            self.analytics_category_combobox.config(values=["All Categories"] + self.db.get_categories())
            self._update_budget_month_year_comboboxes() # Update budget selectors

        except Exception as e:
            self.update_status_bar(f"Error erasing database: {e}", self.accent_danger)
            messagebox.showerror("Erase Error", f"Failed to erase database: {e}")
            # Attempt to reconnect in case of partial error
            self.db._connect()


    # --- Charting Methods ---
    def _prepare_chart_area(self, is_dashboard=False):
        """Clears the existing Matplotlib figure and prepares it for new plotting.
           Selects the correct figure/canvas based on whether it's for dashboard or analytics."""
        
        figure_to_clear = self.dashboard_figure if is_dashboard else self.figure
        canvas_to_draw = self.dashboard_canvas_widget if is_dashboard else self.canvas_widget
        
        # Clear all axes from the figure
        figure_to_clear.clear()
        # Ensure the canvas widget is visible if it was hidden (e.g., by a no_data_label)
        if not canvas_to_draw.get_tk_widget().winfo_ismapped():
            canvas_to_draw.get_tk_widget().pack(expand=True, fill="both")
        canvas_to_draw.draw_idle() # Redraw to show blank canvas

    def display_no_chart_data_message(self, message, is_dashboard=False):
        """Displays a message when no data is available for charts by drawing on the figure."""
        self._prepare_chart_area(is_dashboard=is_dashboard) # Ensure any existing plot is cleared
        
        figure_to_use = self.dashboard_figure if is_dashboard else self.figure
        canvas_to_draw = self.dashboard_canvas_widget if is_dashboard else self.canvas_widget
        
        ax = figure_to_use.add_subplot(111)
        ax.text(0.5, 0.5, message, horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=12, color=self.text_color, style='italic')
        ax.set_xticks([]) # Hide ticks
        ax.set_yticks([])
        ax.set_frame_on(False) # Hide frame
        ax.set_facecolor(self.frame_bg) # Ensure background matches
        figure_to_use.set_facecolor(self.frame_bg) # Ensure figure background matches
        canvas_to_draw.draw()

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
        """Generates and displays a DONUT chart of expenses by category, filtered by month/year."""
        self._prepare_chart_area()

        selected_year = self.analytics_year_combobox.get()
        selected_month = self.analytics_month_combobox.get()

        if selected_year == "All Years":
            self.display_no_chart_data_message("Please select a specific year for a meaningful Donut Chart.")
            return
        
        expenses = self.get_filtered_data_for_charts(data_type="expenses")

        if not expenses:
            self.display_no_chart_data_message("No expenses recorded for the selected period to generate charts.")
            return

        category_totals = collections.defaultdict(float)
        for exp in expenses:
            category_totals[exp[2].capitalize()] += exp[3]

        if not category_totals:
            self.display_no_chart_data_message("No categorized expenses for the selected period.")
            return

        # --- Combine small slices into "Other" ---
        total_sum = sum(category_totals.values())
        min_percentage = 2.0  # Minimum percentage for individual slice
        
        large_slices = {}
        other_sum = 0.0
        
        for label, value in category_totals.items():
            percentage = (value / total_sum) * 100
            if percentage >= min_percentage:
                large_slices[label] = value
            else:
                other_sum += value
        
        if other_sum > 0:
            large_slices["Other"] = other_sum

        labels = list(large_slices.keys())
        sizes = list(large_slices.values())

        ax = self.figure.add_subplot(111)
        
        # Create donut chart
        wedges, texts = ax.pie(
            sizes,
            labels=labels,
            colors=self.chart_colors,
            startangle=140,
            wedgeprops={'width': 0.4, 'edgecolor': 'black'},  # Key change for donut
            textprops=dict(color=self.text_color, fontsize=10, fontweight='bold')
        )

        # Add percentage labels inside the wedges
        for i, wedge in enumerate(wedges):
            angle = (wedge.theta2 - wedge.theta1)/2. + wedge.theta1
            x = 0.6 * np.cos(np.deg2rad(angle))  # Position inside the ring
            y = 0.6 * np.sin(np.deg2rad(angle))
            percentage = 100. * sizes[i]/total_sum
            if percentage >= min_percentage:
                ax.text(x, y, f"{percentage:.1f}%", 
                        ha='center', va='center', 
                        fontsize=9, fontweight='bold', 
                        color='white' if percentage < 5 else '#333333')

        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        
        chart_title_suffix = f" for {selected_month}/{selected_year}" if selected_month != "All" else f" for {selected_year}"
        ax.set_title(f"Expense Distribution by Category{chart_title_suffix}", fontsize=12, color=self.text_color)
        ax.set_facecolor(self.frame_bg)
        self.figure.set_facecolor(self.frame_bg)

        self.canvas_widget.draw()

    def generate_bar_chart_filtered(self):
        """Generates and displays a bar chart of monthly spending, filtered by selected year."""
        self._prepare_chart_area()
        
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

        ax = self.figure.add_subplot(111)
        ax.bar(display_labels, amounts, color=self.accent_info) 
        ax.set_xlabel("Month", color=self.text_color)
        ax.set_ylabel("Total Amount (₹)", color=self.text_color)
        ax.set_title(f"Monthly Spending Overview for {selected_year}", fontsize=12, color=self.text_color)
        ax.tick_params(axis='x', rotation=45, labelsize=9, colors=self.text_color)
        for label in ax.get_xticklabels():
            label.set_fontweight('bold')
        ax.tick_params(axis='y', labelsize=9, colors=self.text_color)
        ax.grid(axis='y', linestyle='--', alpha=0.7, color="#555555") 
        ax.set_facecolor(self.frame_bg)
        self.figure.set_facecolor(self.frame_bg)
        plt.tight_layout()

        self.canvas_widget.draw()

    def generate_monthly_spending_trend_chart(self):
        """Generates and displays a line chart of overall spending trend across months/years."""
        self._prepare_chart_area()

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

        ax = self.figure.add_subplot(111)
        ax.plot(display_labels, amounts, marker='o', linestyle='-', color=self.accent_primary)
        ax.set_xlabel("Month and Year", color=self.text_color)
        ax.set_ylabel("Total Amount (₹)", color=self.text_color)
        
        chart_title = "Overall Monthly Spending Trend"
        if selected_year != "All Years":
            chart_title += f" in {selected_year}"
        
        ax.set_title(chart_title, fontsize=14, color=self.text_color)
        ax.tick_params(axis='x', rotation=45, labelsize=8, colors=self.text_color)
        for label in ax.get_xticklabels():
            label.set_fontweight('bold')
        ax.tick_params(axis='y', labelsize=8, colors=self.text_color)
        ax.grid(True, linestyle='--', alpha=0.6, color="#555555")
        ax.set_facecolor(self.frame_bg)
        self.figure.set_facecolor(self.frame_bg)
        plt.tight_layout()

        self.canvas_widget.draw()

    def generate_category_spending_trend_chart(self):
        """Generates a line chart showing spending trend for a specific category over time."""
        self._prepare_chart_area()

        selected_category = self.analytics_category_combobox.get()
        selected_year = self.analytics_year_combobox.get()
        selected_month = self.analytics_month_combobox.get()

        if selected_category == "All Categories":
            self.display_no_chart_data_message("Please select a specific category to generate a category trend chart.")
            return
        if selected_month != "All":
            self.display_no_chart_data_message("Category Trend Chart shows spending across months/years. Please set 'Select Month' to 'All'.")
            return

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

        ax = self.figure.add_subplot(111)
        ax.plot(display_labels, amounts, marker='o', linestyle='-', color=self.accent_orange)
        ax.set_xlabel("Month and Year", color=self.text_color)
        ax.set_ylabel(f"Amount Spent in {selected_category} (₹)", color=self.text_color)
        
        chart_title = f"Spending Trend for '{selected_category}'"
        if selected_year != "All Years":
            chart_title += f" in {selected_year}"
        
        ax.set_title(chart_title, fontsize=14, color=self.text_color)
        ax.tick_params(axis='x', rotation=45, labelsize=8, colors=self.text_color)
        for label in ax.get_xticklabels():
            label.set_fontweight('bold')
        ax.tick_params(axis='y', labelsize=8, colors=self.text_color)
        ax.grid(True, linestyle='--', alpha=0.6, color="#555555")
        ax.set_facecolor(self.frame_bg)
        self.figure.set_facecolor(self.frame_bg)
        plt.tight_layout()

        self.canvas_widget.draw()


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

        # Regenerate the default chart (e.e., pie chart for selected year/all)
        self.generate_pie_chart_filtered()


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

