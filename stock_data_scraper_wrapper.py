#!/usr/bin/env python3
"""
Stock Data Scraper Wrapper - Unicode-safe version
This script runs the stock_data_scraper.py with proper UTF-8 encoding to avoid errors on Windows
"""
import sys
import os
import subprocess
import tempfile
import time
import re
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("Usage: python stock_data_scraper_wrapper.py SYMBOL")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    
    # Set environment variables to ensure proper encoding
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Process start time for the file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Prepare command to call the original scraper but with ascii-only printable output
    cmd = f"python -c \"import stock_data_scraper; scraper = stock_data_scraper.StockDataScraper('{symbol}'); print('Collecting data for {symbol}...'); scraper.collect_all_data(); scraper.save_html('{symbol}_data_{timestamp}.html')\""
    
    # Run the command
    print(f"Starting data collection for {symbol}...")
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            shell=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Monitor output
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                # Replace any problematic Unicode characters
                safe_output = output.encode('ascii', 'replace').decode('ascii')
                print(safe_output.strip())
                
        # Check for errors
        stderr = process.stderr.read()
        if stderr:
            safe_stderr = stderr.encode('ascii', 'replace').decode('ascii')
            print(f"ERROR: {safe_stderr}")
            sys.exit(1)
            
        # Success!
        print(f"Data collection complete for {symbol}")
        print(f"Report saved to {symbol}_data_{timestamp}.html")
        
    except Exception as e:
        print(f"Error running stock data scraper: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
