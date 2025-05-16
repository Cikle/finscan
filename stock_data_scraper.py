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
        """Get Yahoo Finance data using multiple fallback strategies to avoid rate limiting"""
        try:
            print("ℹ️ Attempting to fetch Yahoo Finance data...")
            
            # STRATEGY 1: Use yfinance library directly first - it's more reliable
            try:
                time.sleep(1)
                print("📊 Trying yfinance library...")
                
                ticker = yf.Ticker(self.symbol)
                
                # Basic info - usually works even when rate limited
                try:
                    info = ticker.fast_info
                    if hasattr(info, 'last_price') and info.last_price is not None:
                        self.data["yahoo_finance"]["currentPrice"] = round(info.last_price, 2)
                    if hasattr(info, 'day_volume') and info.day_volume is not None:
                        self.data["yahoo_finance"]["volume"] = info.day_volume
                    if hasattr(info, 'market_cap') and info.market_cap is not None:
                        self.data["yahoo_finance"]["marketCap"] = info.market_cap
                except Exception:
                    pass
                
                # Try getting the company info - may fail when rate limited
                try:
                    # This might fetch basic data like company name, sector, etc.
                    time.sleep(1)  # Extra delay before info request
                    company_info = ticker.info
                    
                    # Extract the most useful fields
                    key_fields = [
                        'shortName', 'longName', 'sector', 'industry', 'website', 
                        'marketCap', 'forwardPE', 'trailingPE', 'beta',
                        'dividendYield', 'fiftyTwoWeekLow', 'fiftyTwoWeekHigh'
                    ]
                    
                    for field in key_fields:
                        if field in company_info and company_info[field] is not None:
                            self.data["yahoo_finance"][field] = company_info[field]
                except Exception as e:
                    print(f"ℹ️ Full company info not available: {e}")
                
                # Try getting just basic price data as a last resort
                if not self.data["yahoo_finance"]:
                    time.sleep(1)
                    hist = ticker.history(period="2d")
                    if not hist.empty:
                        last_row = hist.iloc[-1]
                        self.data["yahoo_finance"]["currentPrice"] = round(float(last_row["Close"]), 2)
                        self.data["yahoo_finance"]["previousClose"] = round(float(hist.iloc[-2]["Close"]), 2)
                
                if self.data["yahoo_finance"]:
                    print("✅ Yahoo Finance data collected via yfinance library")
            except Exception as e:
                print(f"⚠️ yfinance approach failed: {e}")
            
            # STRATEGY 2: If yfinance failed, try direct HTML scraping with browser-like headers
            if not self.data["yahoo_finance"]:
                time.sleep(2)  # Wait before trying direct HTML
                try:
                    print("🌐 Trying direct HTML scraping...")
                    # More browser-like headers to avoid detection
                    custom_headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Cache-Control': 'max-age=0',
                        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"Windows"',
                    }
                    
                    # Try a different Yahoo Finance URL that might be less protected
                    url = f"https://finance.yahoo.com/quote/{self.symbol}/profile"
                    response = requests.get(url, headers=custom_headers)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Try to extract company name, sector, industry
                        h1_tags = soup.find_all('h1')
                        for h1 in h1_tags:
                            if self.symbol.lower() in h1.text.lower():
                                self.data["yahoo_finance"]["shortName"] = h1.text.split('(')[0].strip()
                                break
                        
                        # Look for sector and industry info
                        spans = soup.find_all('span')
                        for i, span in enumerate(spans):
                            if span.text.strip() == "Sector":
                                if i + 1 < len(spans):
                                    self.data["yahoo_finance"]["sector"] = spans[i+1].text.strip()
                            if span.text.strip() == "Industry":
                                if i + 1 < len(spans):
                                    self.data["yahoo_finance"]["industry"] = spans[i+1].text.strip()
                            if span.text.strip() == "Full Time Employees":
                                if i + 1 < len(spans):
                                    self.data["yahoo_finance"]["employees"] = spans[i+1].text.strip()
                        
                        if self.data["yahoo_finance"]:
                            print("✅ Yahoo Finance profile data collected via HTML")
                except Exception as html_error:
                    print(f"⚠️ HTML scraping failed: {html_error}")
            
            # STRATEGY 3: Fall back to alternative URL if needed
            if not self.data["yahoo_finance"]:
                time.sleep(2)
                try:
                    print("🔄 Trying alternative Yahoo Finance URL...")
                    url = f"https://finance.yahoo.com/quote/{self.symbol}/key-statistics" 
                    response = requests.get(url, headers=custom_headers)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Try to extract data from tables
                        tables = soup.find_all('table')
                        for table in tables:
                            for row in table.find_all('tr'):
                                cells = row.find_all('td')
                                if len(cells) >= 2:
                                    label = cells[0].text.strip()
                                    value = cells[1].text.strip()
                                    self.data["yahoo_finance"][label] = value
                except Exception:
                    pass
            
            # FALLBACK: If nothing else worked, at least get basic info from Finviz
            if not self.data["yahoo_finance"]:
                print("⚠️ Using Finviz data as fallback for Yahoo Finance")
                # Copy some basic data from Finviz
                finviz_mapping = {
                    "Price": "currentPrice",
                    "Change": "priceChange", 
                    "Market Cap": "marketCap",
                    "P/E": "trailingPE",
                    "Forward P/E": "forwardPE",
                    "Beta": "beta",
                    "Volume": "volume",
                }
                
                for finviz_key, yahoo_key in finviz_mapping.items():
                    if finviz_key in self.data["finviz"]:
                        self.data["yahoo_finance"][yahoo_key] = self.data["finviz"][finviz_key]
                
                self.data["yahoo_finance"]["source"] = "Data from Finviz (Yahoo Finance unavailable)"
            
            # If still no data after all attempts
            if not self.data["yahoo_finance"]:
                print("⚠️ All Yahoo Finance data collection methods failed")
                self.data["yahoo_finance"] = {"error": "Rate limited by Yahoo Finance"}
            
        except Exception as e:
            print(f"⚠️ Error in Yahoo Finance data collection: {e}")
            self.data["yahoo_finance"] = {"error": str(e)}
        
        return self.data["yahoo_finance"]
    
    def get_analyst_recommendations(self):
        """Get analyst recommendations and price targets"""
        print("ℹ️ Fetching analyst recommendations...")
        self.data["analyst_recommendations"] = {}
        
        try:
            # Try to get analyst data from Finviz first
            if "Recom" in self.data["finviz"]:
                self.data["analyst_recommendations"]["consensus"] = self.data["finviz"]["Recom"]
            
            if "Target Price" in self.data["finviz"]:
                self.data["analyst_recommendations"]["price_target"] = self.data["finviz"]["Target Price"]
            
            # Try to get more detailed data from Yahoo Finance
            if yf is not None:
                try:
                    ticker = yf.Ticker(self.symbol)
                    recommendations = ticker.recommendations
                    if recommendations is not None and not recommendations.empty:
                        # Get the most recent recommendations
                        recent_recs = recommendations.sort_index(ascending=False).head(5)
                        rec_dict = {}
                        for date, row in recent_recs.iterrows():
                            firm = row.get('Firm', '')
                            to_grade = row.get('To Grade', '')
                            rec_dict[str(date).split()[0]] = f"{firm}: {to_grade}"
                        self.data["analyst_recommendations"]["recent"] = rec_dict
                except Exception as e:
                    print(f"⚠️ Could not fetch detailed analyst recommendations: {e}")
            
            print("✅ Analyst recommendation data collected")
        except Exception as e:
            print(f"⚠️ Error collecting analyst recommendations: {e}")
            self.data["analyst_recommendations"] = {"error": str(e)}
        
        return self.data["analyst_recommendations"]
    
    def get_financial_summary(self):
        """Get summary financial data"""
        print("ℹ️ Fetching financial summary data...")
        self.data["financial_summary"] = {}
        
        try:
            # Extract data from Finviz
            finviz_financials = {
                "profit_margin": self.data["finviz"].get("Profit Margin", ""),
                "operating_margin": self.data["finviz"].get("Oper. Margin", ""),
                "return_on_assets": self.data["finviz"].get("ROA", ""),
                "return_on_equity": self.data["finviz"].get("ROE", ""),
                "revenue": self.data["finviz"].get("Sales", ""),
                "revenue_growth": self.data["finviz"].get("Sales Y/Y TTM", ""),
                "quarterly_revenue_growth": self.data["finviz"].get("Sales Q/Q", ""),
                "gross_profit_margin": self.data["finviz"].get("Gross Margin", ""),
                "diluted_eps": self.data["finviz"].get("EPS (ttm)", ""),
                "earnings_growth": self.data["finviz"].get("EPS Y/Y TTM", ""),
                "quarterly_earnings_growth": self.data["finviz"].get("EPS Q/Q", "")
            }
            
            self.data["financial_summary"]["income_statement"] = finviz_financials
            
            # Balance sheet data from Finviz
            finviz_balance_sheet = {
                "cash_per_share": self.data["finviz"].get("Cash/sh", ""),
                "book_value_per_share": self.data["finviz"].get("Book/sh", ""),
                "debt_to_equity": self.data["finviz"].get("Debt/Eq", ""),
                "long_term_debt_to_equity": self.data["finviz"].get("LT Debt/Eq", ""),
                "current_ratio": self.data["finviz"].get("Current Ratio", ""),
                "quick_ratio": self.data["finviz"].get("Quick Ratio", "")
            }
            
            self.data["financial_summary"]["balance_sheet"] = finviz_balance_sheet
            
            # Try to get more from Yahoo Finance if available
            try:
                if "beta" in self.data["yahoo_finance"]:
                    self.data["financial_summary"]["beta"] = self.data["yahoo_finance"]["beta"]
            except:
                pass
            
            print("✅ Financial summary data collected")
        except Exception as e:
            print(f"⚠️ Error collecting financial summary: {e}")
            self.data["financial_summary"] = {"error": str(e)}
        
        return self.data["financial_summary"]
    
    def get_competitors(self):
        """Get competitors analysis"""
        print("ℹ️ Fetching competitors data...")
        self.data["competitors"] = {}
        
        try:
            # Use the sector and industry from Yahoo Finance to get peers
            sector = self.data["yahoo_finance"].get("sector", "")
            industry = self.data["yahoo_finance"].get("industry", "")
            
            if sector and industry:
                self.data["competitors"]["sector"] = sector
                self.data["competitors"]["industry"] = industry
                
                # Use Finviz data for industry analysis if we have it
                if "Sector" in self.data["finviz"]:
                    self.data["competitors"]["finviz_sector"] = self.data["finviz"].get("Sector", "")
                
                if "Industry" in self.data["finviz"]:
                    self.data["competitors"]["finviz_industry"] = self.data["finviz"].get("Industry", "")
                
                # Add competitor comparison data
                self.data["competitors"]["comparison"] = {
                    "this_company": {
                        "symbol": self.symbol,
                        "market_cap": self.data["finviz"].get("Market Cap", ""),
                        "pe_ratio": self.data["finviz"].get("P/E", ""),
                        "forward_pe": self.data["finviz"].get("Forward P/E", ""),
                        "ps_ratio": self.data["finviz"].get("P/S", ""),
                        "pb_ratio": self.data["finviz"].get("P/B", "")
                    }
                }
                
                print("✅ Competitors analysis collected")
            else:
                self.data["competitors"] = {
                    "note": "No sector/industry data available to identify competitors"
                }
        except Exception as e:
            print(f"⚠️ Error collecting competitors data: {e}")
            self.data["competitors"] = {"error": str(e)}
        
        return self.data["competitors"]
    
    def collect_all_data(self):
        """Collect data from all sources"""
        print(f"🔍 Collecting data for {self.symbol}...")
        
        self.get_finviz_data()
        self.get_capital_com_data()
        self.get_openinsider_data()
        self.get_yahoo_finance_data()
        
        # Add our new data collection methods
        self.get_analyst_recommendations()
        self.get_financial_summary()
        self.get_competitors()
        
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
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
                .chart-container {{ 
                    position: relative; 
                    height: 250px;
                    margin-bottom: 20px; 
                }}
                .stat-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 15px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background-color: #f9f9f9;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 24px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .stat-label {{
                    color: #666;
                    font-size: 14px;
                }}
                .trend-positive {{
                    color: #4CAF50;
                }}
                .trend-negative {{
                    color: #f44336;
                }}
                .trend-neutral {{
                    color: #9e9e9e;
                }}
                .gauge-container {{
                    position: relative;
                    margin: 20px 0;
                    text-align: center;
                }}
                .gauge {{
                    width: 100%;
                    max-width: 200px;
                    margin: 0 auto;
                }}
                .rating {{
                    text-align: center;
                    font-size: 18px;
                    margin: 10px 0;
                    font-weight: bold;
                }}
                .rating-strong {{
                    color: #2e7d32;
                }}
                .rating-good {{
                    color: #4CAF50;
                }}
                .rating-neutral {{
                    color: #9e9e9e;
                }}
                .rating-warning {{
                    color: #f9a825;
                }}
                .rating-poor {{
                    color: #f44336;
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                }}
                @media (max-width: 768px) {{
                    .stat-grid {{
                        grid-template-columns: repeat(2, 1fr);
                    }}
                    .metrics-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <h1>{self.symbol} Financial Data</h1>
            <p>Data collected on {self.data['timestamp']}</p>
            
            <button class="copy-btn" onclick="copyAllData()">Copy All Data for AI Trading</button>
            <textarea id="copyArea" class="hidden"></textarea>
            
            <div class="section">
                <h2>Key Statistics Dashboard</h2>
                <div class="card">
                    <div class="stat-grid">
                        <!-- Market Cap -->
                        <div class="stat-card">
                            <div class="stat-label">Market Cap</div>
                            <div class="stat-value" id="marketCap">-</div>
                        </div>
                        
                        <!-- P/E Ratio -->
                        <div class="stat-card">
                            <div class="stat-label">P/E Ratio</div>
                            <div class="stat-value" id="peRatio">-</div>
                        </div>
                        
                        <!-- Stock Price -->
                        <div class="stat-card">
                            <div class="stat-label">Current Price</div>
                            <div class="stat-value" id="stockPrice">-</div>
                        </div>
                        
                        <!-- Change -->
                        <div class="stat-card">
                            <div class="stat-label">Daily Change</div>
                            <div class="stat-value" id="priceChange">-</div>
                        </div>
                        
                        <!-- Volume -->
                        <div class="stat-card">
                            <div class="stat-label">Volume</div>
                            <div class="stat-value" id="volume">-</div>
                        </div>
                        
                        <!-- Beta -->
                        <div class="stat-card">
                            <div class="stat-label">Beta</div>
                            <div class="stat-value" id="beta">-</div>
                        </div>
                    </div>
                      <div class="metrics-grid">
                        <!-- Performance Chart -->
                        <div>
                            <h3>Performance Metrics</h3>
                            <div class="chart-container">
                                <canvas id="performanceChart"></canvas>
                            </div>
                        </div>
                        
                        <!-- Valuation Gauge -->
                        <div>
                            <h3>Analyst Recommendations</h3>
                            <div class="gauge-container">
                                <div class="gauge">
                                    <canvas id="recommendationGauge"></canvas>
                                </div>
                                <div class="rating" id="recommendationRating">-</div>
                            </div>
                        </div>
                        
                        <!-- Insider Trading Chart -->
                        <div>
                            <h3>Insider Trading by Quarter</h3>
                            <div class="chart-container">
                                <canvas id="insiderQuarterlyChart"></canvas>
                                <div style="text-align: center; margin-top: 10px; font-size: 12px; color: #666;">
                                    Q1: Jan-Mar | Q2: Apr-Jun | Q3: Jul-Sep | Q4: Oct-Dec
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
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
        
        # Add Analyst Recommendations if available
        if "analyst_recommendations" in self.data and self.data["analyst_recommendations"]:
            html_content += """
                <div class="section">
                    <h2>Analyst Recommendations</h2>
                    <div class="card">
                        <table>
                            <tr><th>Metric</th><th>Value</th></tr>
            """
            
            for key, value in self.data["analyst_recommendations"].items():
                if key == "recent" and isinstance(value, dict):
                    html_content += f"<tr><td colspan='2'><strong>Recent Recommendations</strong></td></tr>"
                    for date, rec in value.items():
                        html_content += f"<tr><td>{date}</td><td>{rec}</td></tr>"
                elif key != "error":
                    html_content += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
            
            html_content += """
                        </table>
                    </div>
                </div>
            """
        
        # Add Financial Summary if available
        if "financial_summary" in self.data and self.data["financial_summary"]:
            html_content += """
                <div class="section">
                    <h2>Financial Summary</h2>
                    <div class="card">
            """
            
            # Income Statement data
            if "income_statement" in self.data["financial_summary"]:
                html_content += """
                        <h3>Income Statement Metrics</h3>
                        <table>
                            <tr><th>Metric</th><th>Value</th></tr>
                """
                
                for key, value in self.data["financial_summary"]["income_statement"].items():
                    if value:  # Only show metrics that have values
                        html_content += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
                
                html_content += """
                        </table>
                        <br>
                """
            
            # Balance Sheet data
            if "balance_sheet" in self.data["financial_summary"]:
                html_content += """
                        <h3>Balance Sheet Metrics</h3>
                        <table>
                            <tr><th>Metric</th><th>Value</th></tr>
                """
                
                for key, value in self.data["financial_summary"]["balance_sheet"].items():
                    if value:  # Only show metrics that have values
                        html_content += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
                
                html_content += """
                        </table>
                """
            
            html_content += """
                    </div>
                </div>
            """
        
        # Add Competitors Analysis if available
        if "competitors" in self.data and self.data["competitors"]:
            html_content += """
                <div class="section">
                    <h2>Industry & Competitors</h2>
                    <div class="card">
            """
            
            # Sector and Industry info
            if "sector" in self.data["competitors"] or "industry" in self.data["competitors"]:
                html_content += """
                        <h3>Sector & Industry</h3>
                        <table>
                            <tr><th>Category</th><th>Classification</th></tr>
                """
                
                if "sector" in self.data["competitors"]:
                    html_content += f"<tr><td>Sector</td><td>{self.data['competitors']['sector']}</td></tr>"
                
                if "industry" in self.data["competitors"]:
                    html_content += f"<tr><td>Industry</td><td>{self.data['competitors']['industry']}</td></tr>"
                
                html_content += """
                        </table>
                        <br>
                """
            
            # Comparison data
            if "comparison" in self.data["competitors"] and "this_company" in self.data["competitors"]["comparison"]:
                html_content += """
                        <h3>Valuation Metrics</h3>
                        <table>
                            <tr><th>Metric</th><th>Value</th></tr>
                """
                
                for key, value in self.data["competitors"]["comparison"]["this_company"].items():
                    if key != "symbol" and value:
                        html_content += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
                
                html_content += """
                        </table>
                """
            
            html_content += """
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
        
        # Add Analyst Recommendations to the copy text
        if "analyst_recommendations" in self.data and self.data["analyst_recommendations"]:
            html_content += """
                    
                    === ANALYST RECOMMENDATIONS ===
            """
            
            for key, value in self.data["analyst_recommendations"].items():
                if key == "recent" and isinstance(value, dict):
                    html_content += f"Recent Recommendations:\\n"
                    for date, rec in value.items():
                        html_content += f"  {date}: {rec}\\n"
                elif key != "error":
                    html_content += f"{key.replace('_', ' ').title()}: {value}\\n"
        
        # Add Financial Summary to the copy text
        if "financial_summary" in self.data and self.data["financial_summary"]:
            html_content += """
                    
                    === FINANCIAL SUMMARY ===
            """
            
            # Income Statement data
            if "income_statement" in self.data["financial_summary"]:
                html_content += "Income Statement Metrics:\\n"
                for key, value in self.data["financial_summary"]["income_statement"].items():
                    if value:
                        html_content += f"  {key.replace('_', ' ').title()}: {value}\\n"
            
            # Balance Sheet data
            if "balance_sheet" in self.data["financial_summary"]:
                html_content += "\\nBalance Sheet Metrics:\\n"
                for key, value in self.data["financial_summary"]["balance_sheet"].items():
                    if value:
                        html_content += f"  {key.replace('_', ' ').title()}: {value}\\n"
        
        # Add Competitors Analysis to the copy text
        if "competitors" in self.data and self.data["competitors"]:
            html_content += """
                    
                    === INDUSTRY & COMPETITORS ===
            """
            
            if "sector" in self.data["competitors"]:
                html_content += f"Sector: {self.data['competitors']['sector']}\\n"
            
            if "industry" in self.data["competitors"]:
                html_content += f"Industry: {self.data['competitors']['industry']}\\n"
            
            # Comparison data        if "comparison" in self.data["competitors"] and "this_company" in self.data["competitors"]["comparison"]:
            html_content += "\\nValuation Metrics:\\n"
            for key, value in self.data["competitors"]["comparison"]["this_company"].items():
                if key != "symbol" and value:
                    html_content += f"  {key.replace('_', ' ').title()}: {value}\\n"
        
        # Add Capital.com data to the copy text
        if self.data["capital_com"] and "error" not in self.data["capital_com"]:
            html_content += """
                    
                    === CAPITAL.COM DATA ===
            """
            
            # Format the capital.com data nicely for the text copy
            capital_data = self.data["capital_com"]
            
            # Add the main Capital.com fields
            html_content += f"Symbol: {capital_data.get('symbol', '')}\\n"
            html_content += f"Status: {capital_data.get('status', '')}\\n"
            html_content += f"Timestamp: {capital_data.get('timestamp', '')}\\n"
            
            # Add market_data if available
            if "market_data" in capital_data and isinstance(capital_data["market_data"], dict):
                html_content += "\\nMarket Data:\\n"
                for key, value in capital_data["market_data"].items():
                    html_content += f"  {key}: {value}\\n"
            
            # Add any notes
            if "note" in capital_data:
                html_content += f"\\nNote: {capital_data['note']}\\n"
            
            html_content += """`;
                    
                    const copyArea = document.getElementById('copyArea');
                    copyArea.value = dataText;
                    copyArea.classList.remove('hidden');
                    copyArea.select();
                    document.execCommand('copy');
                    copyArea.classList.add('hidden');
                    
                    alert('All data copied to clipboard! Ready to paste into trading AI.');
                }
                
                // Function to populate the dashboard with data
                function populateDashboard() {
                    // Get all the stock data from our tables
                    const stockData = {};                    // Parse Finviz data table - this is where most of our key metrics are
                    // Get all sections and find the one with Finviz Data
                    const sections = document.querySelectorAll('.section');
                    let finvizTable = null;
                    
                    for (const section of sections) {
                        const heading = section.querySelector('h2');
                        if (heading && heading.textContent.includes('Finviz Data')) {
                            finvizTable = section.querySelector('table');
                            break;
                        }
                    }
                    
                    if (finvizTable) {
                        const rows = finvizTable.querySelectorAll('tr');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                const key = cells[0].textContent.trim();
                                const value = cells[1].textContent.trim();
                                stockData[key] = value;
                                console.log(`Found Finviz data: ${key} = ${value}`);
                            }
                        });
                    }

                    // Parse Yahoo Finance data table
                    const yahooTable = document.querySelector('.section:nth-of-type(4) table');
                    if (yahooTable) {
                        const rows = yahooTable.querySelectorAll('tr');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                const key = cells[0].textContent.trim();
                                const value = cells[1].textContent.trim();
                                stockData[key] = value;
                            }
                        });
                    }
                    
                    // Populate key statistics
                    const elements = {
                        'marketCap': ['Market Cap', 'marketCap'],
                        'peRatio': ['P/E', 'trailingPE', 'P/E Ratio'],
                        'stockPrice': ['Price', 'currentPrice', 'Last Price'],
                        'priceChange': ['Change', 'priceChange'],
                        'volume': ['Volume', 'volume', 'Volume'],
                        'beta': ['Beta', 'beta']
                    };
                    
                    // Try to find each metric in our collected data
                    for (const [elementId, possibleKeys] of Object.entries(elements)) {
                        const element = document.getElementById(elementId);
                        if (element) {
                            for (const key of possibleKeys) {
                                if (stockData[key]) {
                                    element.textContent = stockData[key];
                                    
                                    // Special formatting for some fields
                                    if (elementId === 'priceChange' && stockData[key]) {
                                        const change = parseFloat(stockData[key]);
                                        if (!isNaN(change)) {
                                            if (change > 0) {
                                                element.classList.add('trend-positive');
                                                element.textContent = '+' + stockData[key];
                                            } else if (change < 0) {
                                                element.classList.add('trend-negative');
                                            }
                                        }
                                    }
                                    break;
                                }
                            }
                        }
                    }
                      // Create the performance chart
                    const performanceLabels = ['Week', 'Month', 'Quarter', 'Half Year', 'Year', 'YTD'];
                    const performanceData = [];
                    const performanceKeys = ['Perf Week', 'Perf Month', 'Perf Quarter', 'Perf Half Y', 'Perf Year', 'Perf YTD'];
                    
                    // Collect performance data
                    for (const key of performanceKeys) {
                        if (stockData[key]) {
                            // Extract percentage value, removing % sign
                            const valueStr = stockData[key].replace('%', '');
                            const value = parseFloat(valueStr);
                            performanceData.push(isNaN(value) ? 0 : value);
                            console.log(`Found performance data: ${key} = ${value}`);
                        } else {
                            performanceData.push(0);
                            console.log(`No data found for ${key}`);
                        }
                    }
                    
                    // Create performance chart
                    if (document.getElementById('performanceChart')) {
                        const ctx = document.getElementById('performanceChart').getContext('2d');
                        new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: performanceLabels,
                                datasets: [{
                                    label: 'Performance (%)',
                                    data: performanceData,
                                    backgroundColor: performanceData.map(value => 
                                        value > 0 ? 'rgba(76, 175, 80, 0.6)' : 'rgba(244, 67, 54, 0.6)'
                                    ),
                                    borderColor: performanceData.map(value => 
                                        value > 0 ? 'rgba(76, 175, 80, 1)' : 'rgba(244, 67, 54, 1)'
                                    ),
                                    borderWidth: 1
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Performance (%)'
                                        },
                                        ticks: {
                                            callback: function(value) {
                                                return value + '%';
                                            }
                                        }
                                    }
                                }
                            }
                        });
                    }
                    
                    // Create analyst recommendation gauge
                    const recommendationElement = document.getElementById('recommendationRating');
                    let recommendationValue = 3; // Default neutral
                    let recommendationText = 'Hold';
                    
                    if (stockData['Recom']) {
                        recommendationValue = parseFloat(stockData['Recom']);
                        
                        // Set the text and color based on the value
                        if (recommendationValue <= 1.5) {
                            recommendationText = 'Strong Buy';
                            recommendationElement.className = 'rating rating-strong';
                        } else if (recommendationValue <= 2.5) {
                            recommendationText = 'Buy';
                            recommendationElement.className = 'rating rating-good';
                        } else if (recommendationValue <= 3.5) {
                            recommendationText = 'Hold';
                            recommendationElement.className = 'rating rating-neutral';
                        } else if (recommendationValue <= 4.5) {
                            recommendationText = 'Sell';
                            recommendationElement.className = 'rating rating-warning';
                        } else {
                            recommendationText = 'Strong Sell';
                            recommendationElement.className = 'rating rating-poor';
                        }
                        
                        recommendationElement.textContent = `${recommendationText} (${recommendationValue})`;
                    }
                    
                    // Create the recommendation gauge chart
                    if (document.getElementById('recommendationGauge')) {
                        const ctx = document.getElementById('recommendationGauge').getContext('2d');
                        
                        new Chart(ctx, {
                            type: 'doughnut',
                            data: {
                                datasets: [{
                                    data: [recommendationValue, 5 - recommendationValue],
                                    backgroundColor: [
                                        recommendationValue <= 1.5 ? '#2e7d32' : 
                                        recommendationValue <= 2.5 ? '#4CAF50' : 
                                        recommendationValue <= 3.5 ? '#9e9e9e' : 
                                        recommendationValue <= 4.5 ? '#f9a825' : '#f44336',
                                        'rgba(220, 220, 220, 0.5)'
                                    ],
                                    borderWidth: 0
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                cutout: '70%',
                                plugins: {
                                    tooltip: {
                                        enabled: false
                                    },
                                    legend: {
                                        display: false
                                    }
                                }
                            }
                        });                    }
                    
                    // Create the quarterly insider trading chart
                    if (document.getElementById('insiderQuarterlyChart')) {
                        // Find the OpenInsider section to extract data
                        let insiderTrades = [];
                        
                        for (const section of sections) {
                            const heading = section.querySelector('h2');
                            if (heading && heading.textContent.includes('OpenInsider Data')) {
                                const table = section.querySelector('table');
                                if (table) {
                                    // Find column indexes for trade date and trade type
                                    const headerRow = table.querySelector('tr');
                                    if (!headerRow) continue;
                                    
                                    const headers = headerRow.querySelectorAll('th');
                                    let dateColIndex = -1;
                                    let typeColIndex = -1;
                                    
                                    for (let i = 0; i < headers.length; i++) {
                                        const header = headers[i].textContent.trim();
                                        if (header === 'Trade Date' || header === 'Filing Date') {
                                            dateColIndex = i;
                                        }
                                        if (header === 'Trade Type') {
                                            typeColIndex = i;
                                        }
                                    }
                                    
                                    if (dateColIndex >= 0) {
                                        // Process all rows
                                        const rows = table.querySelectorAll('tr');
                                        for (let i = 1; i < rows.length; i++) { // Skip header
                                            const cells = rows[i].querySelectorAll('td');
                                            if (cells.length > Math.max(dateColIndex, typeColIndex)) {
                                                const dateStr = cells[dateColIndex].textContent.trim();
                                                const date = new Date(dateStr);
                                                
                                                if (!isNaN(date.getTime())) {
                                                    let isBuy = false;
                                                    
                                                    // Determine if buy or sell
                                                    if (typeColIndex >= 0) {
                                                        const typeStr = cells[typeColIndex].textContent.trim();
                                                        isBuy = typeStr.includes('P - Purchase') || typeStr.startsWith('P ');
                                                    }
                                                    
                                                    insiderTrades.push({
                                                        date: date,
                                                        isBuy: isBuy
                                                    });
                                                }
                                            }
                                        }
                                    }
                                }
                                break;
                            }
                        }
                          // Get the last 4 quarters
                        const now = new Date();
                        const currentQuarter = Math.floor(now.getMonth() / 3) + 1;
                        const currentYear = now.getFullYear();
                        
                        // Create labels for the last 4 quarters
                        const quarterLabels = [];
                        const quarterlyData = {};
                        
                        for (let i = 0; i < 4; i++) {
                            // Calculate quarter and year (going backward from current quarter)
                            let quarter = currentQuarter - i;
                            let year = currentYear;
                            
                            // Handle negative quarters by moving to previous year
                            if (quarter <= 0) {
                                quarter += 4;
                                year -= 1;
                            }
                            
                            // Create label with year for clarity
                            const label = `Q${quarter} ${year}`;
                            quarterLabels.unshift(label); // Add to front to maintain chronological order
                            quarterlyData[label] = { buys: 0, sells: 0 };
                        }
                        
                        // Process trades for the last 4 quarters
                        for (const trade of insiderTrades) {
                            const tradeYear = trade.date.getFullYear();
                            const tradeQuarter = Math.floor(trade.date.getMonth() / 3) + 1;
                            
                            // Check if the trade falls within our 4-quarter window
                            for (const label of quarterLabels) {
                                const [q, y] = label.split(' ');
                                const quarterNum = parseInt(q.substring(1));
                                const year = parseInt(y);
                                
                                if (tradeYear === year && tradeQuarter === quarterNum) {
                                    if (trade.isBuy) {
                                        quarterlyData[label].buys++;
                                    } else {
                                        quarterlyData[label].sells++;
                                    }
                                    break;
                                }
                            }
                        }
                          // Prepare data for chart
                        const labels = quarterLabels; // Use our ordered labels
                        const buyData = labels.map(q => quarterlyData[q].buys);
                        const sellData = labels.map(q => quarterlyData[q].sells);
                        
                        // Create the quarterly chart
                        const ctx = document.getElementById('insiderQuarterlyChart').getContext('2d');
                        new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: labels,
                                datasets: [
                                    {
                                        label: 'Buys',
                                        data: buyData,
                                        backgroundColor: 'rgba(76, 175, 80, 0.7)',
                                        borderColor: 'rgba(76, 175, 80, 1)',
                                        borderWidth: 1
                                    },
                                    {
                                        label: 'Sells',
                                        data: sellData,
                                        backgroundColor: 'rgba(244, 67, 54, 0.7)',
                                        borderColor: 'rgba(244, 67, 54, 1)',
                                        borderWidth: 1
                                    }
                                ]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        title: {
                                            display: true,
                                            text: 'Number of Transactions'
                                        },
                                        ticks: {
                                            stepSize: 1
                                        }
                                    }
                                },
                                plugins: {
                                    title: {
                                        display: true,
                                        text: 'Insider Activity - Last 4 Quarters'
                                    },                                    tooltip: {
                                        callbacks: {
                                            title: function(tooltipItems) {
                                                return tooltipItems[0].label; // Label already includes year
                                            },
                                            label: function(context) {
                                                const value = context.raw;
                                                const label = context.dataset.label;
                                                return `${label}: ${value} transactions`;
                                            }
                                        }
                                    }
                                }
                            }
                        });
                    }
                }
                
                // Run the dashboard population when the page loads
                document.addEventListener('DOMContentLoaded', populateDashboard);
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