#!/usr/bin/env python
"""
FinScan Qt - A modern Qt-based interface for stock data analysis
All-in-one version that handles Unicode encoding directly

Copyright (c) 2025 Cyril Lutziger
License: MIT (see LICENSE file for details)
"""
import sys
import os
import threading
import json
import subprocess
import webbrowser
import shutil
from datetime import datetime
import re
import glob

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QTableWidget, QTableWidgetItem, QSplitter, QTabWidget, 
                            QProgressBar, QTextEdit, QMessageBox, QHeaderView, 
                            QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox)
from PyQt5.QtCore import QSettings
from PyQt5.QtCore import Qt, QUrl, pyqtSlot, QSize, QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

# Import stock_data_scraper directly - we'll handle Unicode safety within this app
try:
    import stock_data_scraper
except ImportError:
    print("Error: stock_data_scraper.py not found in the current directory.")
    sys.exit(1)


class StockDataThread(QThread):
    """Thread for running stock data collection with Unicode safety"""
    output_received = pyqtSignal(str)
    data_ready = pyqtSignal(bool, str, str)  # Success, Error message, Filename
    
    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol
    
    def run(self):
        try:
            # Set environment variable for encoding
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            
            # Generate a unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.symbol}_data_{timestamp}.html"              # Use the FileManager's temp directory path
            file_manager = FileManager()
            if not os.path.exists(file_manager.temp_dir):
                os.makedirs(file_manager.temp_dir, exist_ok=True)
            full_path = os.path.join(file_manager.temp_dir, filename)
            
            # Safe output function to handle Unicode characters
            def safe_print(text):
                safe_text = str(text).encode('ascii', 'replace').decode('ascii')
                self.output_received.emit(safe_text)
            
            # Print initial message
            safe_print(f"Starting data collection for {self.symbol}...")
            
            try:
                # Create scraper instance and collect data
                scraper = stock_data_scraper.StockDataScraper(self.symbol)
                
                # Handle output safely using a custom output capture function
                original_print = print
                def custom_print(*args, **kwargs):
                    text = " ".join(map(str, args))
                    safe_print(text)
                
                # Use a context manager for temporarily redirecting print output
                from contextlib import redirect_stdout
                import io
                
                # Capture print output
                output_buffer = io.StringIO()
                with redirect_stdout(output_buffer):
                    # Run data collection
                    safe_print(f"Collecting data for {self.symbol}...")
                    scraper.collect_all_data()
                    
                    # Save HTML report to the temp directory explicitly
                    html_file = scraper.save_html(full_path)
                
                # Process any captured output
                captured_output = output_buffer.getvalue()
                for line in captured_output.splitlines():
                    safe_print(line)
                
                # Check if any meaningful data was collected
                if not scraper.data or (isinstance(scraper.data, dict) and 
                                      (not scraper.data.get('finviz') or
                                       len(scraper.data.get('finviz', {})) <= 1)):
                    safe_print(f"No data found for symbol {self.symbol}")
                    self.data_ready.emit(False, f"Symbol {self.symbol} could not be found", "")
                else:
                    # Success
                    safe_print(f"Data collection complete for {self.symbol}")
                    safe_print(f"Report saved to {filename}")
                    self.data_ready.emit(True, "", full_path)  # Return full path to the file
                
            except Exception as e:
                safe_error = str(e).encode('ascii', 'replace').decode('ascii')
                safe_print(f"ERROR: {safe_error}")
                self.data_ready.emit(False, safe_error, "")
                
        except Exception as e:
            safe_error = str(e).encode('ascii', 'replace').decode('ascii')
            self.output_received.emit(f"Exception: {safe_error}")
            self.data_ready.emit(False, safe_error, "")


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


class WebBridge(QObject):
    """Bridge for JavaScript to Python communication"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None
    
    @pyqtSlot(str)
    def openExternal(self, url):
        """Opens an external URL in the default browser"""
        webbrowser.open(url)
        
    @pyqtSlot(str, str)
    def openInTab(self, url, title="External Page"):
        """Opens an external URL in the appropriate tab based on the domain"""
        if self.main_window:
            # Check if URL is from one of our supported sites
            if "finviz.com" in url:
                self.main_window.finviz_view.load(QUrl(url))
                self.main_window.tab_widget.setCurrentWidget(self.main_window.finviz_tab)
            elif "openinsider.com" in url:
                self.main_window.openinsider_view.load(QUrl(url))
                self.main_window.tab_widget.setCurrentWidget(self.main_window.openinsider_tab)
            elif "finance.yahoo.com" in url:
                self.main_window.yahoo_view.load(QUrl(url))
                self.main_window.tab_widget.setCurrentWidget(self.main_window.yahoo_tab)
            else:
                # For other URLs, open in a new tab
                self.main_window.open_url_in_tab(url, title)


class TradingViewWidget(QWebEngineView):
    """Widget for displaying TradingView charts"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(500)
        
        # Set cache path to a known writable location
        profile = self.page().profile()
        cache_dir = os.path.join(os.path.expanduser("~"), ".finscan_cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        profile.setCachePath(cache_dir)
        profile.setPersistentStoragePath(cache_dir)
          # Add bridge to open external URLs
        self.page().profile().downloadRequested.connect(self.on_download_requested)
        
        # Set up channel for JavaScript to communicate with Python
        self.page().setWebChannel(QWebChannel(self.page()))
        self.bridge = WebBridge()
        self.page().webChannel().registerObject('qt', self.bridge)
          
    def on_download_requested(self, download):
        """Handle download requests by opening in external browser"""
        url = download.url().toString()
        webbrowser.open(url)
        download.cancel()  # Cancel the download in the WebEngine
        
    def load_chart(self, symbol, company_name=""):
        """Load TradingView chart for the given symbol"""
        # Extract just the symbol part without exchange
        symbol_only = symbol.split(':')[-1] if ':' in symbol else symbol
        
        # Use a more reliable chart method with direct image embedding
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Stock Chart</title>        <style>                :root {
                    --bg-color: #f8f4f4;
                    --text-color: #333333;
                    --secondary-text-color: #555555;
                    --note-color: #999;
                    --button-bg: #2962ff;
                    --button-hover-bg: #1E52E0;
                    --shadow-color: rgba(0,0,0,0.2);
                }
                  body, html { 
                    margin: 0; 
                    padding: 0; 
                    height: 100%; 
                    width: 100%; 
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    background-color: var(--bg-color);
                    color: var(--text-color);
                    font-family: Arial, sans-serif;
                    overflow-y: auto;
                }                .chart-container {
                    width: 100%;
                    padding-top: 20px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    text-align: center;
                    margin-top: 20px;
                }
                .symbol {
                    font-size: 24px;
                    margin-bottom: 20px;
                    font-weight: bold;
                }
                .company-name {
                    font-size: 16px;
                    margin-bottom: 15px;
                    color: var(--secondary-text-color);
                }
                .chart-image {
                    width: 95%;
                    max-width: 1200px;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px var(--shadow-color);
                }                .note {
                    margin-top: 10px;
                    color: var(--note-color);
                    font-size: 12px;
                }                
                .button {
                    margin-top: 15px;
                    margin-right: 12px;
                    margin-left: 12px;
                    padding: 10px 20px;
                    background-color: var(--button-bg);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    text-decoration: none;
                    font-weight: bold;
                    transition: background-color 0.2s;
                    display: inline-block;
                }
                .button:hover {
                    background-color: var(--button-hover-bg);
                }                .chart-options {
                    margin-bottom: 10px;
                    display: flex;
                    justify-content: center;
                }
                .chart-btn {
                    margin: 0 5px;
                    padding: 5px 15px;
                    background-color: #eee;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .chart-btn.active {
                    background-color: var(--button-bg);
                    color: white;
                    border-color: var(--button-bg);
                }
                .chart-btn:hover:not(.active) {
                    background-color: #ddd;
                }
                .buttons-container {
                    margin-top: 20px;
                    margin-bottom: 15px;
                    display: flex;
                    gap: 20px;
                    flex-wrap: wrap;
                    justify-content: center;
                }
                .theme-toggle {
                    margin-top: 20px;
                }
                #theme-button {
                    padding: 6px 12px;
                    background-color: #555;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: bold;
                    transition: background-color 0.2s;
                }
                #theme-button:hover {
                    background-color: #666;
                }
            </style>
        </head>
        <body>
            <div class="chart-container">
                <div class="symbol">REPLACE_SYMBOL</div>
                <div class="company-name">COMPANY_NAME</div>                <!-- Chart timeframe options -->                <div class="chart-options">
                    <button class="chart-btn active" data-timeframe="d">Daily</button>
                    <button class="chart-btn" data-timeframe="w">Weekly</button>
                    <button class="chart-btn" data-timeframe="y">Monthly</button>
                    <button class="chart-btn" data-timeframe="m">Yearly</button>
                </div>
                <!-- Use direct img tag instead of background-image for better reliability -->
                <img class="chart-image" src="https://charts2.finviz.com/chart.ashx?t=SYMBOL_ONLY&ty=c&ta=1&p=d&s=l" alt="SYMBOL_ONLY Chart" onerror="this.onerror=null; this.src='https://finviz.com/chart.ashx?t=SYMBOL_ONLY&ty=c&ta=1&p=d&s=l';">
            </div>              <!-- Script to handle image loading errors and chart timeframe -->            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    // Handle image loading errors
                    const img = document.querySelector('.chart-image');
                    img.onerror = function() {
                        // Try alternative source if the first one fails
                        this.src = 'https://finviz.com/chart.ashx?t=SYMBOL_ONLY&ty=c&ta=1&p=d&s=l';
                        
                        // If still fails, show error message
                        this.onerror = function() {
                            this.style.display = 'none';
                            const container = document.querySelector('.chart-container');
                            const errorMsg = document.createElement('div');
                            errorMsg.innerHTML = '<p style="color: #ff6b6b; font-size: 18px;">Unable to load chart for SYMBOL_ONLY</p>';
                            container.insertBefore(errorMsg, document.querySelector('.note'));
                        };
                    };
                    
                    // Handle chart timeframe buttons
                    const timeframeButtons = document.querySelectorAll('.chart-btn');
                    timeframeButtons.forEach(button => {
                        button.addEventListener('click', function() {
                            // Remove active class from all buttons
                            timeframeButtons.forEach(btn => btn.classList.remove('active'));
                            
                            // Add active class to clicked button
                            this.classList.add('active');
                            
                            // Update chart timeframe
                            const timeframe = this.getAttribute('data-timeframe');
                            const img = document.querySelector('.chart-image');
                            const currentSrc = img.src;                            // Update timeframe parameter
                            console.log(`Changing chart to timeframe: ${timeframe}`);
                            
                            // Create a completely new URL with the selected timeframe
                            const baseUrl = currentSrc.split('&p=')[0];
                            const newSrc = `${baseUrl}&p=${timeframe}${currentSrc.includes('&s=') ? '&s=l' : ''}`;
                            
                            console.log(`New URL: ${newSrc}`);
                            img.src = newSrc;
                        });
                    });                    // Handle external links to open in browser
                    const externalLinks = document.querySelectorAll('.button');
                    externalLinks.forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            try {
                                const urlStr = this.href;
                                if (urlStr) {
                                    console.log("Opening URL: " + urlStr);
                                    
                                    // Use Qt bridge to open links in tabs
                                    if (window.qt && typeof window.qt.openInTab === 'function') {
                                        console.log("Using Qt bridge");
                                        window.qt.openInTab(urlStr, this.textContent.trim());
                                    } else {
                                        console.log("Fallback to window.open");
                                        window.open(urlStr, '_blank');
                                    }
                                }
                            } catch (error) {
                                console.error("Error handling link click: ", error);
                            }
                        });
                    });
                });
            </script>
        </body>
        </html>
        """
        
        # Replace the symbol placeholder
        html = html.replace("REPLACE_SYMBOL", symbol)
        html = html.replace("SYMBOL_ONLY", symbol_only)
        
        # Replace company name or hide the element if not provided
        if company_name:
            html = html.replace("COMPANY_NAME", company_name)
        else:
            # If no company name, replace with empty div
            html = html.replace('<div class="company-name">COMPANY_NAME</div>', '')
        
        # Apply the HTML
        self.setHtml(html)


class FileManager:
    """Manages files and file operations"""
    def __init__(self):
        self.base_dir = os.getcwd()
        
        # Use a temp_data folder for temporary storage
        self.temp_dir = os.path.join(self.base_dir, "temp_data")
        
        # Use a saved_data folder for permanent storage
        self.saved_dir = os.path.join(self.base_dir, "saved_data")
        
        # Create directories if they don't exist
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            
        if not os.path.exists(self.saved_dir):
            os.makedirs(self.saved_dir)
    
    def get_files(self, pattern="*_data_*.html"):
        """Get list of report files"""
        temp_files = glob.glob(os.path.join(self.temp_dir, pattern))
        saved_files = glob.glob(os.path.join(self.saved_dir, pattern))
        
        all_files = []
        
        # Process temp files - these are ACTUALLY temporary files
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
                    'temp': True  # Mark files from temp directory as temporary
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
    
    def save_file(self, temp_path, target_dir=None):
        """Move a file from temp to permanent storage
        
        Args:
            temp_path: Path to the temporary file
            target_dir: Optional target directory. If None, use the saved_data directory
        """
        if os.path.exists(temp_path):
            # Make sure this is a path in the temp directory
            norm_temp_dir = os.path.normpath(self.temp_dir)
            norm_path_dir = os.path.normpath(os.path.dirname(temp_path))
            
            if norm_temp_dir == norm_path_dir:
                filename = os.path.basename(temp_path)
                
                # Use specified target directory or default to saved_dir
                if target_dir and os.path.isdir(target_dir):
                    new_path = os.path.join(target_dir, filename)
                else:
                    new_path = os.path.join(self.saved_dir, filename)
                
                print(f"Moving {temp_path} to {new_path}")
                
                # Remove existing file with same name if it exists
                if os.path.exists(new_path):
                    os.remove(new_path)
                    
                # Copy file from temp to permanent location
                shutil.copy2(temp_path, new_path)
                
                # Remove the temp file after copying
                try:
                    os.remove(temp_path)
                except Exception as e:
                    print(f"Warning: Could not remove temp file: {e}")
                    
                return new_path
            else:
                print(f"Error: Path {temp_path} is not in temp directory {self.temp_dir}")
        else:
            print(f"Error: File does not exist: {temp_path}")
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
            
            # Extract company name
            company_name = ""
            h1_tags = soup.find_all('h1')
            for h1 in h1_tags:
                if metrics.get('symbol', '') in h1.text:
                    company_name = h1.text.strip()
                    # Remove the symbol from the company name
                    if metrics.get('symbol', '') in company_name:
                        company_name = company_name.replace(metrics.get('symbol', ''), '').strip()
                        # Remove any remaining parentheses
                        company_name = re.sub(r'[\(\)]', '', company_name).strip()
                    
                    metrics['longName'] = company_name
                    break
            
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
              # Format specific fields and organize into categories
            key_metrics = {
                # Basic info
                'symbol': metrics.get('symbol', ''),
                'longName': metrics.get('longName', ''),
                
                # Price data
                'Price': metrics.get('Price', ''),
                'Change': metrics.get('Change', ''),
                'Market Cap': metrics.get('Market Cap', ''),
                'P/E': metrics.get('P/E', ''),
                'Volume': metrics.get('Volume', ''),
                'Recom': metrics.get('Recom', ''),
                
                # Categories for organization
                'valuation_metrics': {},
                'financial_metrics': {},
                'technical_metrics': {},
                'growth_metrics': {}
            }
            
            # Organize metrics into categories
            for key, value in metrics.items():
                # Valuation metrics
                if key in ['P/E', 'P/S', 'P/B', 'P/FCF', 'EPS', 'Dividend', 'Dividend %', 'PEG', 'EV/EBITDA']:
                    key_metrics['valuation_metrics'][key] = value
                
                # Financial metrics
                elif key in ['ROA', 'ROE', 'ROI', 'Gross Margin', 'Oper. Margin', 'Profit Margin', 'Earnings', 'Payout', 'Debt/Eq', 'Current Ratio']:
                    key_metrics['financial_metrics'][key] = value
                
                # Technical metrics
                elif key in ['RSI', 'Rel Volume', 'Beta', 'ATR', 'Volatility', '52W High', '52W Low', 'SMA20', 'SMA50', 'SMA200']:
                    key_metrics['technical_metrics'][key] = value
                
                # Growth metrics
                elif 'Growth' in key or key in ['EPS next Y', 'EPS next Q', 'Sales Q/Q', 'EPS Q/Q']:
                    key_metrics['growth_metrics'][key] = value
            
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
        
        # Apply styling
        self.apply_style()
        
        # Show default chart
        self.tradingview_widget.load_chart("NASDAQ:NVDA")
        
        # Set the main window reference in WebBridge objects
        self.tradingview_widget.bridge.main_window = self
    
    def open_url_in_tab(self, url, title):
        """Opens a URL in a new tab"""
        # Create a new web view for the tab
        web_view = QWebEngineView()
        web_view.load(QUrl(url))
        
        # Add to tab widget
        tab_index = self.tab_widget.addTab(web_view, title)
        self.tab_widget.setCurrentIndex(tab_index)
        
        # Add a close button to the tab
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet("QPushButton { border: none; color: #777; } QPushButton:hover { color: #f00; }")
        close_button.clicked.connect(lambda: self.close_tab(tab_index))
        self.tab_widget.tabBar().setTabButton(tab_index, self.tab_widget.tabBar().RightSide, close_button)
        
    def close_tab(self, index):
        """Close a tab by index"""
        # Don't close the first five tabs (Chart & Metrics, Full Report, Finviz, OpenInsider, Yahoo Finance)
        if index > 4:
            self.tab_widget.removeTab(index)
    
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
          # Theme toggle button removed - using only light mode
        
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
        
        # Combined Chart and Metrics tab
        combined_tab = QWidget()
        combined_layout = QVBoxLayout(combined_tab)
        
        # Symbol header
        self.symbol_header = QLabel("")
        self.symbol_header.setAlignment(Qt.AlignCenter)
        self.symbol_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        combined_layout.addWidget(self.symbol_header)
        
        # Create splitter for chart and metrics
        metrics_splitter = QSplitter(Qt.Vertical)
        
        # Trading View Chart
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tradingview_widget = TradingViewWidget()
        chart_layout.addWidget(self.tradingview_widget)
        
        # Stock metrics
        metrics_container = QWidget()
        metrics_layout = QVBoxLayout(metrics_container)
        metrics_layout.setContentsMargins(10, 10, 10, 10)
        
        self.metrics_display = QTextEdit()
        self.metrics_display.setReadOnly(True)
        self.metrics_display.setFont(QFont("Segoe UI", 10))
        metrics_layout.addWidget(self.metrics_display)
        
        # Add widgets to splitter
        metrics_splitter.addWidget(chart_container)
        metrics_splitter.addWidget(metrics_container)
        
        # Set initial sizes (60% chart, 40% metrics)
        metrics_splitter.setSizes([600, 400])
        
        combined_layout.addWidget(metrics_splitter)
        combined_tab.setLayout(combined_layout)
        
        self.tab_widget.addTab(combined_tab, "Chart & Metrics")
          # HTML Report tab (will be populated when a report is selected)
        self.report_tab = QWidget()
        report_layout = QVBoxLayout(self.report_tab)
        
        self.report_view = QWebEngineView()
        report_layout.addWidget(self.report_view)
        
        self.tab_widget.addTab(self.report_tab, "Full Report")
        
        # Create dedicated tabs for external services
        self.finviz_tab = QWidget()
        finviz_layout = QVBoxLayout(self.finviz_tab)
        self.finviz_view = QWebEngineView()
        finviz_layout.addWidget(self.finviz_view)
        self.tab_widget.addTab(self.finviz_tab, "Finviz")
        
        self.openinsider_tab = QWidget()
        openinsider_layout = QVBoxLayout(self.openinsider_tab)
        self.openinsider_view = QWebEngineView()
        openinsider_layout.addWidget(self.openinsider_view)
        self.tab_widget.addTab(self.openinsider_tab, "OpenInsider")
        
        self.yahoo_tab = QWidget()
        yahoo_layout = QVBoxLayout(self.yahoo_tab)
        self.yahoo_view = QWebEngineView()
        yahoo_layout.addWidget(self.yahoo_view)
        self.tab_widget.addTab(self.yahoo_tab, "Yahoo Finance")
        
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
        # Define colors
        colors = {
            "bg": "#f5f5f5",
            "text": "#333333",
            "accent": "#4a86e8",
            "accent_hover": "#3a76d8",
            "border": "#cccccc",
            "disabled": "#cccccc",
            "alt_bg": "#f9f9f9",
            "header_bg": "#e0e0e0", 
            "tab_bg": "#e0e0e0",
            "tab_selected": "white"
        }
        
        # Modern style sheet with dynamic colors
        style = f"""
        QMainWindow, QDialog {{
            background-color: {colors["bg"]};
            color: {colors["text"]};
        }}
        QWidget {{
            color: {colors["text"]};
        }}
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {colors["border"]};
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            color: {colors["text"]};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }}
        QPushButton {{
            background-color: {colors["accent"]};
            color: white;
            border: none;
            border-radius: 3px;
            padding: 5px 10px;
        }}
        QPushButton:hover {{
            background-color: {colors["accent_hover"]};
        }}
        QPushButton:disabled {{
            background-color: {colors["disabled"]};
        }}
        QPushButton#themeToggleBtn {{
            background-color: {colors["header_bg"]};
            padding: 5px;
        }}
        QPushButton#themeToggleBtn:hover {{
            background-color: {colors["accent"]};
        }}
        QLineEdit {{
            border: 1px solid {colors["border"]};
            border-radius: 3px;
            padding: 5px;
            background-color: {colors["bg"]};
            color: {colors["text"]};
        }}
        QTableWidget {{
            border: 1px solid {colors["border"]};
            border-radius: 3px;
            alternate-background-color: {colors["alt_bg"]};
            gridline-color: {colors["border"]};
            background-color: {colors["bg"]};
            color: {colors["text"]};
        }}
        QTableWidget::item:selected {{
            background-color: {colors["accent"]};
            color: white;
        }}
        QHeaderView::section {{
            background-color: {colors["header_bg"]};
            border: none;
            padding: 5px;
            color: {colors["text"]};
        }}
        QTabWidget::pane {{
            border: 1px solid {colors["border"]};
            border-radius: 3px;
        }}
        QTabBar::tab {{
            background-color: {colors["tab_bg"]};
            border: 1px solid {colors["border"]};
            border-bottom: none;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
            padding: 5px 10px;
            margin-right: 2px;
            color: {colors["text"]};
        }}
        QTabBar::tab:selected {{
            background-color: {colors["tab_selected"]};
        }}
        QTextEdit {{
            background-color: {colors["bg"]};
            color: {colors["text"]};
            border: 1px solid {colors["border"]};
        }}
        QLabel {{
            color: {colors["text"]};
        }}
        QComboBox {{
            border: 1px solid {colors["border"]};
            border-radius: 3px;
            padding: 5px;
            background-color: {colors["bg"]};
            color: {colors["text"]};
        }}
        QProgressBar {{
            border: 1px solid {colors["border"]};
            border-radius: 3px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {colors["accent"]};
        }}
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
                    
                    # Get company name from metrics
                    company_name = metrics.get('longName', '')
                    if not company_name:
                        # Fallback: Extract company name from the content if not in metrics
                        company_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
                        if company_match:
                            company_name = company_match.group(1).strip()
                            if file_info['symbol'] in company_name:
                                company_name = company_name.replace(file_info['symbol'], '').strip()
                                # Remove any remaining parentheses
                                company_name = re.sub(r'[\(\)]', '', company_name).strip()
                    
                    # Update the symbol header
                    header_text = f"{file_info['symbol']}"
                    if company_name:
                        header_text += f" - {company_name}"
                    self.symbol_header.setText(header_text)
                      # Format metrics for display with collapsible sections
                    formatted_metrics = f"""
                    <style>
                        .collapsible {{
                            background-color: #f1f1f1;
                            color: #444;
                            cursor: pointer;
                            padding: 10px;
                            width: 100%;
                            border: none;
                            text-align: left;
                            outline: none;
                            font-size: 15px;
                            margin-top: 10px;
                            border-radius: 4px;
                        }}
                        .active, .collapsible:hover {{
                            background-color: #ddd;
                        }}
                        .content {{
                            padding: 0 10px;
                            max-height: 0;
                            overflow: hidden;
                            transition: max-height 0.2s ease-out;
                            background-color: #f9f9f9;
                            border-radius: 0 0 4px 4px;
                        }}
                        .expanded {{
                            max-height: 1000px !important;
                            padding: 10px;
                            border: 1px solid #ddd;
                        }}
                        table {{
                            width: 100%;
                            border-collapse: collapse;
                        }}
                        td, th {{
                            padding: 4px;
                        }}
                        .key-metrics {{
                            background-color: #e8f4f8;
                            padding: 10px;
                            border-radius: 4px;
                            margin-bottom: 15px;
                        }}
                        .section-heading {{
                            font-weight: bold;
                            color: #2962ff;
                            margin-top: 15px;
                            margin-bottom: 5px;
                        }}
                    </style>
                    <script>
                        function toggleCollapsible(id) {{
                            var content = document.getElementById(id);
                            content.classList.toggle("expanded");
                            
                            var btn = document.querySelector('button[data-target="' + id + '"]');
                            if (content.classList.contains("expanded")) {{
                                btn.innerHTML = btn.innerHTML.replace("▼", "▲");
                            }} else {{
                                btn.innerHTML = btn.innerHTML.replace("▲", "▼");
                            }}
                        }}
                    </script>
                    """
                    
                    # Header with symbol and company name
                    if company_name:
                        formatted_metrics += f"<h2>{file_info['symbol']} - {company_name}</h2>"
                    else:
                        formatted_metrics += f"<h2>{file_info['symbol']} Key Metrics</h2>"
                    
                    formatted_metrics += f"<p><b>Report Date:</b> {file_info['date']}</p>"
                    
                    # Key market data - always visible
                    formatted_metrics += "<div class='key-metrics'>"
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
                    
                    formatted_metrics += "</table></div>"
                      # Add collapsible sections for additional data
                    
                    # Valuation metrics section
                    if metrics.get('valuation_metrics') and len(metrics['valuation_metrics']) > 0:
                        formatted_metrics += "<button class='collapsible' data-target='valuation-metrics' onclick='toggleCollapsible(\"valuation-metrics\")'>Valuation Metrics ▼</button>"
                        formatted_metrics += "<div id='valuation-metrics' class='content'>"
                        formatted_metrics += "<table border='0' style='width:100%'>"
                        
                        # Display valuation metrics in rows of 2 columns
                        items = list(metrics['valuation_metrics'].items())
                        for i in range(0, len(items), 2):
                            formatted_metrics += "<tr>"
                            k1, v1 = items[i]
                            formatted_metrics += f"<td><b>{k1}:</b></td><td>{v1}</td>"
                            
                            # Add second column if available
                            if i + 1 < len(items):
                                k2, v2 = items[i + 1]
                                formatted_metrics += f"<td><b>{k2}:</b></td><td>{v2}</td>"
                            
                            formatted_metrics += "</tr>"
                            
                        formatted_metrics += "</table>"
                        formatted_metrics += "</div>"
                    
                    # Financial metrics section
                    if metrics.get('financial_metrics') and len(metrics['financial_metrics']) > 0:
                        formatted_metrics += "<button class='collapsible' data-target='financial-metrics' onclick='toggleCollapsible(\"financial-metrics\")'>Financial Metrics ▼</button>"
                        formatted_metrics += "<div id='financial-metrics' class='content'>"
                        formatted_metrics += "<table border='0' style='width:100%'>"
                        
                        # Display financial metrics in rows of 2 columns
                        items = list(metrics['financial_metrics'].items())
                        for i in range(0, len(items), 2):
                            formatted_metrics += "<tr>"
                            k1, v1 = items[i]
                            formatted_metrics += f"<td><b>{k1}:</b></td><td>{v1}</td>"
                            
                            # Add second column if available
                            if i + 1 < len(items):
                                k2, v2 = items[i + 1]
                                formatted_metrics += f"<td><b>{k2}:</b></td><td>{v2}</td>"
                            
                            formatted_metrics += "</tr>"
                            
                        formatted_metrics += "</table>"
                        formatted_metrics += "</div>"
                    
                    # Technical metrics section
                    if metrics.get('technical_metrics') and len(metrics['technical_metrics']) > 0:
                        formatted_metrics += "<button class='collapsible' data-target='technical-metrics' onclick='toggleCollapsible(\"technical-metrics\")'>Technical Metrics ▼</button>"
                        formatted_metrics += "<div id='technical-metrics' class='content'>"
                        formatted_metrics += "<table border='0' style='width:100%'>"
                        
                        # Display technical metrics in rows of 2 columns
                        items = list(metrics['technical_metrics'].items())
                        for i in range(0, len(items), 2):
                            formatted_metrics += "<tr>"
                            k1, v1 = items[i]
                            formatted_metrics += f"<td><b>{k1}:</b></td><td>{v1}</td>"
                            
                            # Add second column if available
                            if i + 1 < len(items):
                                k2, v2 = items[i + 1]
                                formatted_metrics += f"<td><b>{k2}:</b></td><td>{v2}</td>"
                            
                            formatted_metrics += "</tr>"
                            
                        formatted_metrics += "</table>"
                        formatted_metrics += "</div>"                    # Growth metrics section
                    if metrics.get('growth_metrics') and len(metrics['growth_metrics']) > 0:
                        formatted_metrics += "<button class='collapsible' data-target='growth-metrics' onclick='toggleCollapsible(\"growth-metrics\")'>Growth Metrics ▼</button>"
                        formatted_metrics += "<div id='growth-metrics' class='content'>"
                        formatted_metrics += "<table border='0' style='width:100%'>"
                        
                        # Display growth metrics in rows of 2 columns
                        items = list(metrics['growth_metrics'].items())
                        for i in range(0, len(items), 2):
                            formatted_metrics += "<tr>"
                            k1, v1 = items[i]
                            formatted_metrics += f"<td><b>{k1}:</b></td><td>{v1}</td>"
                            
                            # Add second column if available
                            if i + 1 < len(items):
                                k2, v2 = items[i + 1]
                                formatted_metrics += f"<td><b>{k2}:</b></td><td>{v2}</td>"
                            
                            formatted_metrics += "</tr>"
                            
                        formatted_metrics += "</table>"
                        formatted_metrics += "</div>"
                    
                    # Insider data section
                    if 'Buy Count' in metrics and 'Sell Count' in metrics:
                        formatted_metrics += "<button class='collapsible' data-target='insider-data' onclick='toggleCollapsible(\"insider-data\")'>Insider Trading Data ▼</button>"
                        formatted_metrics += "<div id='insider-data' class='content'>"
                        formatted_metrics += f"<p><b>Buy Count:</b> {metrics['Buy Count']} | <b>Sell Count:</b> {metrics['Sell Count']}</p>"
                        formatted_metrics += "</div>"
                    
                    self.metrics_display.setHtml(formatted_metrics)
                    
                    # Update chart with the symbol and company name (if available)
                    if self.tradingview_widget.load_chart.__code__.co_argcount > 2:  # Check if method accepts company_name parameter
                        self.tradingview_widget.load_chart(f"NASDAQ:{file_info['symbol']}", company_name)
                    else:
                        # Fallback for older version without company_name support
                        self.tradingview_widget.load_chart(f"NASDAQ:{file_info['symbol']}")
                    
                    # Load the full HTML report in the report tab
                    self.report_view.load(QUrl.fromLocalFile(file_info['path']))
                    
                    # Update the report tab title to include the company name
                    report_tab_title = "Full Report"
                    if company_name:
                        report_tab_title = f"Full Report - {file_info['symbol']} ({company_name})"
                    self.tab_widget.setTabText(1, report_tab_title)
                      # Switch to the combined tab
                    self.tab_widget.setCurrentIndex(0)
          # Update external service tabs
        if self.current_file:
            self.update_external_tabs(symbol=self.current_file['symbol'])
    def update_external_tabs(self, symbol):
        """Update the external service tabs with the current symbol"""
        if symbol:
            # Load Finviz tab
            finviz_url = f"https://finviz.com/quote.ashx?t={symbol}"
            self.finviz_view.load(QUrl(finviz_url))
            
            # Load OpenInsider tab
            openinsider_url = f"http://openinsider.com/screener?s={symbol}"
            self.openinsider_view.load(QUrl(openinsider_url))
            
            # Load Yahoo Finance tab
            yahoo_url = f"https://finance.yahoo.com/quote/{symbol}"
            self.yahoo_view.load(QUrl(yahoo_url))
    
    def on_file_double_clicked(self, row, column):
        """Handle double-click on file in the list"""
        self.on_view_clicked()
        
    def on_view_clicked(self):
        """View selected report in a new tab"""
        if self.current_file and os.path.exists(self.current_file['path']):
            # Create a new web view for the tab
            web_view = QWebEngineView()
            web_view.load(QUrl.fromLocalFile(self.current_file['path']))
            
            # Add to tab widget
            tab_index = self.tab_widget.addTab(web_view, f"External View - {self.current_file['symbol']}")
            self.tab_widget.setCurrentIndex(tab_index)
            
            # Add a close button to the tab
            close_button = QPushButton("×")
            close_button.setFixedSize(20, 20)
            close_button.setStyleSheet("QPushButton { border: none; color: #777; } QPushButton:hover { color: #f00; }")
            close_button.clicked.connect(lambda: self.close_tab(tab_index))
            self.tab_widget.tabBar().setTabButton(tab_index, self.tab_widget.tabBar().RightSide, close_button)
    
    def on_save_clicked(self):
        """Save temporary file to permanent storage"""
        if self.current_file and self.current_file['temp']:
            new_path = self.file_manager.save_file(self.current_file['path'])
            if new_path:
                # Show temporary status message instead of modal dialog
                self.status_label.setText(f"Report saved to saved_data folder as {os.path.basename(new_path)}")
                
                # Auto-clear the message after 3 seconds
                QTimer.singleShot(3000, lambda: self.status_label.setText("Ready to collect stock data..."))
                
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
        
        # Use our integrated Unicode-safe thread instead of a separate script
        self.stock_thread = StockDataThread(symbol)
        self.stock_thread.output_received.connect(self.update_console)
        self.stock_thread.data_ready.connect(lambda success, err, filename: self.on_stock_data_ready(success, err, symbol, filename))
        self.stock_thread.start()
        
    def update_console(self, text):
        """Update console output with new text"""
        self.console_output.append(text)
        self.console_output.ensureCursorVisible()    
    def on_stock_data_ready(self, success, error, symbol, filename):
        """Handle completion of stock data generation"""
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
                    
        else:
            if "could not be found" in error:
                self.status_label.setText(f"Symbol {symbol} could not be found!")
                QMessageBox.critical(self, "Symbol Not Found", f"Symbol {symbol} could not be found in our data sources.")
            else:
                self.status_label.setText(f"Error collecting data for {symbol}!")
                QMessageBox.critical(self, "Error", f"Failed to generate data: {error}")    # Toggle theme method removed - always using light mode


def main():
    # Set environment variable for encoding
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    app = QApplication(sys.argv)
    
    # Create and show the window
    window = FinScanQt()
    
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
