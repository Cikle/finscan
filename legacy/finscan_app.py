"""
FinScan Desktop Application
A GUI for scraping and displaying stock data
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
from datetime import datetime
import webbrowser
import glob

class FinScanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FinScan - Stock Data Analyzer")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        # Set icon (optional)
        # self.root.iconbitmap("icon.ico")  # Add an icon file if you have one
        
        # Style
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("Header.TLabel", font=("Arial", 14, "bold"))
        
        # Create the main container
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        header = ttk.Label(
            self.main_frame, 
            text="FinScan Stock Data Analyzer", 
            style="Header.TLabel"
        )
        header.pack(pady=(0, 20))
        
        # Create search frame
        search_frame = ttk.Frame(self.main_frame)
        search_frame.pack(fill=tk.X)
        
        # Symbol entry
        ttk.Label(search_frame, text="Stock Symbol:").pack(side=tk.LEFT)
        self.symbol_entry = ttk.Entry(search_frame, width=10, font=("Arial", 12))
        self.symbol_entry.pack(side=tk.LEFT, padx=5)
        
        # Search button
        self.search_button = ttk.Button(
            search_frame, 
            text="Generate Data", 
            command=self.generate_stock_data
        )
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        # Quick examples
        example_frame = ttk.Frame(self.main_frame)
        example_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(example_frame, text="Quick Examples:").pack(side=tk.LEFT)
        
        examples = ["AAPL", "MSFT", "GOOG", "TSLA", "AMZN", "THS"]
        for symbol in examples:
            ttk.Button(
                example_frame, 
                text=symbol, 
                width=5,
                command=lambda s=symbol: self.load_example(s)
            ).pack(side=tk.LEFT, padx=2)
        
        # Progress area
        progress_frame = ttk.LabelFrame(self.main_frame, text="Status")
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_label = ttk.Label(
            progress_frame, 
            text="Ready to generate stock data..."
        )
        self.progress_label.pack(pady=5, padx=5, anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            orient=tk.HORIZONTAL, 
            length=100, 
            mode='indeterminate'
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # Console output
        console_frame = ttk.LabelFrame(self.main_frame, text="Console Output")
        console_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.console = scrolledtext.ScrolledText(
            console_frame, 
            wrap=tk.WORD, 
            font=("Consolas", 9),
            height=10
        )
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console.config(state=tk.DISABLED)
        
        # Generated files area
        files_frame = ttk.LabelFrame(self.main_frame, text="Generated Files")
        files_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        files_toolbar = ttk.Frame(files_frame)
        files_toolbar.pack(fill=tk.X)
        
        ttk.Button(
            files_toolbar,
            text="Refresh",
            command=self.refresh_files
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Create a treeview for files
        self.files_tree = ttk.Treeview(
            files_frame,
            columns=("symbol", "date", "filename"),
            show="headings"
        )
        self.files_tree.heading("symbol", text="Symbol")
        self.files_tree.heading("date", text="Date")
        self.files_tree.heading("filename", text="Filename")
        
        self.files_tree.column("symbol", width=80)
        self.files_tree.column("date", width=150)
        self.files_tree.column("filename", width=400)
        
        self.files_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.files_tree.bind("<Double-1>", self.open_selected_file)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize
        self.refresh_files()
    
    def write_to_console(self, text):
        """Write text to the console widget"""
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, text + "\n")
        self.console.see(tk.END)  # Scroll to the end
        self.console.config(state=tk.DISABLED)
    
    def generate_stock_data(self):
        """Generate stock data for the entered symbol"""
        symbol = self.symbol_entry.get().strip().upper()
        
        if not symbol:
            messagebox.showwarning("Warning", "Please enter a stock symbol")
            return
        
        self.search_button.config(state=tk.DISABLED)
        self.progress_label.config(text=f"Generating data for {symbol}...")
        self.progress_bar.start(10)
        self.status_var.set(f"Running stock data scraper for {symbol}...")
        self.write_to_console(f"[{datetime.now().strftime('%H:%M:%S')}] Starting data collection for {symbol}...")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_data_{timestamp}.html"
        
        # Run the scraper in a separate thread
        thread = threading.Thread(
            target=self.run_scraper_thread,
            args=(symbol, filename)
        )
        thread.daemon = True
        thread.start()
    
    def run_scraper_thread(self, symbol, filename):
        """Run the stock data scraper in a separate thread"""
        try:
            # Build the command
            cmd = [sys.executable, "stock_data_scraper.py", symbol, "--html", "--output", filename]
            
            # Execute the command and capture output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Process output in real-time
            while True:
                output_line = process.stdout.readline()
                if output_line == '' and process.poll() is not None:
                    break
                if output_line:
                    self.root.after(0, self.write_to_console, output_line.strip())
            
            # Get any remaining output and the return code
            stdout, stderr = process.communicate()
            return_code = process.returncode
            
            if stderr:
                self.root.after(0, self.write_to_console, stderr)
            
            # Update UI based on result
            if return_code == 0:
                # Success
                self.root.after(0, self.scraper_completed, True, symbol, filename)
            else:
                # Error
                self.root.after(0, self.scraper_completed, False, symbol, None)
                
        except Exception as e:
            self.root.after(0, self.write_to_console, f"Error: {str(e)}")
            self.root.after(0, self.scraper_completed, False, symbol, None)
    
    def scraper_completed(self, success, symbol, filename):
        """Handle completion of scraper process"""
        self.progress_bar.stop()
        self.search_button.config(state=tk.NORMAL)
        
        if success:
            self.progress_label.config(text=f"Data generated successfully for {symbol}!")
            self.status_var.set(f"Data generated: {filename}")
            self.write_to_console(f"[{datetime.now().strftime('%H:%M:%S')}] Data generation complete!")
            
            # Ask if user wants to open the file
            if messagebox.askyesno("Success", f"Data for {symbol} generated successfully!\n\nDo you want to open it now?"):
                self.open_file(filename)
            
            # Refresh the file list
            self.refresh_files()
        else:
            self.progress_label.config(text=f"Error generating data for {symbol}")
            self.status_var.set("Error generating data")
    
    def load_example(self, symbol):
        """Load an example stock symbol"""
        self.symbol_entry.delete(0, tk.END)
        self.symbol_entry.insert(0, symbol)
        self.generate_stock_data()
    
    def refresh_files(self):
        """Refresh the list of generated files"""
        # Clear existing items
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        
        # Find all HTML files that match our pattern
        files = []
        for filename in glob.glob("*_data_*.html"):
            try:
                # Try to extract symbol from filename
                parts = filename.split('_data_')
                if len(parts) == 2:
                    symbol = parts[0]
                    # Get file modification time
                    mod_time = os.path.getmtime(filename)
                    date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                    
                    files.append({
                        'symbol': symbol,
                        'date': date_str,
                        'filename': filename,
                        'timestamp': mod_time
                    })
            except:
                # Skip files that don't match our pattern
                continue
        
        # Sort by timestamp (newest first)
        files.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Add to treeview
        for file in files:
            self.files_tree.insert(
                "", 
                "end", 
                values=(file['symbol'], file['date'], file['filename'])
            )
    
    def open_selected_file(self, event):
        """Open the selected file from the treeview"""
        selection = self.files_tree.selection()
        if selection:
            item = self.files_tree.item(selection[0])
            filename = item['values'][2]
            self.open_file(filename)
    
    def open_file(self, filename):
        """Open a file in the default browser"""
        if os.path.exists(filename):
            # Convert to absolute file path with file:// prefix
            file_path = os.path.abspath(filename)
            url = f"file://{file_path}"
            webbrowser.open(url)
            self.status_var.set(f"Opened {filename}")
        else:
            messagebox.showerror("Error", f"File not found: {filename}")
            self.status_var.set(f"File not found: {filename}")

def main():
    root = tk.Tk()
    app = FinScanApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()