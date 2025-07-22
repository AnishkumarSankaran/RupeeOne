import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
from datetime import datetime

# --- Database Management Class ---
class DatabaseManager:
    """Handles all interactions with the SQLite database."""
    def __init__(self, db_name="expenses.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_table()

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            print(f"Connected to database: {self.db_name}")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to connect to database: {e}")
            self.conn = None # Ensure conn is None if connection fails
            self.cursor = None

    def _create_table(self):
        """Creates the 'expenses' table if it doesn't already exist."""
        if self.cursor:
            try:
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS expenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        category TEXT NOT NULL,
                        amount REAL NOT NULL,
                        description TEXT
                    )
                ''')
                self.conn.commit()
                print("Table 'expenses' checked/created successfully.")
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to create table: {e}")
        else:
            print("No database connection to create table.")

    def add_expense(self, date, category, amount, description):
        """Inserts a new expense record into the database."""
        if not self.cursor:
            messagebox.showerror("Database Error", "No active database connection.")
            return False
        try:
            self.cursor.execute('''
                INSERT INTO expenses (date, category, amount, description)
                VALUES (?, ?, ?, ?)
            ''', (date, category, amount, description))
            self.conn.commit()
            print(f"Expense added: {date}, {category}, {amount}, {description}")
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to add expense: {e}")
            return False

    def fetch_expenses(self):
        """Fetches all expense records from the database."""
        if not self.cursor:
            messagebox.showerror("Database Error", "No active database connection.")
            return []
        try:
            self.cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch expenses: {e}")
            return []

    def delete_expense(self, expense_id):
        """Deletes an expense record by its ID."""
        if not self.cursor:
            messagebox.showerror("Database Error", "No active database connection.")
            return False
        try:
            self.cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            self.conn.commit()
            print(f"Expense with ID {expense_id} deleted.")
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete expense: {e}")
            return False

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
        master.geometry("800x600")
        master.resizable(False, False) # Prevent resizing for simpler layout

        self.db = DatabaseManager()

        # Ensure the database connection is active before proceeding
        if not self.db.conn:
            messagebox.showerror("Initialization Error", "Could not connect to database. Exiting application.")
            master.destroy()
            return

        self.create_widgets()
        self.view_expenses() # Load expenses on startup

    def create_widgets(self):
        """Creates and arranges all GUI elements."""
        # --- Input Frame ---
        input_frame = tk.LabelFrame(self.master, text="Add New Expense", padx=10, pady=10)
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Date Input
        tk.Label(input_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", pady=2)
        self.date_entry = tk.Entry(input_frame, width=30)
        self.date_entry.grid(row=0, column=1, pady=2)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d")) # Pre-fill with current date

        # Category Input
        tk.Label(input_frame, text="Category:").grid(row=1, column=0, sticky="w", pady=2)
        self.category_entry = tk.Entry(input_frame, width=30)
        self.category_entry.grid(row=1, column=1, pady=2)

        # Amount Input
        tk.Label(input_frame, text="Amount (₹):").grid(row=2, column=0, sticky="w", pady=2)
        self.amount_entry = tk.Entry(input_frame, width=30)
        self.amount_entry.grid(row=2, column=1, pady=2)

        # Description Input
        tk.Label(input_frame, text="Description:").grid(row=3, column=0, sticky="w", pady=2)
        self.description_entry = tk.Entry(input_frame, width=30)
        self.description_entry.grid(row=3, column=1, pady=2)

        # Add Expense Button
        add_button = tk.Button(input_frame, text="Add Expense", command=self.add_expense_gui, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), relief="raised", bd=3)
        add_button.grid(row=4, column=0, columnspan=2, pady=10, ipadx=20)

        # --- Expense List Frame ---
        list_frame = tk.LabelFrame(self.master, text="All Expenses", padx=10, pady=10)
        list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Configure grid for list_frame to allow Treeview to expand
        self.master.grid_rowconfigure(1, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
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
        self.expense_tree.column("Description", width=250, anchor=tk.W, stretch=tk.YES) # Allow description to expand

        self.expense_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for Treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.expense_tree.yview)
        self.expense_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Delete Expense Button
        delete_button = tk.Button(list_frame, text="Delete Selected Expense", command=self.delete_expense_gui, bg="#f44336", fg="white", font=("Arial", 10, "bold"), relief="raised", bd=3)
        delete_button.grid(row=1, column=0, columnspan=2, pady=10, ipadx=20)

        # Bind selection event to Treeview (optional: for future editing/displaying selected item)
        # self.expense_tree.bind("<<TreeviewSelect>>", self.on_select_item)

    def clear_entries(self):
        """Clears the input fields."""
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.category_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)

    def add_expense_gui(self):
        """Handles adding an expense from the GUI."""
        date = self.date_entry.get()
        category = self.category_entry.get().strip()
        amount_str = self.amount_entry.get().strip()
        description = self.description_entry.get().strip()

        if not date or not category or not amount_str:
            messagebox.showwarning("Input Error", "Date, Category, and Amount are required fields.")
            return

        try:
            # Validate date format
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Input Error", "Invalid date format. Please use YYYY-MM-DD.")
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

    def view_expenses(self):
        """Populates the Treeview with expenses from the database."""
        # Clear existing items in the treeview
        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        expenses = self.db.fetch_expenses()
        if not expenses:
            self.expense_tree.insert("", tk.END, values=("", "", "No expenses yet", "", ""), tags=('center_text',))
            self.expense_tree.tag_configure('center_text', anchor='center')
            return

        for exp in expenses:
            # Format amount for display
            formatted_amount = f"₹{exp[3]:,.2f}"
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

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete expense ID: {expense_id}?"):
            if self.db.delete_expense(expense_id):
                messagebox.showinfo("Success", "Expense deleted successfully!")
                self.view_expenses() # Refresh the list
            else:
                messagebox.showerror("Error", "Failed to delete expense.")

    # Optional: Function to handle item selection in Treeview
    # def on_select_item(self, event):
    #     selected_item = self.expense_tree.selection()
    #     if selected_item:
    #         item_values = self.expense_tree.item(selected_item, 'values')
    #         print(f"Selected: ID={item_values[0]}, Date={item_values[1]}, Category={item_values[2]}, Amount={item_values[3]}, Description={item_values[4]}")

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
