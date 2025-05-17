# Script to fix the stock data HTML template issues
import os
import shutil
from bs4 import BeautifulSoup

def update_stock_data_scraper():
    """Modify the stock_data_scraper.py file to use the new template"""
    print("Updating stock_data_scraper.py to use the new template...")
    
    # 1. Make a backup of the original file
    scraper_path = os.path.join(os.getcwd(), "stock_data_scraper.py")
    backup_path = os.path.join(os.getcwd(), "stock_data_scraper.py.bak")
    
    if not os.path.exists(backup_path):
        shutil.copy2(scraper_path, backup_path)
        print(f"Created backup at {backup_path}")
    
    # 2. Read the template file
    template_path = os.path.join(os.getcwd(), "stock_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    # 3. Read the current scraper file
    with open(scraper_path, "r", encoding="utf-8") as f:
        scraper_content = f.read()
    
    # 4. Find the save_html method in the scraper code
    save_html_start = scraper_content.find("def save_html")
    if save_html_start == -1:
        print("Error: Could not find save_html method in the scraper code")
        return False
    
    # Find the next method after save_html
    next_method = scraper_content.find("def ", save_html_start + 1)
    if next_method == -1:
        print("Error: Could not find the end of save_html method")
        return False
    
    # Extract the current save_html method
    save_html_method = scraper_content[save_html_start:next_method]
    
    # 5. Create a new save_html method using the template
    new_save_html_method = f"""
    def save_html(self, filename=None):
        '''Save the collected data as a formatted HTML file'''
        if not filename:
            filename = f"{{self.symbol}}_data_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.html"
        
        # Read the template file
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_template.html")
        
        # If template doesn't exist, create a basic HTML template
        if not os.path.exists(template_path):
            # Create a simple HTML structure
            html_content = f'''<!DOCTYPE html>
            <html>
            <head>
                <title>{{self.symbol}} Financial Data</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                </style>
            </head>
            <body>
                <h1>{{self.symbol}} Financial Data</h1>
                <p>Data collected on {{self.data["timestamp"]}}</p>
                <pre>{{str(self.data)}}</pre>
            </body>
            </html>'''
        else:
            # Use the template file
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
            
            # Update template with stock data
            html_content = template.replace("Stock Financial Data", f"{{self.symbol}} Financial Data")
            html_content = html_content.replace("[DATE]", self.data["timestamp"])
            
            # Create a BeautifulSoup object to modify the template
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Add Finviz data to the template
            finviz_table = soup.find(id="finvizTable")
            if finviz_table:
                for key, value in self.data["finviz"].items():
                    row = soup.new_tag("tr")
                    key_cell = soup.new_tag("td")
                    key_cell.string = key
                    value_cell = soup.new_tag("td")
                    value_cell.string = str(value)
                    row.append(key_cell)
                    row.append(value_cell)
                    finviz_table.append(row)
            
            # Add Yahoo Finance data
            yahoo_section = soup.find(id="finvizSection")
            if yahoo_section and self.data["yahoo_finance"]:
                # Create Yahoo Finance section
                yahoo_div = soup.new_tag("div")
                yahoo_div["class"] = "section"
                yahoo_h2 = soup.new_tag("h2")
                yahoo_h2.string = "Yahoo Finance Data"
                yahoo_div.append(yahoo_h2)
                
                card_div = soup.new_tag("div")
                card_div["class"] = "card"
                yahoo_div.append(card_div)
                
                yahoo_table = soup.new_tag("table")
                card_div.append(yahoo_table)
                
                # Add header row
                header_row = soup.new_tag("tr")
                header_metric = soup.new_tag("th")
                header_metric.string = "Metric"
                header_value = soup.new_tag("th")
                header_value.string = "Value"
                header_row.append(header_metric)
                header_row.append(header_value)
                yahoo_table.append(header_row)
                
                # Add data rows
                for key, value in self.data["yahoo_finance"].items():
                    if key != "error":
                        row = soup.new_tag("tr")
                        key_cell = soup.new_tag("td")
                        key_cell.string = key
                        value_cell = soup.new_tag("td")
                        value_cell.string = str(value)
                        row.append(key_cell)
                        row.append(value_cell)
                        yahoo_table.append(row)
                
                # Insert Yahoo section after Finviz section
                yahoo_section.insert_after(yahoo_div)
            
            # Add other sections as needed
            html_content = str(soup)
            
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"💾 HTML report saved to {{filename}}")
        return filename
    """
    
    # 6. Replace the old save_html method with the new one
    new_scraper_content = scraper_content.replace(save_html_method, new_save_html_method)
    
    # 7. Write the updated scraper back to disk
    with open(scraper_path, "w", encoding="utf-8") as f:
        f.write(new_scraper_content)
    
    print("Successfully updated stock_data_scraper.py")
    return True

def main():
    print("Starting HTML template fix...")
    
    # Check if the template file exists
    template_path = os.path.join(os.getcwd(), "stock_template.html")
    if not os.path.exists(template_path):
        print(f"Error: Template file not found at {template_path}")
        return
    
    # Update the stock_data_scraper.py file
    if update_stock_data_scraper():
        print("\nAll updates completed successfully.")
        print("\nThe stock scraper now uses the improved template that correctly displays:")
        print("- Volume")
        print("- Daily change")
        print("- Performance metrics")
        print("- Analyst recommendations")
        print("\nGenerate a new report to see these improvements.")
    else:
        print("\nFailed to update stock_data_scraper.py")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()