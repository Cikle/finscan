# Stock Data Scraper

This tool collects financial data from multiple sources (Finviz, Capital.com, OpenInsider, and Yahoo Finance) for a specified stock symbol and presents it in a format that's easy to copy or download for use with AI trading algorithms.

## Installation

1. Clone the repository or download the files
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create your configuration file:
   ```
   cp config.json.template config.json
   ```
4. Edit `config.json` and add your API keys

## Usage

Run the script from the command line, providing the stock symbol as an argument:

```
python stock_data_scraper.py AAPL
```

This will generate an HTML report by default.

### Options

- `--json` - Save data in JSON format
- `--html` - Save data in HTML format (default)
- `--output` or `-o` - Specify output filename

Example:
```
python stock_data_scraper.py MSFT --json --output microsoft_data.json
```

## Output

### HTML Report

The HTML report includes:
- Interactive tables with data from all sources
- A "Copy All Data" button to copy formatted data for AI trading
- Visualizations of key metrics

### JSON Data

The JSON output contains the raw data collected from all sources, which can be used for further analysis or integration with other tools.

## API Keys

To use the Capital.com API functionality, you'll need to add your API key to the `config.json` file. Other data sources don't require API keys as they're scraped from public web pages.

## Quantum Trading Format

The data is formatted specifically to work with the Quantum Trading prompt for AI trading assistants. Just copy the data using the button in the HTML report and paste it along with your Quantum Trading prompt.