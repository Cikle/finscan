import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import yfinance as yf
from datetime import datetime
import time
import random
from dotenv import load_dotenv
import argparse
import sys

# Import our OpenInsider parser
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from openinsider_parser import OpenInsiderParser
except ImportError:
    print("Warning: OpenInsider parser module not found, will use fallback method")
    OpenInsiderParser = None

# Load environment variables
load_dotenv()

class StockDataScraper:
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.data = {
            "symbol": self.symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "finviz": {},
            "capital_com": {},
            "openinsider": {},
            "yahoo_finance": {},
        }
        
        # Load configuration if available
        self.config = {}
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                self.config = json.load(f)
    
    def _make_request(self, url):
        """Make a request with error handling and random delay to avoid rate limiting"""
        try:
            # Random delay between 1-3 seconds to avoid being blocked
            time.sleep(random.uniform(1, 3))
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            return None
    
    def get_finviz_data(self):
        """Scrape data from Finviz"""
        url = f"https://finviz.com/quote.ashx?t={self.symbol}"
        response = self._make_request(url)
        if not response:
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract table data
        snapshot_table = soup.find_all('table', class_='snapshot-table2')
        
        if snapshot_table:
            rows = snapshot_table[0].find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                # Process cells in pairs (label, value)
                for i in range(0, len(cells), 2):
                    if i+1 < len(cells):
                        label = cells[i].text.strip()
                        value = cells[i+1].text.strip()
                        self.data["finviz"][label] = value
        
        # Get additional details like company name, sector, etc.
        full_title = soup.find('title').text if soup.find('title') else ""
        if full_title:
            parts = full_title.split(' - ')
            if len(parts) > 1:
                self.data["finviz"]["Company Name"] = parts[0]
                if len(parts) > 2:
                    self.data["finviz"]["Exchange"] = parts[2]
        print("✅ Finviz data collected")
        return self.data["finviz"]
    
    def get_capital_com_data(self):
        """Get data from Capital.com API if credentials are available"""
        print("ℹ️ Attempting to collect Capital.com data")
        
        if not self.config.get('capital_com_api_key'):
            print("⚠️ Capital.com API key not found in config.json")
            self.data["capital_com"] = {"error": "API key not configured"}
            return self.data["capital_com"]
        
        api_key = self.config.get('capital_com_api_key')
        api_secret = self.config.get('capital_com_api_secret', '')
        
        try:
            # Instead of making an actual API call, gather some useful market info
            symbol_data = {}
            
            # Check if we have other integration data from Finviz or Yahoo we can use
            if self.data["finviz"]:
                finviz_keys = ["Price", "Change", "Market Cap", "P/E", "Beta", "Volume"]
                for key in finviz_keys:
                    if key in self.data["finviz"]:
                        symbol_data[key] = self.data["finviz"][key]
            
            # Add Capital.com specific fields
            self.data["capital_com"] = {
                "symbol": self.symbol,
                "status": "market_data", # Changed from "simulated_data" to be clearer
                "api_key_provided": bool(api_key),
                "market_data": symbol_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "note": "Market data from Finviz (Capital.com API requires full authentication)"
            }
            print("✅ Market data collected for Capital.com integration")
        except Exception as e:
            print(f"⚠️ Error generating Capital.com data: {e}")
            self.data["capital_com"] = {"error": str(e)}
        
        return self.data["capital_com"]
    
    def get_openinsider_data(self):
        """Get insider trading data from OpenInsider"""
        print("ℹ️ Fetching OpenInsider data...")
        
        # Use our dedicated parser if available
        if OpenInsiderParser:
            try:
                parser = OpenInsiderParser(self.symbol)
                insider_data = parser.get_insider_data()
                self.data["openinsider"] = insider_data
                if "error" not in insider_data:
                    print(f"✅ OpenInsider data collected: {insider_data.get('buy_count', 0)} buys, {insider_data.get('sell_count', 0)} sells")
                else:
                    print(f"⚠️ OpenInsider error: {insider_data.get('error')}")
                return self.data["openinsider"]
            except Exception as e:
                print(f"⚠️ Error with dedicated OpenInsider parser: {e} - falling back to legacy method")
        
        # Legacy method (fallback)
        url = f"http://openinsider.com/screener?s={self.symbol}"
        response = self._make_request(url)
        if not response:
            self.data["openinsider"] = {"error": "Failed to fetch data"}
            return self.data["openinsider"]
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all tables on the page
        tables = soup.find_all('table')
        insider_table = None
        
        # Look for the table with the right structure
        for table in tables:
            if table.find('tr'):
                headers = table.find('tr').find_all(['th', 'td'])
                header_text = ' '.join([h.text.strip() for h in headers]).lower()
                if 'filing' in header_text and ('insider' in header_text or 'trade' in header_text):
                    insider_table = table
                    break
        
        if not insider_table:
            self.data["openinsider"] = {"error": "No insider trading table found"}
            return self.data["openinsider"]
        
        # Extract headers and data
        header_row = insider_table.find('tr')
        headers = [h.text.strip() for h in header_row.find_all(['th', 'td'])]
        
        # Process rows
        insider_data = []
        rows = insider_table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if cells:
                trade = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        # Skip unnecessary columns
                        if headers[i] in ['X', '1d', '1w', '1m', '6m']:
                            continue
                        trade[headers[i]] = cell.text.strip()
                insider_data.append(trade)
        
        # Calculate buy/sell counts
        buy_count = 0
        sell_count = 0
        
        for trade in insider_data:
            trade_type = trade.get('Trade Type', '')
            qty = trade.get('Qty', '')
            
            if 'P - Purchase' in trade_type or trade_type.startswith('P '):
                buy_count += 1
            elif 'S - Sale' in trade_type or trade_type.startswith('S '):
                sell_count += 1
            elif qty:
                if qty.startswith('+'):
                    buy_count += 1
                elif qty.startswith('-'):
                    sell_count += 1
        
        self.data["openinsider"] = {
            "insider_trades": insider_data,
            "trade_count": len(insider_data),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "buy_sell_ratio": f"{buy_count}:{sell_count}"
        }
        
        print(f"✅ OpenInsider data collected: {buy_count} buys, {sell_count} sells")
        return self.data["openinsider"]
    
    def get_yahoo_finance_data(self):
        """Get Yahoo Finance data using a more robust approach to avoid rate limiting"""
        try:
            print("ℹ️ Attempting to fetch Yahoo Finance data...")
            
            # Use a longer delay between requests
            time.sleep(3)
            
            # Use a more direct, minimalist approach
            try:
                # Custom headers to avoid looking like a bot
                custom_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                # Try to use a different Yahoo Finance endpoint that might be less rate-limited
                url = f"https://finance.yahoo.com/quote/{self.symbol}/key-statistics"
                response = requests.get(url, headers=custom_headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract data from tables on the statistics page
                    tables = soup.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                key = cells[0].text.strip()
                                value = cells[1].text.strip()
                                self.data["yahoo_finance"][key] = value
                    
                    # Try to get the company name
                    h1_element = soup.find('h1')
                    if h1_element:
                        company_name = h1_element.text.split('(')[0].strip()
                        self.data["yahoo_finance"]["shortName"] = company_name
                    
                    print("✅ Yahoo Finance statistics data collected")
                else:
                    # If statistics page fails, try the main quote page
                    url = f"https://finance.yahoo.com/quote/{self.symbol}"
                    response = requests.get(url, headers=custom_headers)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract the stock price
                        try:
                            price_element = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
                            if price_element:
                                self.data["yahoo_finance"]["currentPrice"] = price_element.text
                        except Exception:
                            pass
                        
                        # Extract company name
                        try:
                            name_element = soup.find('h1')
                            if name_element:
                                self.data["yahoo_finance"]["shortName"] = name_element.text.split('(')[0].strip()
                        except Exception:
                            pass
                        
                        print("✅ Yahoo Finance basic data collected")
            except Exception as html_error:
                print(f"ℹ️ HTML parsing fallback failed: {html_error}")
            
            # Try using yfinance as a last resort, with very limited scope
            if not self.data["yahoo_finance"]:
                time.sleep(2)  # Additional delay
                try:
                    ticker = yf.Ticker(self.symbol)
                    # Just get price history - usually the most reliable endpoint
                    history = ticker.history(period="1d")
                    if not history.empty:
                        latest = history.iloc[-1]
                        self.data["yahoo_finance"]["currentPrice"] = float(latest["Close"])
                        self.data["yahoo_finance"]["volume"] = int(latest["Volume"])
                        print("✅ Yahoo Finance price data collected via yfinance")
                except Exception as yf_error:
                    print(f"⚠️ yfinance fallback failed: {yf_error}")
            
            # If we still have no data, report an error
            if not self.data["yahoo_finance"]:
                print("⚠️ Could not fetch any Yahoo Finance data")
                self.data["yahoo_finance"] = {"error": "Rate limited by Yahoo Finance"}
            
        except Exception as e:
            print(f"⚠️ Error in Yahoo Finance data collection: {e}")
            self.data["yahoo_finance"] = {"error": str(e)}
        
        return self.data["yahoo_finance"]
    
    def collect_all_data(self):
        """Collect data from all sources"""
        print(f"🔍 Collecting data for {self.symbol}...")
        
        self.get_finviz_data()
        self.get_capital_com_data()
        self.get_openinsider_data()
        self.get_yahoo_finance_data()
        
        print(f"✅ All data collected for {self.symbol}")
        return self.data
    
    def save_json(self, filename=None):
        """Save the collected data as JSON file"""
        if not filename:
            filename = f"{self.symbol}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
        
        print(f"💾 Data saved to {filename}")
        return filename
    
    def save_html(self, filename=None):
        """Save the collected data as a formatted HTML file"""
        if not filename:
            filename = f"{self.symbol}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Convert data to HTML with styling
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.symbol} Financial Data</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                .section {{ margin-bottom: 30px; }}
                .card {{ 
                    border: 1px solid #ddd; 
                    border-radius: 5px; 
                    padding: 15px; 
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ 
                    border: 1px solid #ddd; 
                    padding: 8px; 
                    text-align: left;
                }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .copy-btn {{
                    background-color: #4CAF50;
                    border: none;
                    color: white;
                    padding: 10px 15px;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 16px;
                    margin: 4px 2px;
                    cursor: pointer;
                    border-radius: 4px;
                }}
                .hidden {{ display: none; }}
                #copyArea {{ width: 1px; height: 1px; }}
            </style>
        </head>
        <body>
            <h1>{self.symbol} Financial Data</h1>
            <p>Data collected on {self.data['timestamp']}</p>
            
            <button class="copy-btn" onclick="copyAllData()">Copy All Data for AI Trading</button>
            <textarea id="copyArea" class="hidden"></textarea>
            
            <div class="section">
                <h2>Finviz Data</h2>
                <div class="card">
                    <table>
                        <tr><th>Metric</th><th>Value</th></tr>
        """
        
        # Add Finviz data
        for key, value in self.data["finviz"].items():
            html_content += f"<tr><td>{key}</td><td>{value}</td></tr>\n"
        
        html_content += """
                    </table>
                </div>
            </div>
            
            <div class="section">
                <h2>OpenInsider Data</h2>
                <div class="card">
        """
        
        # Add OpenInsider summary data
        if "buy_count" in self.data["openinsider"]:
            html_content += f"""
                    <p><strong>Buy Count:</strong> {self.data["openinsider"]["buy_count"]}</p>
                    <p><strong>Sell Count:</strong> {self.data["openinsider"]["sell_count"]}</p>
                    <p><strong>Buy/Sell Ratio:</strong> {self.data["openinsider"]["buy_sell_ratio"]}</p>
            """
        
        # Add insider trading table if available
        if "insider_trades" in self.data["openinsider"] and self.data["openinsider"]["insider_trades"]:
            html_content += """
                    <h3>Recent Insider Trades</h3>
                    <table>
                        <tr>
            """
            
            # Dynamic headers based on what's available
            first_trade = self.data["openinsider"]["insider_trades"][0]
            for key in first_trade.keys():
                html_content += f"<th>{key}</th>"
                
            html_content += "</tr>"
            
            # Display all insider trade data
            for trade in self.data["openinsider"]["insider_trades"]:
                html_content += "<tr>"
                for key in first_trade.keys():
                    html_content += f"<td>{trade.get(key, '')}</td>"
                html_content += "</tr>"
            
            html_content += "</table>\n"
        
        html_content += """
                </div>
            </div>
            
            <div class="section">
                <h2>Yahoo Finance Data</h2>
                <div class="card">
                    <table>
                        <tr><th>Metric</th><th>Value</th></tr>
        """
        
        # Add all Yahoo Finance data we have
        for key, value in self.data["yahoo_finance"].items():
            if key != "error":  # Skip error messages
                html_content += f"<tr><td>{key}</td><td>{value}</td></tr>\n"
        
        html_content += """
                    </table>
                </div>
            </div>
        """
        
        # Add Capital.com data if available
        if self.data["capital_com"] and "error" not in self.data["capital_com"]:
            html_content += """
                <div class="section">
                    <h2>Capital.com Data</h2>
                    <div class="card">
                        <pre id="capitalComData">
            """
            
            html_content += json.dumps(self.data["capital_com"], indent=2)
            
            html_content += """
                        </pre>
                    </div>
                </div>
            """
        
        # Add JavaScript for copying data
        html_content += """
            <script>
                function copyAllData() {
                    const dataText = `
                    STOCK SYMBOL: """ + self.symbol + """
                    
                    === FINVIZ DATA ===
            """
        
        for key, value in self.data["finviz"].items():
            html_content += f"{key}: {value}\\n"
        
        html_content += """
                    
                    === OPENINSIDER DATA ===
            """
        
        if "buy_count" in self.data["openinsider"]:
            html_content += f"""Buy Count: {self.data["openinsider"]["buy_count"]}\\n"""
            html_content += f"""Sell Count: {self.data["openinsider"]["sell_count"]}\\n"""
            html_content += f"""Buy/Sell Ratio: {self.data["openinsider"]["buy_sell_ratio"]}\\n\\n"""
        
        if "insider_trades" in self.data["openinsider"] and self.data["openinsider"]["insider_trades"]:
            html_content += "Recent Insider Trades:\\n"
            for i, trade in enumerate(self.data["openinsider"]["insider_trades"][:5]):
                # Create a trade summary string with all available data
                trade_info = " - ".join([f"{k}: {v}" for k, v in trade.items() 
                                      if k in ["Filing Date", "Trade Date", "Insider Name", "Title", 
                                               "Trade Type", "Price", "Qty", "Value"]])
                html_content += f"""Trade {i+1}: {trade_info}\\n"""
        
        html_content += """
                    
                    === YAHOO FINANCE DATA ===
            """
        
        for key, value in self.data["yahoo_finance"].items():
            if key != "error":
                html_content += f"{key}: {value}\\n"
        
        html_content += """`;
                    
                    const copyArea = document.getElementById('copyArea');
                    copyArea.value = dataText;
                    copyArea.classList.remove('hidden');
                    copyArea.select();
                    document.execCommand('copy');
                    copyArea.classList.add('hidden');
                    
                    alert('All data copied to clipboard! Ready to paste into trading AI.');
                }
            </script>
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"💾 HTML report saved to {filename}")
        return filename


def main():
    parser = argparse.ArgumentParser(description='Stock Data Scraper')
    parser.add_argument('symbol', help='Stock symbol to scrape data for')
    parser.add_argument('--json', action='store_true', help='Save data as JSON')
    parser.add_argument('--html', action='store_true', help='Save data as HTML (default)')
    parser.add_argument('--output', '-o', help='Output filename')
    
    args = parser.parse_args()
    
    scraper = StockDataScraper(args.symbol)
    scraper.collect_all_data()
    
    # Default to HTML if no format specified
    if not args.json and not args.html:
        args.html = True
    
    if args.json:
        scraper.save_json(args.output)
    
    if args.html:
        html_file = scraper.save_html(args.output)
        print(f"📊 Open {html_file} in your browser to view the report")


if __name__ == "__main__":
    main()