import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import sqlite3
from datetime import datetime
from tkcalendar import DateEntry # For the date picker
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections # For counting categories in charts

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
        """Creates the 'expenses' and 'budgets' tables if they don't already exist."""
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
                # Budgets table (simple monthly budget for now)
                # We'll store a single monthly budget value.
                # For category-specific budgets, the schema would need to be more complex.
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS budgets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        month_year TEXT UNIQUE NOT NULL, -- e.g., '2025-07'
                        budget_amount REAL NOT NULL
                    )
                ''')
                self.conn.commit()
                print("Tables 'expenses' and 'budgets' checked/created successfully.")
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

    def fetch_expenses(self, start_date=None, end_date=None, category=None):
        """Fetches expense records with optional filters."""
        if not self.cursor: return []
        query = "SELECT * FROM expenses WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if category:
            query += " AND category LIKE ?"
            params.append(f"%{category}%")

        query += " ORDER BY date DESC"

        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch expenses: {e}")
            return []

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
        master.title("Personal Expense Tracker")
        master.geometry("1000x700") # Increased size for more features
        master.resizable(True, True) # Allow resizing

        self.db = DatabaseManager()
        if not self.db.conn:
            messagebox.showerror("Initialization Error", "Could not connect to database. Exiting application.")
            master.destroy()
            return

        # Styling for a modern look
        self.style = ttk.Style()
        self.style.theme_use('clam') # 'clam', 'alt', 'default', 'classic'
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        self.style.configure("TButton", font=("Arial", 10, "bold"), padding=5)
        self.style.configure("TEntry", padding=3)
        self.style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        self.style.configure("Treeview", font=("Arial", 9))

        self.selected_expense_id = None # To keep track of expense being edited

        self.create_widgets()
        self.view_expenses() # Load expenses on startup
        self.update_summary_and_budget_display()

    def create_widgets(self):
        """Creates and arranges all GUI elements using a tabbed interface."""
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # --- Tab 1: Expenses ---
        self.expenses_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.expenses_tab, text="Expenses")
        self._create_expenses_tab_widgets(self.expenses_tab)

        # --- Tab 2: Reports ---
        self.reports_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.reports_tab, text="Reports")
        self._create_reports_tab_widgets(self.reports_tab)

        # Bind tab change event to refresh reports
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def _create_expenses_tab_widgets(self, parent_frame):
        """Widgets for the Expenses tab (Add, View, Edit, Delete)."""
        # Configure grid for parent_frame
        parent_frame.grid_rowconfigure(1, weight=1) # Allow list_frame to expand
        parent_frame.grid_columnconfigure(0, weight=1)

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(parent_frame, text="Add/Edit Expense", padding="10 10")
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Date Input with DateEntry
        ttk.Label(input_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        self.date_entry = DateEntry(input_frame, width=27, background='darkblue', foreground='white', borderwidth=2,
                                     year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                                     date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=0, column=1, pady=2, padx=5, sticky="ew")

        # Category Input
        ttk.Label(input_frame, text="Category:").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        self.category_entry = ttk.Entry(input_frame, width=30)
        self.category_entry.grid(row=1, column=1, pady=2, padx=5, sticky="ew")

        # Amount Input
        ttk.Label(input_frame, text="Amount (₹):").grid(row=2, column=0, sticky="w", pady=2, padx=5)
        self.amount_entry = ttk.Entry(input_frame, width=30)
        self.amount_entry.grid(row=2, column=1, pady=2, padx=5, sticky="ew")

        # Description Input
        ttk.Label(input_frame, text="Description:").grid(row=3, column=0, sticky="w", pady=2, padx=5)
        self.description_entry = ttk.Entry(input_frame, width=30)
        self.description_entry.grid(row=3, column=1, pady=2, padx=5, sticky="ew")

        # Buttons for Add/Update and Cancel Edit
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.add_update_button = ttk.Button(button_frame, text="Add Expense", command=self.add_expense_gui)
        self.add_update_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.cancel_edit_button = ttk.Button(button_frame, text="Cancel Edit", command=self.cancel_edit, state=tk.DISABLED)
        self.cancel_edit_button.grid(row=0, column=1, padx=5, sticky="ew")

        # --- Expense List Frame ---
        list_frame = ttk.LabelFrame(parent_frame, text="All Expenses", padding="10 10")
        list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Treeview (Table) to display expenses
        columns = ("ID", "Date", "Category", "Amount", "Description")
        self.expense_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        # Define column headings and widths
        self.expense_tree.heading("ID", text="ID", anchor=tk.CENTER)
        self.expense_tree.heading("Date", text="Date", anchor=tk.CENTER)
        self.expense_tree.heading("Category", text="Category", anchor=tk.CENTER)
        self.expense_tree.heading("Amount", text="Amount (₹)", anchor=tk.CENTER)
        self.expense_tree.heading("Description", text="Description", anchor=tk.CENTER)

        self.expense_tree.column("ID", width=50, anchor=tk.CENTER, stretch=tk.NO)
        self.expense_tree.column("Date", width=100, anchor=tk.CENTER, stretch=tk.NO)
        self.expense_tree.column("Category", width=120, anchor=tk.W, stretch=tk.NO)
        self.expense_tree.column("Amount", width=100, anchor=tk.E, stretch=tk.NO)
        self.expense_tree.column("Description", width=250, anchor=tk.W, stretch=tk.YES)

        self.expense_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for Treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.expense_tree.yview)
        self.expense_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Buttons for Edit and Delete
        action_button_frame = ttk.Frame(list_frame)
        action_button_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        action_button_frame.grid_columnconfigure(0, weight=1)
        action_button_frame.grid_columnconfigure(1, weight=1)

        edit_button = ttk.Button(action_button_frame, text="Edit Selected Expense", command=self.edit_expense_gui)
        edit_button.grid(row=0, column=0, padx=5, sticky="ew")

        delete_button = ttk.Button(action_button_frame, text="Delete Selected Expense", command=self.delete_expense_gui)
        delete_button.grid(row=0, column=1, padx=5, sticky="ew")

        # --- Summary and Budget Frame (bottom of expenses tab) ---
        summary_budget_frame = ttk.LabelFrame(parent_frame, text="Summary & Budget", padding="10 10")
        summary_budget_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        summary_budget_frame.grid_columnconfigure(0, weight=1)
        summary_budget_frame.grid_columnconfigure(1, weight=1)

        # Category Summary Display
        ttk.Label(summary_budget_frame, text="Category Breakdown:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        self.category_summary_text = tk.Text(summary_budget_frame, height=5, width=40, state=tk.DISABLED, wrap=tk.WORD)
        self.category_summary_text.grid(row=1, column=0, sticky="nsew", pady=2, padx=5)

        # Budget Section
        ttk.Label(summary_budget_frame, text="Current Month Budget:").grid(row=0, column=1, sticky="w", pady=2, padx=5)
        self.budget_amount_label = ttk.Label(summary_budget_frame, text="₹0.00", font=("Arial", 12, "bold"))
        self.budget_amount_label.grid(row=1, column=1, sticky="w", pady=2, padx=5)

        ttk.Label(summary_budget_frame, text="Spent This Month:").grid(row=2, column=1, sticky="w", pady=2, padx=5)
        self.spent_amount_label = ttk.Label(summary_budget_frame, text="₹0.00", font=("Arial", 12, "bold"))
        self.spent_amount_label.grid(row=3, column=1, sticky="w", pady=2, padx=5)

        ttk.Label(summary_budget_frame, text="Remaining Budget:").grid(row=4, column=1, sticky="w", pady=2, padx=5)
        self.remaining_budget_label = ttk.Label(summary_budget_frame, text="₹0.00", font=("Arial", 12, "bold", "italic"), foreground="green")
        self.remaining_budget_label.grid(row=5, column=1, sticky="w", pady=2, padx=5)

        ttk.Label(summary_budget_frame, text="Set Monthly Budget (₹):").grid(row=2, column=0, sticky="w", pady=2, padx=5)
        self.set_budget_entry = ttk.Entry(summary_budget_frame, width=20)
        self.set_budget_entry.grid(row=3, column=0, sticky="ew", pady=2, padx=5)
        set_budget_button = ttk.Button(summary_budget_frame, text="Set Budget", command=self.set_budget_gui)
        set_budget_button.grid(row=4, column=0, sticky="ew", pady=5, padx=5)


    def _create_reports_tab_widgets(self, parent_frame):
        """Widgets for the Reports tab (Charts)."""
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)

        chart_frame = ttk.Frame(parent_frame, padding="10 10")
        chart_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        chart_frame.grid_rowconfigure(0, weight=1)
        chart_frame.grid_columnconfigure(0, weight=1)

        # Placeholder for matplotlib canvas
        self.canvas_widget = None

        # Buttons to generate different charts
        chart_buttons_frame = ttk.Frame(chart_frame)
        chart_buttons_frame.grid(row=1, column=0, pady=10, sticky="ew")
        chart_buttons_frame.grid_columnconfigure(0, weight=1)
        chart_buttons_frame.grid_columnconfigure(1, weight=1)

        ttk.Button(chart_buttons_frame, text="Generate Category Pie Chart", command=self.generate_pie_chart).grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(chart_buttons_frame, text="Generate Monthly Bar Chart", command=self.generate_bar_chart).grid(row=0, column=1, padx=5, sticky="ew")

        # Initial chart display (e.g., pie chart)
        self.generate_pie_chart()


    def on_tab_change(self, event):
        """Handles actions when the tab is changed."""
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if selected_tab == "Reports":
            self.generate_pie_chart() # Refresh default chart when reports tab is opened
        elif selected_tab == "Expenses":
            self.update_summary_and_budget_display()


    def clear_entries(self):
        """Clears the input fields and resets the add/update state."""
        self.date_entry.set_date(datetime.now().date()) # Reset date picker
        self.category_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)
        self.add_update_button.config(text="Add Expense", command=self.add_expense_gui)
        self.cancel_edit_button.config(state=tk.DISABLED)
        self.selected_expense_id = None

    def add_expense_gui(self):
        """Handles adding a new expense from the GUI."""
        date = self.date_entry.get_date().strftime("%Y-%m-%d")
        category = self.category_entry.get().strip()
        amount_str = self.amount_entry.get().strip()
        description = self.description_entry.get().strip()

        if not date or not category or not amount_str:
            messagebox.showwarning("Input Error", "Date, Category, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if self.db.add_expense(date, category, amount, description):
            messagebox.showinfo("Success", "Expense added successfully!")
            self.clear_entries()
            self.view_expenses() # Refresh the list
            self.update_summary_and_budget_display()
        else:
            messagebox.showerror("Error", "Failed to add expense.")


    def edit_expense_gui(self):
        """Populates input fields with selected expense for editing."""
        selected_item = self.expense_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select an expense to edit.")
            return

        # Get the values of the selected item
        item_values = self.expense_tree.item(selected_item, 'values')
        self.selected_expense_id = item_values[0] # Store ID for update

        # Populate entry fields
        self.date_entry.set_date(datetime.strptime(item_values[1], "%Y-%m-%d").date())
        self.category_entry.delete(0, tk.END)
        self.category_entry.insert(0, item_values[2])
        self.amount_entry.delete(0, tk.END)
        # Remove '₹' and commas for editing
        self.amount_entry.insert(0, item_values[3].replace('₹', '').replace(',', ''))
        self.description_entry.delete(0, tk.END)
        self.description_entry.insert(0, item_values[4])

        # Change button text and command
        self.add_update_button.config(text="Save Changes", command=self.update_expense_gui)
        self.cancel_edit_button.config(state=tk.NORMAL)


    def update_expense_gui(self):
        """Handles updating an existing expense from the GUI."""
        if self.selected_expense_id is None:
            messagebox.showerror("Error", "No expense selected for update.")
            return

        date = self.date_entry.get_date().strftime("%Y-%m-%d")
        category = self.category_entry.get().strip()
        amount_str = self.amount_entry.get().strip()
        description = self.description_entry.get().strip()

        if not date or not category or not amount_str:
            messagebox.showwarning("Input Error", "Date, Category, and Amount are required fields.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                messagebox.showwarning("Input Error", "Amount must be a positive number.")
                return
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid amount. Please enter a valid number.")
            return

        if messagebox.askyesno("Confirm Update", f"Are you sure you want to update expense ID: {self.selected_expense_id}?"):
            if self.db.update_expense(self.selected_expense_id, date, category, amount, description):
                messagebox.showinfo("Success", "Expense updated successfully!")
                self.clear_entries() # Clear fields and reset button
                self.view_expenses() # Refresh the list
                self.update_summary_and_budget_display()
            else:
                messagebox.showerror("Error", "Failed to update expense.")
        else:
            self.cancel_edit() # If user cancels, revert to add mode


    def cancel_edit(self):
        """Cancels the edit operation and reverts to add expense mode."""
        self.clear_entries()
        messagebox.showinfo("Edit Canceled", "Edit operation canceled. Ready to add new expense.")


    def view_expenses(self):
        """Populates the Treeview with expenses from the database."""
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


    def delete_expense_gui(self):
        """Handles deleting the selected expense from the GUI."""
        selected_item = self.expense_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select an expense to delete.")
            return

        # Get the values of the selected item
        item_values = self.expense_tree.item(selected_item, 'values')
        expense_id = item_values[0] # The ID is the first column

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete expense ID: {expense_id}?\nThis action cannot be undone."):
            if self.db.delete_expense(expense_id):
                messagebox.showinfo("Success", "Expense deleted successfully!")
                self.view_expenses() # Refresh the list
                self.update_summary_and_budget_display()
            else:
                messagebox.showerror("Error", "Failed to delete expense.")


    def update_summary_and_budget_display(self):
        """Updates the category summary and budget information."""
        expenses = self.db.fetch_expenses()
        if not expenses:
            self.category_summary_text.config(state=tk.NORMAL)
            self.category_summary_text.delete(1.0, tk.END)
            self.category_summary_text.insert(tk.END, "No expenses to summarize.")
            self.category_summary_text.config(state=tk.DISABLED)
            self.budget_amount_label.config(text="₹0.00")
            self.spent_amount_label.config(text="₹0.00")
            self.remaining_budget_label.config(text="₹0.00", foreground="green")
            return

        # --- Category Summary ---
        category_totals = collections.defaultdict(float)
        for exp in expenses:
            category_totals[exp[2].capitalize()] += exp[3] # exp[2] is category, exp[3] is amount

        summary_text_content = ""
        for category, total in sorted(category_totals.items()):
            summary_text_content += f"{category.ljust(15)}: ₹{total:,.2f}\n"

        self.category_summary_text.config(state=tk.NORMAL)
        self.category_summary_text.delete(1.0, tk.END)
        self.category_summary_text.insert(tk.END, summary_text_content)
        self.category_summary_text.config(state=tk.DISABLED)

        # --- Monthly Budget ---
        current_month_year = datetime.now().strftime("%Y-%m")
        total_spent_this_month = 0.0
        for exp in expenses:
            exp_date_month_year = datetime.strptime(exp[1], "%Y-%m-%d").strftime("%Y-%m")
            if exp_date_month_year == current_month_year:
                total_spent_this_month += exp[3]

        monthly_budget = self.db.get_monthly_budget(current_month_year)
        remaining_budget = monthly_budget - total_spent_this_month

        self.budget_amount_label.config(text=f"₹{monthly_budget:,.2f}")
        self.spent_amount_label.config(text=f"₹{total_spent_this_month:,.2f}")

        if remaining_budget >= 0:
            self.remaining_budget_label.config(text=f"₹{remaining_budget:,.2f}", foreground="green")
        else:
            self.remaining_budget_label.config(text=f"₹{remaining_budget:,.2f} (Over Budget)", foreground="red")

    def set_budget_gui(self):
        """Handles setting the monthly budget from the GUI."""
        budget_amount_str = self.set_budget_entry.get().strip()
        if not budget_amount_str:
            messagebox.showwarning("Input Error", "Please enter a budget amount.")
            return

        try:
            budget_amount = float(budget_amount_str)
            if budget_amount < 0:
                messagebox.showwarning("Input Error", "Budget amount cannot be negative.")
                return
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid budget amount. Please enter a number.")
            return

        current_month_year = datetime.now().strftime("%Y-%m")
        if self.db.set_monthly_budget(current_month_year, budget_amount):
            messagebox.showinfo("Success", f"Monthly budget for {current_month_year} set to ₹{budget_amount:,.2f} successfully!")
            self.set_budget_entry.delete(0, tk.END)
            self.update_summary_and_budget_display()
        else:
            messagebox.showerror("Error", "Failed to set budget.")


    def _clear_chart_canvas(self):
        """Clears the existing matplotlib canvas from the reports tab."""
        if self.canvas_widget:
            self.canvas_widget.destroy()
            self.canvas_widget = None

    def generate_pie_chart(self):
        """Generates and displays a pie chart of expenses by category."""
        self._clear_chart_canvas()

        expenses = self.db.fetch_expenses()
        if not expenses:
            messagebox.showinfo("No Data", "No expenses recorded to generate charts.")
            return

        category_totals = collections.defaultdict(float)
        for exp in expenses:
            category_totals[exp[2].capitalize()] += exp[3]

        if not category_totals:
            messagebox.showinfo("No Data", "No categorized expenses to generate a pie chart.")
            return

        labels = list(category_totals.keys())
        sizes = list(category_totals.values())

        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, wedgeprops={'edgecolor': 'black'})
        ax.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
        ax.set_title("Expense Distribution by Category")

        # Embed the plot in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.reports_tab)
        self.canvas_widget = canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        canvas.draw()

    def generate_bar_chart(self):
        """Generates and displays a bar chart of monthly spending."""
        self._clear_chart_canvas()

        expenses = self.db.fetch_expenses()
        if not expenses:
            messagebox.showinfo("No Data", "No expenses recorded to generate charts.")
            return

        monthly_totals = collections.defaultdict(float)
        for exp in expenses:
            month_year = datetime.strptime(exp[1], "%Y-%m-%d").strftime("%Y-%m")
            monthly_totals[month_year] += exp[3]

        if not monthly_totals:
            messagebox.showinfo("No Data", "No monthly expenses to generate a bar chart.")
            return

        # Sort months chronologically
        sorted_months = sorted(monthly_totals.keys())
        amounts = [monthly_totals[month] for month in sorted_months]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(sorted_months, amounts, color='skyblue')
        ax.set_xlabel("Month-Year")
        ax.set_ylabel("Total Amount (₹)")
        ax.set_title("Monthly Spending Overview")
        ax.tick_params(axis='x', rotation=45) # Rotate labels for readability
        plt.tight_layout() # Adjust layout to prevent labels overlapping

        # Embed the plot in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.reports_tab)
        self.canvas_widget = canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        canvas.draw()


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
