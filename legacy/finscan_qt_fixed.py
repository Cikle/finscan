#!/usr/bin/env python
"""
FinScan Qt - A modern Qt-based interface for stock data analysis
"""
import sys
import os
import threading
import json
import subprocess
import webbrowser
from datetime import datetime
import re
import glob

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QTableWidget, QTableWidgetItem, QSplitter, QTabWidget, 
                            QProgressBar, QTextEdit, QMessageBox, QHeaderView, 
                            QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox)
from PyQt5.QtCore import Qt, QUrl, pyqtSlot, QSize, QThread, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

# We won't directly import stock_data_scraper to avoid Unicode issues
# Instead we'll call the wrapper script using subprocess

class ConsoleThread(QThread):
    """Thread for running console commands and capturing output"""
    output_received = pyqtSignal(str)
    command_finished = pyqtSignal(bool, str)
    
    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process = None
        
    def run(self):
        try:
            self.process = subprocess.Popen(
                self.command, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
            
            while True:
                # Read output line by line
                output_line = self.process.stdout.readline()
                if output_line == '' and self.process.poll() is not None:
                    break
                if output_line:
                    self.output_received.emit(output_line.strip())
            
            stderr = self.process.stderr.read()
            if stderr:
                self.output_received.emit(f"ERROR: {stderr}")
                self.command_finished.emit(False, stderr)
            else:
                self.command_finished.emit(True, "")
                
        except Exception as e:
            self.output_received.emit(f"Exception: {str(e)}")
            self.command_finished.emit(False, str(e))

class TradingViewWidget(QWebEngineView):
    """Widget for displaying TradingView charts"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(500)
        
    def load_chart(self, symbol):
        """Load TradingView chart for the given symbol"""
        # Using a simplified HTML template to avoid JavaScript issues
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TradingView Chart</title>
            <style>
                body, html { margin: 0; padding: 0; height: 100%; }
                .tradingview-widget-container { height: 100%; }
            </style>
        </head>
        <body>
            <!-- TradingView Widget BEGIN -->
            <div class="tradingview-widget-container">
                <div id="tradingview_chart"></div>
                <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                <script type="text/javascript">
                new TradingView.widget({
                    "width": "100%",
                    "height": "100%",
                    "symbol": "REPLACE_SYMBOL",
                    "interval": "D",
                    "timezone": "Etc/UTC",
                    "theme": "dark",
                    "style": "1",
                    "locale": "en",
                    "toolbar_bg": "#f1f3f6",
                    "enable_publishing": false,
                    "allow_symbol_change": true,
                    "container_id": "tradingview_chart"
                });
                </script>
            </div>
            <!-- TradingView Widget END -->
        </body>
        </html>
        """
        
        # Replace the symbol placeholder
        html = html.replace("REPLACE_SYMBOL", symbol)
        self.setHtml(html)

class FileManager:
    """Manages files and file operations"""
    def __init__(self):
        self.base_dir = os.getcwd()
        self.temp_dir = os.path.join(self.base_dir, "temp_data")
        
        # Create temp directory if it doesn't exist
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def get_files(self, pattern="*_data_*.html"):
        """Get list of report files"""
        temp_files = glob.glob(os.path.join(self.temp_dir, pattern))
        saved_files = glob.glob(os.path.join(self.base_dir, pattern))
        
        all_files = []
        
        # Process temp files
        for file_path in temp_files:
            file_name = os.path.basename(file_path)
            match = re.search(r'([A-Z]+)_data_(\d+_\d+)', file_name)
            if match:
                symbol = match.group(1)
                date_str = match.group(2).replace('_', '')
                date_obj = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                all_files.append({
                    'symbol': symbol,
                    'date': formatted_date,
                    'date_obj': date_obj,
                    'path': file_path,
                    'temp': True
                })
        
        # Process saved files
        for file_path in saved_files:
            file_name = os.path.basename(file_path)
            match = re.search(r'([A-Z]+)_data_(\d+_\d+)', file_name)
            if match:
                symbol = match.group(1)
                date_str = match.group(2).replace('_', '')
                date_obj = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                all_files.append({
                    'symbol': symbol,
                    'date': formatted_date,
                    'date_obj': date_obj,
                    'path': file_path,
                    'temp': False
                })
        
        # Sort files by date (newest first)
        all_files.sort(key=lambda x: x['date_obj'], reverse=True)
        return all_files

    def save_file(self, temp_path):
        """Move a file from temp to permanent storage"""
        if os.path.exists(temp_path) and os.path.dirname(temp_path) == self.temp_dir:
            filename = os.path.basename(temp_path)
            new_path = os.path.join(self.base_dir, filename)
            if os.path.exists(new_path):
                os.remove(new_path)
            import shutil
            shutil.copy2(temp_path, new_path)
            return new_path
        return None
    
    def delete_file(self, file_path):
        """Delete a file"""
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    
    def get_file_content(self, file_path):
        """Get content of a file"""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None

class StockDataProcessor:
    """Stock data processing and extraction"""
    @staticmethod
    def extract_metrics_from_html(html_content):
        """Extract key metrics from the HTML report"""
        import re
        # Use BeautifulSoup conditionally to avoid import errors
        try:
            from bs4 import BeautifulSoup
            
            metrics = {}
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Get symbol
            title = soup.title.text if soup.title else ""
            symbol_match = re.search(r'([A-Z]+) Financial Data', title)
            if symbol_match:
                metrics['symbol'] = symbol_match.group(1)
            
            # Get key metrics from table
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        key = cells[0].text.strip()
                        value = cells[1].text.strip()
                        metrics[key] = value
            
            # Format specific fields
            key_metrics = {
                'Price': metrics.get('Price', ''),
                'Change': metrics.get('Change', ''),
                'Market Cap': metrics.get('Market Cap', ''),
                'P/E': metrics.get('P/E', ''),
                'Volume': metrics.get('Volume', ''),
                'Recom': metrics.get('Recom', '')
            }
            
            # Calculate buy/sell ratio based on OpenInsider data
            insider_section = soup.find('div', class_='section')
            if insider_section and 'OpenInsider Data' in insider_section.get_text():
                insider_content = insider_section.get_text()
                buy_match = re.search(r'Buy Count: (\d+)', insider_content)
                sell_match = re.search(r'Sell Count: (\d+)', insider_content)
                if buy_match and sell_match:
                    key_metrics['Buy Count'] = buy_match.group(1)
                    key_metrics['Sell Count'] = sell_match.group(1)
            
            return key_metrics
        except ImportError:
            # Fallback to a simple regex approach if BeautifulSoup is not available
            metrics = {}
            # Extract symbol from title
            symbol_match = re.search(r'<title>([A-Z]+) Financial Data</title>', html_content)
            if symbol_match:
                metrics['symbol'] = symbol_match.group(1)
            
            # Extract common metrics with regex
            for key in ['Price', 'Change', 'Market Cap', 'P/E', 'Volume', 'Recom']:
                pattern = f'<td>{key}</td>\\s*<td>([^<]+)</td>'
                match = re.search(pattern, html_content)
                if match:
                    metrics[key] = match.group(1).strip()
            
            # Extract insider data
            buy_match = re.search(r'Buy Count: (\d+)', html_content)
            sell_match = re.search(r'Sell Count: (\d+)', html_content)
            if buy_match and sell_match:
                metrics['Buy Count'] = buy_match.group(1)
                metrics['Sell Count'] = sell_match.group(1)
                
            return metrics

class FinScanQt(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.file_manager = FileManager()
        self.current_file = None
        
        self.init_ui()
        self.populate_file_list()
        
        # Show default chart
        self.tradingview_widget.load_chart("NASDAQ:AAPL")
        
    def init_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("FinScan Qt - Stock Data Analyzer")
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(900, 600)
        
        # Main layout
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (controls and file list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Search controls
        search_group = QGroupBox("Symbol Search")
        search_layout = QVBoxLayout()
        
        input_layout = QHBoxLayout()
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Enter stock symbol...")
        self.symbol_input.returnPressed.connect(self.on_search_clicked)
        
        search_btn = QPushButton("Generate Data")
        search_btn.clicked.connect(self.on_search_clicked)
        
        input_layout.addWidget(self.symbol_input)
        input_layout.addWidget(search_btn)
        search_layout.addLayout(input_layout)
        
        # Quick examples
        examples_layout = QHBoxLayout()
        examples_layout.addWidget(QLabel("Examples:"))
        
        for symbol in ["AAPL", "MSFT", "GOOG", "TSLA", "AMZN"]:
            example_btn = QPushButton(symbol)
            example_btn.setFixedWidth(50)
            example_btn.clicked.connect(lambda checked, s=symbol: self.load_example(s))
            examples_layout.addWidget(example_btn)
        
        examples_layout.addStretch(1)
        search_layout.addLayout(examples_layout)
        search_group.setLayout(search_layout)
        left_layout.addWidget(search_group)
        
        # Progress and console output
        progress_group = QGroupBox("Processing Status")
        progress_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready to collect stock data...")
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(0)  # Indeterminate mode
        self.progress_bar.setMinimum(0)
        self.progress_bar.hide()
        progress_layout.addWidget(self.progress_bar)
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Consolas", 9))
        self.console_output.setMinimumHeight(100)
        self.console_output.setStyleSheet("background-color: #f0f0f0; color: #333;")
        progress_layout.addWidget(self.console_output)
        
        progress_group.setLayout(progress_layout)
        left_layout.addWidget(progress_group)
        
        # File list
        files_group = QGroupBox("Generated Reports")
        files_layout = QVBoxLayout()
        
        self.files_table = QTableWidget(0, 3)
        self.files_table.setHorizontalHeaderLabels(["Symbol", "Date", "Status"])
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.setSelectionMode(QTableWidget.SingleSelection)
        self.files_table.itemSelectionChanged.connect(self.on_file_selected)
        self.files_table.cellDoubleClicked.connect(self.on_file_double_clicked)
        files_layout.addWidget(self.files_table)
        
        buttons_layout = QHBoxLayout()
        self.view_btn = QPushButton("View Selected")
        self.view_btn.clicked.connect(self.on_view_clicked)
        self.view_btn.setEnabled(False)
        
        self.save_btn = QPushButton("Save Report")
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.save_btn.setEnabled(False)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        self.delete_btn.setEnabled(False)
        
        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.clicked.connect(self.populate_file_list)
        
        buttons_layout.addWidget(self.view_btn)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.delete_btn)
        buttons_layout.addWidget(self.refresh_btn)
        
        files_layout.addLayout(buttons_layout)
        files_group.setLayout(files_layout)
        left_layout.addWidget(files_group)
        
        # Right panel (tabs with chart and data)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_widget = QTabWidget()
        
        # Trading View Chart tab
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tradingview_widget = TradingViewWidget()
        chart_layout.addWidget(self.tradingview_widget)
        
        self.tab_widget.addTab(chart_tab, "TradingView Chart")
        
        # Stock metrics tab
        metrics_tab = QWidget()
        metrics_layout = QVBoxLayout(metrics_tab)
        
        self.metrics_display = QTextEdit()
        self.metrics_display.setReadOnly(True)
        self.metrics_display.setFont(QFont("Segoe UI", 10))
        metrics_layout.addWidget(self.metrics_display)
        
        self.tab_widget.addTab(metrics_tab, "Key Metrics")
        
        right_layout.addWidget(self.tab_widget)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial split ratio (30% left, 70% right)
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)
        self.setCentralWidget(main_widget)

        # Set style
        self.apply_style()
        
    def apply_style(self):
        """Apply styling to the application"""
        # Modern style sheet
        style = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #4a86e8;
            color: white;
            border: none;
            border-radius: 3px;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: #3a76d8;
        }
        QPushButton:disabled {
            background-color: #cccccc;
        }
        QLineEdit {
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 5px;
        }
        QTableWidget {
            border: 1px solid #cccccc;
            border-radius: 3px;
            alternate-background-color: #f9f9f9;
            gridline-color: #e0e0e0;
        }
        QTableWidget::item:selected {
            background-color: #4a86e8;
            color: white;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            border: none;
            padding: 5px;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            border: 1px solid #cccccc;
            border-bottom: none;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
            padding: 5px 10px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: white;
        }
        """
        self.setStyleSheet(style)
        
    def populate_file_list(self):
        """Populate the file list table"""
        self.files_table.setRowCount(0)
        
        files = self.file_manager.get_files()
        self.files_table.setRowCount(len(files))
        
        for row, file_info in enumerate(files):
            symbol_item = QTableWidgetItem(file_info['symbol'])
            date_item = QTableWidgetItem(file_info['date'])
            status_item = QTableWidgetItem("Temporary" if file_info['temp'] else "Saved")
            
            if file_info['temp']:
                status_item.setForeground(QColor(255, 140, 0))  # Orange for temporary
            else:
                status_item.setForeground(QColor(0, 128, 0))  # Green for saved
                
            self.files_table.setItem(row, 0, symbol_item)
            self.files_table.setItem(row, 1, date_item)
            self.files_table.setItem(row, 2, status_item)
            
    def on_file_selected(self):
        """Handle file selection in the list"""
        selected_items = self.files_table.selectedItems()
        if selected_items:
            selected_row = self.files_table.row(selected_items[0])
            files = self.file_manager.get_files()
            
            if 0 <= selected_row < len(files):
                file_info = files[selected_row]
                self.current_file = file_info
                
                # Enable buttons based on file status
                self.view_btn.setEnabled(True)
                self.delete_btn.setEnabled(True)
                self.save_btn.setEnabled(file_info['temp'])
                
                # Update metrics display
                content = self.file_manager.get_file_content(file_info['path'])
                if content:
                    metrics = StockDataProcessor.extract_metrics_from_html(content)
                    
                    # Format metrics for display
                    formatted_metrics = f"<h2>{file_info['symbol']} Key Metrics</h2>"
                    formatted_metrics += f"<p><b>Report Date:</b> {file_info['date']}</p>"
                    
                    formatted_metrics += "<h3>Market Data</h3>"
                    formatted_metrics += "<table border='0' style='width:100%'>"
                    
                    if 'Price' in metrics:
                        formatted_metrics += f"<tr><td><b>Price:</b></td><td>{metrics['Price']}</td>"
                        formatted_metrics += f"<td><b>Change:</b></td><td>{metrics['Change']}</td></tr>"
                    
                    if 'Market Cap' in metrics:
                        formatted_metrics += f"<tr><td><b>Market Cap:</b></td><td>{metrics['Market Cap']}</td>"
                        formatted_metrics += f"<td><b>P/E:</b></td><td>{metrics['P/E']}</td></tr>"
                        
                    if 'Volume' in metrics:
                        formatted_metrics += f"<tr><td><b>Volume:</b></td><td>{metrics['Volume']}</td>"
                        formatted_metrics += f"<td><b>Analyst Rating:</b></td><td>{metrics.get('Recom', 'N/A')}</td></tr>"
                    
                    formatted_metrics += "</table>"
                    
                    # Insider data
                    if 'Buy Count' in metrics:
                        formatted_metrics += "<h3>Insider Trading</h3>"
                        formatted_metrics += f"<p>Buy Count: {metrics['Buy Count']} | Sell Count: {metrics['Sell Count']}</p>"
                    
                    self.metrics_display.setHtml(formatted_metrics)
                    
                    # Update chart with the symbol
                    self.tradingview_widget.load_chart(f"NASDAQ:{file_info['symbol']}")
        else:
            self.view_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.current_file = None
    
    def on_file_double_clicked(self, row, column):
        """Handle double-click on file in the list"""
        self.on_view_clicked()
    
    def on_view_clicked(self):
        """View selected report in browser"""
        if self.current_file and os.path.exists(self.current_file['path']):
            webbrowser.open(f"file://{self.current_file['path']}")
    
    def on_save_clicked(self):
        """Save temporary file to permanent storage"""
        if self.current_file and self.current_file['temp']:
            new_path = self.file_manager.save_file(self.current_file['path'])
            if new_path:
                QMessageBox.information(self, "Success", f"Report saved as {os.path.basename(new_path)}")
                self.populate_file_list()
    
    def on_delete_clicked(self):
        """Delete selected file"""
        if self.current_file:
            confirm = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete {os.path.basename(self.current_file['path'])}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                if self.file_manager.delete_file(self.current_file['path']):
                    self.populate_file_list()
                    self.current_file = None
                    self.view_btn.setEnabled(False)
                    self.save_btn.setEnabled(False)
                    self.delete_btn.setEnabled(False)
    
    def load_example(self, symbol):
        """Load example symbol"""
        self.symbol_input.setText(symbol)
        self.on_search_clicked()
        
    def on_search_clicked(self):
        """Handle search button click"""
        symbol = self.symbol_input.text().strip().upper()
        if not symbol:
            QMessageBox.warning(self, "Input Error", "Please enter a stock symbol!")
            return
            
        self.generate_stock_data(symbol)
        
    def generate_stock_data(self, symbol):
        """Generate stock data report for the given symbol"""
        self.status_label.setText(f"Processing {symbol}...")
        self.progress_bar.show()
        self.console_output.clear()
        
        # Use stock_data_scraper_wrapper.py to avoid Unicode issues
        cmd = f"python stock_data_scraper_wrapper.py {symbol}"
        
        # Run the command in a thread
        self.console_thread = ConsoleThread(cmd)
        self.console_thread.output_received.connect(self.update_console)
        self.console_thread.command_finished.connect(lambda success, err: self.on_command_finished(success, err, symbol))
        self.console_thread.start()
        
    def update_console(self, text):
        """Update console output with new text"""
        self.console_output.append(text)
        self.console_output.ensureCursorVisible()
        
    def on_command_finished(self, success, error, symbol):
        """Handle completion of the stock data generation command"""
        self.progress_bar.hide()
        
        if success:
            self.status_label.setText(f"Data collection for {symbol} completed successfully!")
            self.populate_file_list()
            
            # Find the newly generated file
            files = self.file_manager.get_files()
            for i, file_info in enumerate(files):
                if file_info['symbol'] == symbol:
                    # Select the newly generated file
                    self.files_table.selectRow(i)
                    break
                    
            # Ask if user wants to view the report
            confirm = QMessageBox.question(
                self,
                "View Report",
                f"Data for {symbol} collected successfully. Would you like to view the report?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if confirm == QMessageBox.Yes:
                self.on_view_clicked()
        else:
            self.status_label.setText(f"Error collecting data for {symbol}!")
            QMessageBox.critical(self, "Error", f"Failed to generate data: {error}")

def main():
    app = QApplication(sys.argv)
    window = FinScanQt()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
