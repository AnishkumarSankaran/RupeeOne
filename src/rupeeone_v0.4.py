import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import sqlite3
from datetime import datetime
import collections
import shutil
import os
import webbrowser
from PIL import Image, ImageTk
import sv_ttk
import threading
from tkcalendar import DateEntry

# --- Matplotlib Imports ---
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cursor = self.conn.cursor()
            print(f"Connected to database: {self.db_name}")
        except sqlite3.Error as e:
            # This error is critical, so we show it and prevent the app from running.
            messagebox.showerror("Database Connection Error", f"Failed to connect to the database: {e}\nThe application cannot continue.")
            self.conn = None
            self.cursor = None

    def _create_tables(self):
        """Creates tables if they don't exist and populates default data."""
        if not self.cursor: return
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
                    category TEXT NOT NULL, amount REAL NOT NULL, description TEXT
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, month_year TEXT UNIQUE NOT NULL,
                    budget_amount REAL NOT NULL
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS income (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
                    source TEXT NOT NULL, amount REAL NOT NULL, description TEXT
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL
                )
            ''')
            self.conn.commit()
            self._add_default_data()
        except sqlite3.Error as e:
            messagebox.showerror("Database Table Error", f"Failed to create tables: {e}")

    def _add_default_data(self):
        """Adds default categories and budget if tables are empty."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM categories")
            if self.cursor.fetchone()[0] == 0:
                default_categories = [
                    ("Food",), ("Transport",), ("Utilities",), ("Rent",),
                    ("Entertainment",), ("Shopping",), ("Healthcare",),
                    ("Education",), ("Salary",), ("Freelance",), ("Investments",)
                ]
                self.cursor.executemany("INSERT INTO categories (name) VALUES (?)", default_categories)
                self.conn.commit()

            # --- IMPROVEMENT: Set a more reasonable default budget, e.g., 5000.00 if none exists ---
            self.cursor.execute("SELECT COUNT(*) FROM budgets")
            if self.cursor.fetchone()[0] == 0:
                current_month_year = datetime.now().strftime("%Y-%m")
                self.cursor.execute("INSERT INTO budgets (month_year, budget_amount) VALUES (?, ?)", (current_month_year, 5000.00)) # Default budget
                self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Default Data Error", f"Failed to add default data: {e}")

    def execute_query(self, query, params=(), fetch=None):
        """A generic method to execute database queries with error handling."""
        if not self.cursor: return [] if fetch else False
        try:
            self.cursor.execute(query, params)
            if fetch == "one":
                return self.cursor.fetchone()
            elif fetch == "all":
                return self.cursor.fetchall()
            else:
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Query Error", f"An error occurred: {e}")
            if fetch:
                return [] if fetch == "all" else None
            return False

    def add_expense(self, date, category, amount, description):
        query = "INSERT INTO expenses (date, category, amount, description) VALUES (?, ?, ?, ?)"
        return self.execute_query(query, (date, category, amount, description))

    def fetch_expenses(self, **filters):
        query = "SELECT * FROM expenses WHERE 1=1"
        params = []
        if filters.get("start_date"):
            query += " AND date >= ?"
            params.append(filters["start_date"])
        if filters.get("end_date"):
            query += " AND date <= ?"
            params.append(filters["end_date"])
        if filters.get("category") and filters["category"] != "All Categories":
            query += " AND category = ?"
            params.append(filters["category"])
        if filters.get("month_year"):
            query += " AND STRFTIME('%Y-%m', date) = ?"
            params.append(filters["month_year"])
        query += " ORDER BY date DESC"
        return self.execute_query(query, params, fetch="all")
        
    def delete_expense(self, expense_id):
        return self.execute_query("DELETE FROM expenses WHERE id = ?", (expense_id,))

    def add_income(self, date, source, amount, description):
        query = "INSERT INTO income (date, source, amount, description) VALUES (?, ?, ?, ?)"
        return self.execute_query(query, (date, source, amount, description))

    def fetch_income(self, **filters):
        query = "SELECT * FROM income WHERE 1=1"
        params = []
        if filters.get("month_year"):
            query += " AND STRFTIME('%Y-%m', date) = ?"
            params.append(filters["month_year"])
        query += " ORDER BY date DESC"
        return self.execute_query(query, params, fetch="all")

    # --- IMPROVEMENT: Added delete_income method ---
    def delete_income(self, income_id):
        return self.execute_query("DELETE FROM income WHERE id = ?", (income_id,))

    def get_categories(self):
        return [row[0] for row in self.execute_query("SELECT name FROM categories ORDER BY name ASC", fetch="all")]

    def get_monthly_budget(self, month_year):
        result = self.execute_query("SELECT budget_amount FROM budgets WHERE month_year = ?", (month_year,), fetch="one")
        return result[0] if result else 0.0

    def set_monthly_budget(self, month_year, amount):
        query = "INSERT OR REPLACE INTO budgets (month_year, budget_amount) VALUES (?, ?)"
        return self.execute_query(query, (month_year, amount))

    def close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

# --- Expense Tracker GUI Application Class ---
class ExpenseTrackerApp:
    """Main application class for the GUI Expense Tracker."""

    # --- REFACTOR: Centralized configuration dictionary ---
    CONFIG = {
        "font_family": "Segoe UI",
        "db_name": "expenses.db",
        "colors": {
            "primary": "#4361ee",
            "secondary": "#3f37c9",
            "success": "#4cc9f0",
            "warning": "#f72585",
            "danger": "#e63946",
            "info": "#4895ef",
            "light": "#f8f9fa",
            "dark": "#212529",
            "card_bg": "#3a3a3a",
            "chart_bg": "#2c2c2c"
        },
        "chart_colors": [
            "#4CAF50", "#2196F3", "#FFC107", "#FF5722", "#9C27B0",
            "#00BCD4", "#FFEB3B", "#795548", "#E91E63", "#607D8B"
        ]
    }

    def __init__(self, master):
        self.master = master
        master.title("RupeeOne - Personal Finance Tracker") # Changed app name
        master.geometry("1280x800")
        master.minsize(1024, 768)

        sv_ttk.set_theme("dark")

        self.db = DatabaseManager(self.CONFIG["db_name"])
        if not self.db.conn:
            master.destroy()
            return

        self._configure_styles()
        self.create_widgets()
        self.on_tab_change(None) # Initial load of the first tab
        self.update_status_bar("Welcome to RupeeOne! ✨") # Changed app name

    def _configure_styles(self):
        """Configures all ttk styles for the application."""
        style = ttk.Style()
        font_family = self.CONFIG["font_family"]
        colors = self.CONFIG["colors"]

        # Fonts
        self.heading_font = (font_family, 18, "bold")
        self.body_font = (font_family, 10)
        self.button_font = (font_family, 10, "bold")

        # General Styles
        style.configure("TButton", font=self.button_font, padding=8)
        style.configure("TLabel", font=self.body_font)
        style.configure("Card.TFrame", background=colors["card_bg"])
        style.configure("Treeview.Heading", font=(font_family, 10, "bold"))
        style.configure("Treeview", rowheight=28)

        # Button Styles
        style.map("TButton",
                  background=[('active', colors["secondary"]), ('!disabled', colors["primary"])],
                  foreground=[('!disabled', colors["light"])])
        style.configure("Delete.TButton", background=colors["danger"], foreground=colors["light"])
        style.map("Delete.TButton", background=[('active', '#C02A38')])

    def create_widgets(self):
        """Creates and arranges all GUI elements."""
        main_container = ttk.Frame(self.master, style="Card.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header = ttk.Frame(main_container)
        header.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(header, text="RupeeOne", font=self.heading_font, foreground=self.CONFIG["colors"]["primary"]).pack(side=tk.LEFT) # Changed app name

        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create tabs
        self.dashboard_tab = ttk.Frame(self.notebook)
        self.expenses_tab = ttk.Frame(self.notebook)
        self.income_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.dashboard_tab, text="Dashboard 📊")
        self.notebook.add(self.expenses_tab, text="Expenses 💸")
        self.notebook.add(self.income_tab, text="Income 💰")

        # Populate tabs
        self._create_dashboard_tab(self.dashboard_tab)
        
        # --- REFACTOR: Use a helper method to create transaction tabs ---
        self._create_transaction_tab(self.expenses_tab, "Expense")
        self._create_transaction_tab(self.income_tab, "Income")

        self.status_label = ttk.Label(main_container, text="", anchor="w")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def _create_dashboard_tab(self, parent):
        """Creates the widgets for the dashboard tab."""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Summary Cards Frame
        cards_frame = ttk.Frame(parent)
        cards_frame.grid(row=0, column=0, sticky="ew", pady=10)
        for i in range(3):
            cards_frame.grid_columnconfigure(i, weight=1)

        self.income_card_var = tk.StringVar(value="₹0.00")
        self.expense_card_var = tk.StringVar(value="₹0.00")
        self.balance_card_var = tk.StringVar(value="₹0.00")

        self._create_dashboard_card(cards_frame, "Total Income", self.income_card_var, 0)
        self._create_dashboard_card(cards_frame, "Total Expenses", self.expense_card_var, 1)
        self._create_dashboard_card(cards_frame, "Net Balance", self.balance_card_var, 2)
        
        # Chart Frame
        chart_frame = ttk.LabelFrame(parent, text="Monthly Spending Breakdown", padding=10)
        chart_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.dashboard_figure = plt.Figure(figsize=(5, 4), dpi=100, facecolor=self.CONFIG["colors"]["chart_bg"])
        self.dashboard_canvas = FigureCanvasTkAgg(self.dashboard_figure, master=chart_frame)
        self.dashboard_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _create_dashboard_card(self, parent, title, string_var, col):
        """Helper to create a single dashboard card."""
        card = ttk.Frame(parent, style="Card.TFrame", padding=15)
        card.grid(row=0, column=col, sticky="nsew", padx=10)
        ttk.Label(card, text=title, font=(self.CONFIG["font_family"], 12)).pack()
        ttk.Label(card, textvariable=string_var, font=(self.CONFIG["font_family"], 24, "bold"), foreground=self.CONFIG["colors"]["light"]).pack(pady=5)

    # --- REFACTOR: A single method to create the UI for both Expenses and Income ---
    def _create_transaction_tab(self, parent, trans_type):
        """
        Creates a standardized tab for managing transactions (Expenses or Income).
        This method reduces code duplication significantly.
        """
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(parent, text=f"Add/Edit {trans_type}", padding=15)
        input_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        for i in range(4):
            input_frame.grid_columnconfigure(i, weight=1 if i % 2 != 0 else 0)

        # Store widgets in a dictionary to avoid instance variable clutter
        widgets = {}

        ttk.Label(input_frame, text="Date:").grid(row=0, column=0, sticky="w", padx=5)
        widgets['date_entry'] = DateEntry(input_frame, date_pattern='yyyy-mm-dd', width=15)
        widgets['date_entry'].grid(row=0, column=1, sticky="ew", padx=5)

        # Differentiate between 'Category' for Expense and 'Source' for Income
        label_text = "Category:" if trans_type == "Expense" else "Source:"
        ttk.Label(input_frame, text=label_text).grid(row=0, column=2, sticky="w", padx=5)
        if trans_type == "Expense":
            widgets['cat_source_entry'] = ttk.Combobox(input_frame, values=self.db.get_categories())
        else:
            widgets['cat_source_entry'] = ttk.Entry(input_frame)
        widgets['cat_source_entry'].grid(row=0, column=3, sticky="ew", padx=5)
        
        ttk.Label(input_frame, text="Amount (₹):").grid(row=1, column=0, sticky="w", padx=5)
        widgets['amount_entry'] = ttk.Entry(input_frame)
        widgets['amount_entry'].grid(row=1, column=1, sticky="ew", padx=5)

        ttk.Label(input_frame, text="Description:").grid(row=1, column=2, sticky="w", padx=5)
        widgets['desc_entry'] = ttk.Entry(input_frame)
        widgets['desc_entry'].grid(row=1, column=3, sticky="ew", padx=5)

        # Add Button
        add_cmd = lambda: self.add_transaction(trans_type, widgets)
        widgets['add_btn'] = ttk.Button(input_frame, text=f"➕ Add {trans_type}", command=add_cmd)
        widgets['add_btn'].grid(row=2, column=0, columnspan=4, pady=10)

        # --- Data List Frame ---
        list_frame = ttk.LabelFrame(parent, text=f"All {trans_type}s", padding=15)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        cols = ("ID", "Date", "Category/Source", "Amount", "Description")
        widgets['tree'] = ttk.Treeview(list_frame, columns=cols, show="headings")
        for col in cols:
            widgets['tree'].heading(col, text=col)
        widgets['tree'].column("ID", width=50, stretch=tk.NO)
        widgets['tree'].grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=widgets['tree'].yview)
        widgets['tree'].configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Delete Button
        delete_cmd = lambda: self.delete_transaction(trans_type, widgets['tree'])
        widgets['delete_btn'] = ttk.Button(list_frame, text=f"🗑️ Delete Selected", command=delete_cmd, style="Delete.TButton")
        widgets['delete_btn'].grid(row=1, column=0, columnspan=2, pady=10)

        # Store the dictionary of widgets on the instance for later access
        setattr(self, f"{trans_type.lower()}_widgets", widgets)

    def on_tab_change(self, event):
        """Handles actions when the tab is changed."""
        selected_tab_index = self.notebook.index(self.notebook.select())
        if selected_tab_index == 0: # Dashboard
            self.update_dashboard()
        elif selected_tab_index == 1: # Expenses
            self.refresh_transaction_view("Expense")
        elif selected_tab_index == 2: # Income
            self.refresh_transaction_view("Income")

    def update_dashboard(self):
        """Updates all dashboard components."""
        current_month_year = datetime.now().strftime("%Y-%m")
        
        # --- REFACTOR: Added error handling for database calls ---
        try:
            expenses = self.db.fetch_expenses(month_year=current_month_year)
            income = self.db.fetch_income(month_year=current_month_year)
        except sqlite3.Error as e:
            self.update_status_bar(f"Error fetching dashboard data: {e}", "red")
            return

        total_spent = sum(exp[3] for exp in expenses)
        total_income = sum(inc[3] for inc in income)
        net_balance = total_income - total_spent

        self.income_card_var.set(f"₹{total_income:,.2f}")
        self.expense_card_var.set(f"₹{total_spent:,.2f}")
        self.balance_card_var.set(f"₹{net_balance:,.2f}")

        self.update_dashboard_chart(expenses)

    def update_dashboard_chart(self, expenses):
        """Updates the dashboard pie chart."""
        self.dashboard_figure.clear()
        
        if not expenses:
            ax = self.dashboard_figure.add_subplot(111)
            ax.text(0.5, 0.5, "No data for this month", ha="center", va="center", color="white")
            ax.set_facecolor(self.CONFIG["colors"]["chart_bg"])
            self.dashboard_canvas.draw()
            return
            
        category_totals = collections.defaultdict(float)
        for _, _, category, amount, _ in expenses:
            category_totals[category] += amount

        labels = list(category_totals.keys())
        sizes = list(category_totals.values())

        ax = self.dashboard_figure.add_subplot(111)
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
               colors=self.CONFIG["chart_colors"],
               textprops={'color': self.CONFIG["colors"]["light"]})
        ax.axis('equal')
        ax.set_title("Spending by Category", color=self.CONFIG["colors"]["light"])
        self.dashboard_figure.set_facecolor(self.CONFIG["colors"]["chart_bg"])
        
        self.dashboard_canvas.draw()

    def add_transaction(self, trans_type, widgets):
        """Handles adding a new expense or income."""
        date = widgets['date_entry'].get_date().strftime("%Y-%m-%d")
        cat_source = widgets['cat_source_entry'].get().strip()
        amount_str = widgets['amount_entry'].get().strip()
        desc = widgets['desc_entry'].get().strip()

        if not all([date, cat_source, amount_str]):
            messagebox.showwarning("Input Error", "Date, Category/Source, and Amount are required.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter a valid numeric amount.")
            return

        success = False
        try:
            if trans_type == "Expense":
                success = self.db.add_expense(date, cat_source, amount, desc)
            else: # Income
                success = self.db.add_income(date, cat_source, amount, desc)
        except sqlite3.Error as e:
            self.update_status_bar(f"Error adding {trans_type}: {e}", "red")

        if success:
            self.update_status_bar(f"{trans_type} added successfully!", "green")
            self.refresh_transaction_view(trans_type)
            # Clear entries
            widgets['cat_source_entry'].delete(0, tk.END)
            widgets['amount_entry'].delete(0, tk.END)
            widgets['desc_entry'].delete(0, tk.END)
            # Re-populate categories for expense combobox if it's an expense and a new category was added (though the current design only allows selection)
            if trans_type == "Expense":
                widgets['cat_source_entry']['values'] = self.db.get_categories()
        else:
            self.update_status_bar(f"Failed to add {trans_type}.", "red")

    def delete_transaction(self, trans_type, tree):
        """Handles deleting a selected transaction."""
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", f"Please select an {trans_type.lower()} to delete.")
            return

        item_id = tree.item(selected_item, "values")[0]
        
        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete this {trans_type.lower()}?"):
            return

        success = False
        try:
            if trans_type == "Expense":
                success = self.db.delete_expense(item_id)
            elif trans_type == "Income": # --- IMPROVEMENT: Call delete_income ---
                success = self.db.delete_income(item_id)
        except sqlite3.Error as e:
            self.update_status_bar(f"Error deleting {trans_type}: {e}", "red")

        if success:
            self.update_status_bar(f"{trans_type} deleted successfully!", "green")
            self.refresh_transaction_view(trans_type)
        else:
            self.update_status_bar(f"Failed to delete {trans_type}.", "red")

    def refresh_transaction_view(self, trans_type):
        """Refreshes the Treeview with the latest data."""
        widgets = getattr(self, f"{trans_type.lower()}_widgets")
        tree = widgets['tree']
        
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)

        try:
            if trans_type == "Expense":
                records = self.db.fetch_expenses()
            else: # Income
                records = self.db.fetch_income()
        except sqlite3.Error as e:
            self.update_status_bar(f"Error fetching {trans_type} data: {e}", "red")
            return

        for record in records:
            # Format amount with currency
            formatted_record = list(record)
            formatted_record[3] = f"₹{record[3]:,.2f}"
            tree.insert("", tk.END, values=formatted_record)

    def update_status_bar(self, message, color="white"):
        """Updates the status bar with a message."""
        self.status_label.config(text=message, foreground=color)

def main():
    """Initializes and runs the Tkinter application."""
    root = tk.Tk()
    app = ExpenseTrackerApp(root)
    
    # Set window icon
    try:
        # The 'icon.png' file should be in the same directory as the script.
        img = Image.open("icon.png") 
        icon = ImageTk.PhotoImage(img)
        root.iconphoto(False, icon)
    except FileNotFoundError:
        print("Warning: 'icon.png' not found. The application will use a default icon.")
    except Exception as e:
        print(f"Could not load icon: {e}")
    
    # Gracefully close the database connection on exit
    def on_closing():
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            app.db.close()
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()