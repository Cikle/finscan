"""
FinScan Desktop Application - With Temporary File Management
A GUI for scraping and displaying stock data that stores files in a temp directory
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
import shutil

class FinScanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FinScan - Stock Data Analyzer")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        # Set up temp directory path
        self.temp_dir = os.path.join(os.getcwd(), "temp_data")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        # Register cleanup function to run when app is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Set style
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("Header.TLabel", font=("Arial", 14, "bold"))
        
        # Main container
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
        
        ttk.Label(search_frame, text="Stock Symbol:").pack(side=tk.LEFT)
        self.symbol_entry = ttk.Entry(search_frame, width=10, font=("Arial", 12))
        self.symbol_entry.pack(side=tk.LEFT, padx=5)
        
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
        
        # Action buttons
        action_frame = ttk.Frame(progress_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.view_button = ttk.Button(
            action_frame, 
            text="View Selected Report", 
            command=self.view_selected_report,
            state=tk.DISABLED
        )
        self.view_button.pack(side=tk.LEFT, padx=5)
        
        self.keep_button = ttk.Button(
            action_frame, 
            text="Save Report to Keep", 
            command=self.save_selected_report,
            state=tk.DISABLED
        )
        self.keep_button.pack(side=tk.LEFT, padx=5)
        
        # Add a preview frame for statistics
        self.preview_frame = ttk.LabelFrame(self.main_frame, text="Selected Stock Preview")
        self.preview_frame.pack(fill=tk.X, pady=10)
        
        # Create a grid for stock statistics
        preview_grid = ttk.Frame(self.preview_frame)
        preview_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Configure a grid with 3 columns
        for i in range(3):
            preview_grid.columnconfigure(i, weight=1)
        
        # Key statistics labels and values
        stats = [
            ("Symbol", "symbol_val"),
            ("Price", "price_val"), 
            ("Change", "change_val"),
            ("P/E", "pe_val"), 
            ("Market Cap", "mcap_val"),
            ("Volume", "vol_val")
        ]
        
        # Create labels and values in grid
        self.stat_values = {}
        for idx, (label, key) in enumerate(stats):
            row = idx // 3
            col = idx % 3
            
            # Container frame for each stat
            stat_frame = ttk.Frame(preview_grid)
            stat_frame.grid(row=row, column=col, padx=10, pady=5, sticky="ew")
            
            # Label
            ttk.Label(
                stat_frame, 
                text=label + ":", 
                font=("Arial", 9)
            ).pack(side=tk.LEFT)
            
            # Value (will be updated when a stock is selected)
            value_var = tk.StringVar()
            value_var.set("--")
            self.stat_values[key] = value_var
            
            value_label = ttk.Label(
                stat_frame, 
                textvariable=value_var, 
                font=("Arial", 9, "bold")
            )
            value_label.pack(side=tk.LEFT, padx=5)
            
            # Store label reference for color updates
            if key == "change_val":
                self.change_label = value_label
        
        # Add a simple visual indicator for the stock's health
        visual_frame = ttk.Frame(self.preview_frame)
        visual_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Health indicator - we'll use a simple color bar
        ttk.Label(visual_frame, text="Stock Health:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.health_frame = ttk.Frame(visual_frame)
        self.health_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.health_indicator = tk.Canvas(self.health_frame, height=20, bg="#eeeeee", highlightthickness=1, highlightbackground="#cccccc")
        self.health_indicator.pack(fill=tk.X, expand=True)
        
        self.health_text = tk.StringVar()
        self.health_text.set("No data")
        
        ttk.Label(visual_frame, textvariable=self.health_text, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=10)
        
        # Initialize the preview as empty
        self.clear_stock_preview()
        
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
        files_frame = ttk.LabelFrame(self.main_frame, text="Generated Reports")
        files_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        files_toolbar = ttk.Frame(files_frame)
        files_toolbar.pack(fill=tk.X)
        
        ttk.Button(
            files_toolbar,
            text="Refresh",
            command=self.refresh_files
        ).pack(side=tk.LEFT, padx=5, pady=5)

        ttk.Label(
            files_toolbar,
            text="* Reports stored in temp directory will be deleted when the app closes"
        ).pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Create a treeview for files
        self.files_tree = ttk.Treeview(
            files_frame,
            columns=("symbol", "date", "filename", "location"),
            show="headings"
        )
        self.files_tree.heading("symbol", text="Symbol")
        self.files_tree.heading("date", text="Date")
        self.files_tree.heading("filename", text="Filename")
        self.files_tree.heading("location", text="Location")
        
        self.files_tree.column("symbol", width=80)
        self.files_tree.column("date", width=150)
        self.files_tree.column("filename", width=300)
        self.files_tree.column("location", width=100)
        
        self.files_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.files_tree.bind("<Double-1>", self.open_selected_file)
        self.files_tree.bind("<<TreeviewSelect>>", self.on_file_selected)
        
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
        
        # Prepare the environment variables to avoid emoji encoding issues
        env = os.environ.copy()
        # Force ASCII output to avoid Unicode issues on Windows
        env["PYTHONIOENCODING"] = "ascii:replace"
        
        # Run the scraper in a separate thread
        thread = threading.Thread(
            target=self.run_scraper_thread,
            args=(symbol, filename, env)
        )
        thread.daemon = True
        thread.start()
    
    def run_scraper_thread(self, symbol, filename, env):
        """Run the stock data scraper in a separate thread"""
        try:
            # Ensure temp directory exists
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)
            
            # Set the output path to be in the temp directory
            output_path = os.path.join(self.temp_dir, filename)
            
            # Build the command
            cmd = [sys.executable, "stock_data_scraper.py", symbol, "--html", "--output", output_path]
            
            # Execute the command and capture output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=env  # Use the modified environment
            )
            
            # Process output in real-time
            while True:
                output_line = process.stdout.readline()
                if output_line == '' and process.poll() is not None:
                    break
                if output_line:
                    # Replace any problematic characters
                    safe_line = output_line.encode('ascii', 'replace').decode('ascii')
                    self.root.after(0, self.write_to_console, safe_line.strip())
            
            # Get any remaining output and the return code
            stdout, stderr = process.communicate()
            return_code = process.returncode
            
            if stderr:
                safe_stderr = stderr.encode('ascii', 'replace').decode('ascii')
                self.root.after(0, self.write_to_console, safe_stderr)
            
            # Update UI based on result
            if return_code == 0:
                # Success - pass just the filename (not the full path) for display purposes
                self.root.after(0, self.scraper_completed, True, symbol, filename)
            else:
                # Error
                self.root.after(0, self.scraper_completed, False, symbol, None)
                
        except Exception as e:
            safe_error = str(e).encode('ascii', 'replace').decode('ascii')
            self.root.after(0, self.write_to_console, f"Error: {safe_error}")
            self.root.after(0, self.scraper_completed, False, symbol, None)
    
    def scraper_completed(self, success, symbol, filename):
        """Handle completion of scraper process"""
        self.progress_bar.stop()
        self.search_button.config(state=tk.NORMAL)
        
        if success:
            self.progress_label.config(text=f"Data generated successfully for {symbol}!")
            self.status_var.set(f"Data ready: {filename}")
            self.write_to_console(f"[{datetime.now().strftime('%H:%M:%S')}] Data generation complete!")
            
            # Let the user know they can view it from the list
            self.write_to_console(f"Data saved to temp directory. Select the file in the list and click 'View Selected Report' to open.")
            
            # Refresh the file list and select the new file
            self.refresh_files(select_file=filename)
        else:
            self.progress_label.config(text=f"Error generating data for {symbol}")
            self.status_var.set("Error generating data")
    
    def load_example(self, symbol):
        """Load an example stock symbol"""
        self.symbol_entry.delete(0, tk.END)
        self.symbol_entry.insert(0, symbol)
        self.generate_stock_data()
    
    def refresh_files(self, select_file=None):
        """
        Refresh the list of generated files
        
        Args:
            select_file: If provided, selects this file in the list after refreshing
        """
        # Clear existing items
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        
        # Create a data directory if it doesn't exist
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        # Find all HTML files that match our pattern
        files = []
        
        # Look in current directory for saved files
        for filename in glob.glob("*_data_*.html"):
            try:
                filepath = os.path.abspath(filename)
                parts = filename.split('_data_')
                if len(parts) == 2:
                    symbol = parts[0]
                    mod_time = os.path.getmtime(filepath)
                    date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                    
                    files.append({
                        'symbol': symbol,
                        'date': date_str,
                        'filename': filename,
                        'filepath': filepath,
                        'timestamp': mod_time,
                        'location': 'Saved'
                    })
            except Exception:
                pass
        
        # Look in temp directory for temporary files
        for filename in glob.glob(os.path.join(self.temp_dir, "*_data_*.html")):
            try:
                basename = os.path.basename(filename)
                parts = basename.split('_data_')
                if len(parts) == 2:
                    symbol = parts[0]
                    mod_time = os.path.getmtime(filename)
                    date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                    
                    files.append({
                        'symbol': symbol,
                        'date': date_str,
                        'filename': basename,
                        'filepath': filename,
                        'timestamp': mod_time,
                        'location': 'Temporary'
                    })
            except Exception:
                pass
        
        # Sort by timestamp (newest first)
        files.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Keep track of the item ID to select
        item_to_select = None
        
        # Add to treeview
        for file in files:
            item_id = self.files_tree.insert(
                "", 
                "end", 
                values=(file['symbol'], file['date'], file['filename'], file['location'])
            )
            
            # If this is the file to select, keep track of its ID
            if select_file and file['filename'] == select_file:
                item_to_select = item_id
        
        # Select the specified item if found
        if item_to_select:
            self.files_tree.selection_set(item_to_select)
            self.files_tree.see(item_to_select)  # Ensure it's visible
            self.on_file_selected(None)  # Update button states
    
    def on_file_selected(self, event):
        """Called when a file is selected in the treeview"""
        selection = self.files_tree.selection()
        if selection:
            self.view_button.config(state=tk.NORMAL)
            self.keep_button.config(state=tk.NORMAL)
            
            # Check if the selected file is in the temp directory
            item = self.files_tree.item(selection[0])
            location = item['values'][3]  # The 'location' column
            
            # Only enable the "Save" button if the file is temporary
            if location == 'Temporary':
                self.keep_button.config(state=tk.NORMAL)
            else:
                self.keep_button.config(state=tk.DISABLED)
                
            # Update the stock preview with data from the selected file
            self.update_stock_preview(item['values'])
        else:
            self.view_button.config(state=tk.DISABLED)
            self.keep_button.config(state=tk.DISABLED)
            self.clear_stock_preview()
            
    def clear_stock_preview(self):
        """Clear the stock preview section"""
        for key, var in self.stat_values.items():
            var.set("--")
        
        # Reset change label color
        if hasattr(self, 'change_label'):
            self.change_label.configure(foreground="")
        
        # Reset health indicator
        self.health_indicator.delete("all")
        self.health_text.set("No data")
        
    def update_stock_preview(self, values):
        """Update the stock preview with data from the selected file"""
        symbol = values[0]  # Symbol column
        filename = values[2]  # Filename column
        location = values[3]  # Location column
        
        # Update the symbol
        self.stat_values["symbol_val"].set(symbol)
        
        # Determine the file path
        if location == 'Temporary':
            file_path = os.path.join(self.temp_dir, filename)
        else:
            file_path = os.path.join(os.getcwd(), filename)
        
        # Try to extract data from the HTML file
        if os.path.exists(file_path):
            try:
                # Read the HTML file and extract basic data
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract price
                price_match = self.extract_value(content, ["Price", "currentPrice"], r'(\d+\.\d+)')
                if price_match:
                    self.stat_values["price_val"].set(price_match)
                
                # Extract change
                change_match = self.extract_value(content, ["Change"], r'([+-]?\d+\.\d+%)')
                if change_match:
                    self.stat_values["change_val"].set(change_match)
                    
                    # Set color based on value
                    if change_match.startswith("+"):
                        self.change_label.configure(foreground="green")
                    elif change_match.startswith("-"):
                        self.change_label.configure(foreground="red")
                    else:
                        self.change_label.configure(foreground="")
                
                # Extract P/E
                pe_match = self.extract_value(content, ["P/E", "trailingPE"], r'(\d+\.\d+)')
                if pe_match:
                    self.stat_values["pe_val"].set(pe_match)
                
                # Extract Market Cap
                mcap_match = self.extract_value(content, ["Market Cap", "marketCap"], r'([\d\.]+[BMK]?)')
                if mcap_match:
                    self.stat_values["mcap_val"].set(mcap_match)
                
                # Extract Volume
                vol_match = self.extract_value(content, ["Volume", "volume"], r'([\d,\.]+[KMB]?)')
                if vol_match:
                    self.stat_values["vol_val"].set(vol_match)
                
                # Update the health indicator
                self.update_health_indicator(content)
                
            except Exception as e:
                print(f"Error extracting data from HTML: {e}")
    
    def update_health_indicator(self, content):
        """Update the health indicator based on stock metrics"""
        # Initialize score components
        pe_score = 50
        change_score = 50
        recom_score = 50
        
        # Extract P/E ratio
        pe_match = self.extract_value(content, ["P/E", "trailingPE"], r'(\d+\.\d+)')
        if pe_match:
            try:
                pe_ratio = float(pe_match)
                # Score P/E ratio (lower is better, but not negative)
                if pe_ratio <= 0:
                    pe_score = 20  # Negative P/E is concerning
                elif pe_ratio < 10:
                    pe_score = 80  # Very good P/E
                elif pe_ratio < 15:
                    pe_score = 70  # Good P/E
                elif pe_ratio < 20:
                    pe_score = 60  # Decent P/E
                elif pe_ratio < 25:
                    pe_score = 50  # Average P/E
                elif pe_ratio < 50:
                    pe_score = 40  # High P/E
                else:
                    pe_score = 30  # Very high P/E
            except ValueError:
                pass
        
        # Extract price change
        change_match = self.extract_value(content, ["Change"], r'([+-]?\d+\.\d+)%')
        if change_match:
            try:
                change_pct = float(change_match)
                # Score price change
                if change_pct > 5:
                    change_score = 90  # Very positive
                elif change_pct > 2:
                    change_score = 75  # Positive
                elif change_pct > 0:
                    change_score = 60  # Slightly positive
                elif change_pct > -2:
                    change_score = 45  # Slightly negative
                elif change_pct > -5:
                    change_score = 30  # Negative
                else:
                    change_score = 15  # Very negative
            except ValueError:
                pass
        
        # Extract analyst recommendations
        recom_match = self.extract_value(content, ["Recom"], r'(\d+\.\d+)')
        if recom_match:
            try:
                recom = float(recom_match)
                # Score recommendations (1 is Strong Buy, 5 is Strong Sell)
                if recom <= 1.5:
                    recom_score = 90  # Strong Buy
                elif recom <= 2.2:
                    recom_score = 75  # Buy
                elif recom <= 3.0:
                    recom_score = 50  # Hold
                elif recom_score <= 4.0:
                    recom_score = 30  # Sell
                else:
                    recom_score = 15  # Strong Sell
            except ValueError:
                pass
        
        # Calculate overall score
        overall_score = (pe_score + change_score + recom_score) / 3
        
        # Update the health indicator
        self.health_indicator.delete("all")
        
        # Determine color based on score
        if overall_score >= 75:
            color = "#4CAF50"  # Green
            health_text = "Strong"
        elif overall_score >= 60:
            color = "#8BC34A"  # Light Green
            health_text = "Good"
        elif overall_score >= 45:
            color = "#FFC107"  # Amber
            health_text = "Neutral"
        elif overall_score >= 30:
            color = "#FF9800"  # Orange
            health_text = "Caution"
        else:
            color = "#F44336"  # Red
            health_text = "Weak"
        
        # Draw the health bar
        width = self.health_indicator.winfo_width()
        if width < 2:  # Handle initial rendering when width isn't known yet
            width = 200
            
        bar_width = int((overall_score / 100) * width)
        self.health_indicator.create_rectangle(0, 0, bar_width, 20, fill=color, outline="")
        
        # Update the health text
        self.health_text.set(health_text)
    
    def extract_value(self, content, possible_labels, pattern):
        """Extract a value from HTML content based on possible labels and regex pattern"""
        for label in possible_labels:
            # Try to find the label in a table cell
            label_pattern = f'<td>{label}</td><td>(.*?)</td>'
            import re
            match = re.search(label_pattern, content)
            if match:
                # Extract the value with the specified pattern
                value_match = re.search(pattern, match.group(1))
                if value_match:
                    return value_match.group(1)
        return None
    
    def open_selected_file(self, event):
        """Open the selected file from the treeview"""
        selection = self.files_tree.selection()
        if selection:
            item = self.files_tree.item(selection[0])
            filename = item['values'][2]  # The 'filename' column
            location = item['values'][3]  # The 'location' column
            
            # Determine the file path based on location
            if location == 'Temporary':
                filepath = os.path.join(self.temp_dir, filename)
            else:
                filepath = filename
                
            self.open_file(filepath)
    
    def view_selected_report(self):
        """View the selected report"""
        selection = self.files_tree.selection()
        if selection:
            item = self.files_tree.item(selection[0])
            filename = item['values'][2]
            location = item['values'][3]
            
            if location == 'Temporary':
                filepath = os.path.join(self.temp_dir, filename)
            else:
                filepath = filename
                
            self.open_file(filepath)
    
    def save_selected_report(self):
        """Save the selected report from temp to permanent storage"""
        selection = self.files_tree.selection()
        if selection:
            item = self.files_tree.item(selection[0])
            filename = item['values'][2]
            location = item['values'][3]
            
            if location == 'Temporary':
                # Source path in temp directory
                source = os.path.join(self.temp_dir, filename)
                
                # Destination path in main directory
                dest = os.path.join(os.getcwd(), filename)
                
                try:
                    # Copy the file from temp to main directory
                    shutil.copy2(source, dest)
                    
                    # Refresh the file list
                    self.refresh_files(select_file=filename)
                    
                    # Update status
                    self.status_var.set(f"Report saved: {filename}")
                    self.write_to_console(f"Report {filename} saved to permanent storage.")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not save file: {str(e)}")
    
    def open_file(self, filepath):
        """Open a file in the default browser"""
        if os.path.exists(filepath):
            # Convert to absolute file path with file:// prefix
            abs_path = os.path.abspath(filepath)
            url = f"file://{abs_path}"
            webbrowser.open(url)
            self.status_var.set(f"Opened {os.path.basename(filepath)}")
        else:
            messagebox.showerror("Error", f"File not found: {filepath}")
            self.status_var.set(f"File not found: {filepath}")
    
    def on_close(self):
        """Handle application closing - clean up temp files"""
        # Ask the user if they want to keep any temporary files
        temp_files = glob.glob(os.path.join(self.temp_dir, "*_data_*.html"))
        
        if temp_files:
            resp = messagebox.askyesnocancel(
                "Closing FinScan", 
                f"There are {len(temp_files)} temporary report(s).\n\n"
                "Do you want to save them before exiting?\n"
                "• Yes: Choose which files to save\n"
                "• No: Delete all temporary files\n"
                "• Cancel: Return to application"
            )
            
            if resp is None:  # Cancel was clicked
                return
                
            elif resp is True:  # Yes was clicked - save files
                # Create a simple dialog to choose files to save
                save_window = tk.Toplevel(self.root)
                save_window.title("Save Reports")
                save_window.geometry("600x400")
                save_window.transient(self.root)
                save_window.grab_set()
                
                # Instructions
                ttk.Label(
                    save_window,
                    text="Select reports to save before exiting:",
                    font=("Arial", 10, "bold")
                ).pack(pady=10)
                
                # Create a frame for the listbox and scrollbar
                list_frame = ttk.Frame(save_window)
                list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                
                # Create a scrollbar
                scrollbar = ttk.Scrollbar(list_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Create a listbox with checkbuttons
                file_listbox = tk.Listbox(
                    list_frame,
                    selectmode=tk.MULTIPLE,
                    font=("Consolas", 9),
                    yscrollcommand=scrollbar.set
                )
                file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                # Configure the scrollbar
                scrollbar.config(command=file_listbox.yview)
                
                # Add files to the listbox
                for filepath in temp_files:
                    filename = os.path.basename(filepath)
                    file_listbox.insert(tk.END, filename)
                
                # Buttons
                btn_frame = ttk.Frame(save_window)
                btn_frame.pack(fill=tk.X, padx=10, pady=10)
                
                ttk.Button(
                    btn_frame,
                    text="Save Selected",
                    command=lambda: self.save_selected_and_exit(file_listbox, temp_files, save_window)
                ).pack(side=tk.LEFT, padx=5)
                
                ttk.Button(
                    btn_frame,
                    text="Save All",
                    command=lambda: self.save_all_and_exit(temp_files, save_window)
                ).pack(side=tk.LEFT, padx=5)
                
                ttk.Button(
                    btn_frame,
                    text="Exit Without Saving",
                    command=lambda: self.exit_without_saving(save_window)
                ).pack(side=tk.RIGHT, padx=5)
                
                # Wait for the dialog to be closed
                self.root.wait_window(save_window)
                
            else:  # No was clicked - delete all temp files
                self.cleanup_temp_files()
                self.root.destroy()
                
        else:
            # No temp files, just exit
            self.root.destroy()
    
    def save_selected_and_exit(self, listbox, temp_files, dialog):
        """Save selected files and exit"""
        selected_indices = listbox.curselection()
        
        for i in selected_indices:
            source = temp_files[i]
            dest = os.path.join(os.getcwd(), os.path.basename(source))
            try:
                shutil.copy2(source, dest)
            except Exception as e:
                messagebox.showwarning("Warning", f"Could not save {os.path.basename(source)}: {str(e)}")
        
        dialog.destroy()
        self.cleanup_temp_files()
        self.root.destroy()
    
    def save_all_and_exit(self, temp_files, dialog):
        """Save all files and exit"""
        for source in temp_files:
            dest = os.path.join(os.getcwd(), os.path.basename(source))
            try:
                shutil.copy2(source, dest)
            except Exception as e:
                messagebox.showwarning("Warning", f"Could not save {os.path.basename(source)}: {str(e)}")
        
        dialog.destroy()
        self.cleanup_temp_files()
        self.root.destroy()
    
    def exit_without_saving(self, dialog):
        """Exit without saving any files"""
        dialog.destroy()
        self.cleanup_temp_files()
        self.root.destroy()
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                # If can't remove the directory, at least try to remove the files
                for file in glob.glob(os.path.join(self.temp_dir, "*")):
                    try:
                        os.remove(file)
                    except:
                        pass

def main():
    root = tk.Tk()
    app = FinScanApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()