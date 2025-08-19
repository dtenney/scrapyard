import tkinter as tk
from tkinter import ttk, messagebox
from ..services.transaction_service import TransactionService
from ..services.database import Database

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Scrap Yard POS System")
        self.root.geometry("1200x800")
        
        self.transaction_service = TransactionService()
        self.current_transaction_id = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # Main menu
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Transaction", command=self.new_transaction)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Transaction info
        info_frame = ttk.LabelFrame(main_frame, text="Transaction Info", padding="10")
        info_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(info_frame, text="Customer ID:").grid(row=0, column=0, sticky=tk.W)
        self.customer_id_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.customer_id_var, width=20).grid(row=0, column=1, padx=(5, 0))
        
        # Weight input
        weight_frame = ttk.LabelFrame(main_frame, text="Weight Input", padding="10")
        weight_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 5))
        
        ttk.Label(weight_frame, text="Metal Type:").grid(row=0, column=0, sticky=tk.W)
        self.metal_var = tk.StringVar()
        metal_combo = ttk.Combobox(weight_frame, textvariable=self.metal_var, width=15)
        metal_combo['values'] = ('Copper', 'Aluminum', 'Steel', 'Brass', 'Iron')
        metal_combo.grid(row=0, column=1, padx=(5, 0))
        
        ttk.Label(weight_frame, text="Weight (lbs):").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.weight_var = tk.StringVar()
        ttk.Entry(weight_frame, textvariable=self.weight_var, width=15).grid(row=1, column=1, padx=(5, 0), pady=(5, 0))
        
        ttk.Label(weight_frame, text="Price/lb:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.price_var = tk.StringVar()
        ttk.Entry(weight_frame, textvariable=self.price_var, width=15).grid(row=2, column=1, padx=(5, 0), pady=(5, 0))
        
        ttk.Button(weight_frame, text="Add Item", command=self.add_item).grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        # Transaction items
        items_frame = ttk.LabelFrame(main_frame, text="Transaction Items", padding="10")
        items_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        self.items_tree = ttk.Treeview(items_frame, columns=('Metal', 'Weight', 'Price', 'Total'), show='headings', height=10)
        self.items_tree.heading('Metal', text='Metal Type')
        self.items_tree.heading('Weight', text='Weight (lbs)')
        self.items_tree.heading('Price', text='Price/lb')
        self.items_tree.heading('Total', text='Total ($)')
        
        self.items_tree.column('Metal', width=100)
        self.items_tree.column('Weight', width=80)
        self.items_tree.column('Price', width=80)
        self.items_tree.column('Total', width=80)
        
        self.items_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Total and complete
        total_frame = ttk.Frame(main_frame)
        total_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.total_label = ttk.Label(total_frame, text="Total: $0.00", font=('Arial', 14, 'bold'))
        self.total_label.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Button(total_frame, text="Complete Transaction", command=self.complete_transaction).grid(row=0, column=1, sticky=tk.E)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        items_frame.columnconfigure(0, weight=1)
        items_frame.rowconfigure(0, weight=1)
        total_frame.columnconfigure(0, weight=1)
    
    def new_transaction(self):
        if not self.customer_id_var.get():
            messagebox.showerror("Error", "Please enter a customer ID")
            return
        
        try:
            customer_id = int(self.customer_id_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid customer ID")
            return
        
        self.current_transaction_id = self.transaction_service.create_transaction(customer_id)
        
        # Clear items
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        self.update_total()
        messagebox.showinfo("Success", f"New transaction created: {self.current_transaction_id}")
    
    def add_item(self):
        if not self.current_transaction_id:
            messagebox.showerror("Error", "Please create a new transaction first")
            return
        
        try:
            metal_type = self.metal_var.get()
            if not metal_type:
                messagebox.showerror("Error", "Please select a metal type")
                return
                
            weight = float(self.weight_var.get())
            price = float(self.price_var.get())
            total = weight * price
            
            # Add to database (using metal_id = 1 for demo)
            self.transaction_service.add_item_to_transaction(
                self.current_transaction_id, 1, weight, price
            )
            
            # Add to tree view
            self.items_tree.insert('', 'end', values=(metal_type, f"{weight:.2f}", f"${price:.2f}", f"${total:.2f}"))
            
            # Clear inputs
            self.weight_var.set("")
            self.price_var.set("")
            
            self.update_total()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for weight and price")
    
    def update_total(self):
        total = 0
        for item in self.items_tree.get_children():
            values = self.items_tree.item(item)['values']
            try:
                total += float(values[3].replace('$', ''))
            except (ValueError, IndexError):
                messagebox.showerror("Error", "Invalid total value in transaction")
                return
        
        self.total_label.config(text=f"Total: ${total:.2f}")
    
    def complete_transaction(self):
        if not self.current_transaction_id:
            messagebox.showerror("Error", "No active transaction")
            return
        
        total_amount = self.transaction_service.complete_transaction(
            self.current_transaction_id, "CASH"
        )
        
        messagebox.showinfo("Success", f"Transaction completed. Total: ${total_amount:.2f}")
        self.current_transaction_id = None
    
    def run(self):
        self.root.mainloop()