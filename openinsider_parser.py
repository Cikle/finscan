"""
OpenInsider Parser - Module for parsing insider trading data for FinScan Qt

Copyright (c) 2025 Cyril Lutziger
License: MIT (see LICENSE file for details)
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import random

class OpenInsiderParser:
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
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
    
    def get_insider_data(self):
        """Fetch insider trading data for a symbol"""
        url = f"http://openinsider.com/screener?s={self.symbol}&o=&pl=&ph=&ll=&lh=&fd=730&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"
        response = self._make_request(url)
        if not response:
            return {"error": "Failed to fetch data"}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        insider_data = {"insider_trades": [], "buy_count": 0, "sell_count": 0}
        
        # Find the main table - it's usually the table with class 'tinytable'
        table = soup.find('table', {'class': 'tinytable'})
        
        # If not found, look for any tables with reasonable number of rows
        if not table:
            tables = soup.find_all('table')
            for t in tables:
                rows = t.find_all('tr')
                if len(rows) > 2:  # Looking for tables with enough rows
                    headers = [th.text.strip() for th in rows[0].find_all(['th', 'td'])]
                    # Check if this looks like the insider trading table
                    if any('filing' in h.lower() for h in headers) or any('trade' in h.lower() for h in headers):
                        table = t
                        break
        
        if not table:
            return {"error": "No insider trading data found", "html_content": soup.prettify()}
        
        # Get the expected column headers from the table
        headers = []
        header_row = table.find('tr')
        if header_row:
            headers = [th.text.strip() for th in header_row.find_all(['th', 'td'])]
        
        # If headers are empty or don't look right, use default column mapping
        if not headers or 'Filing Date' not in ' '.join(headers):
            # OpenInsider standard columns
            headers = ["X", "Filing Date", "Trade Date", "Ticker", "Insider Name", 
                      "Title", "Trade Type", "Price", "Qty", "Owned", "ΔOwn", "Value", 
                      "1d", "1w", "1m", "6m"]
        
        # Process each row in the table (skipping header)
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 7:  # Need at least basic trade info
                trade_data = {}
                
                # Map the cells to our expected fields
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        header = headers[i]
                        value = cell.text.strip()
                        
                        # Skip non-informative columns
                        if header in ['X', '1d', '1w', '1m', '6m']:
                            continue
                        
                        trade_data[header] = value
                
                # Add this trade to our data
                if trade_data:
                    insider_data["insider_trades"].append(trade_data)
                    
                    # Track buy/sell counts based on trade type or quantity
                    trade_type = trade_data.get('Trade Type', '')
                    qty = trade_data.get('Qty', '')
                    
                    # Check if it's a buy
                    if 'P - Purchase' in trade_type or trade_type.lower().startswith('p '):
                        insider_data["buy_count"] += 1
                    # Check if it's a sell
                    elif 'S - Sale' in trade_type or trade_type.lower().startswith('s '):
                        insider_data["sell_count"] += 1
                    # If trade type is missing, infer from quantity
                    elif qty:
                        if qty.startswith('+'):
                            insider_data["buy_count"] += 1
                        elif qty.startswith('-'):
                            insider_data["sell_count"] += 1
        
        # Calculate buy/sell ratio
        insider_data["buy_sell_ratio"] = f"{insider_data['buy_count']}:{insider_data['sell_count']}"
        
        return insider_data

if __name__ == "__main__":
    # Example usage
    parser = OpenInsiderParser("THS")
    data = parser.get_insider_data()
    print(json.dumps(data, indent=2))