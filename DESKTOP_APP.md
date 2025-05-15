# FinScan Desktop Application

A graphical user interface for the FinScan stock data scraper.

## Features

- **Easy to use**: Input a stock symbol and click "Generate Data"
- **Real-time console output**: See the scraper's progress live
- **File manager**: Easy access to all generated reports
- **One-click viewing**: Double-click any report to open it in your browser
- **Example symbols**: Quick buttons for popular stocks

## Installation

The desktop application requires Python with Tkinter (included in standard Python installations).

No additional dependencies are required beyond those already needed for the stock data scraper.

## Running the Application

### Windows

Double-click the `launch_finscan.bat` file to start the application.

### Mac/Linux or Command Line

```bash
python finscan_app.py
```

## Using the Application

1. **Input a Stock Symbol**
   - Type a stock symbol in the text box (e.g., "AAPL")
   - Or click one of the example buttons

2. **Generate Data**
   - Click the "Generate Data" button
   - Watch the console output for progress
   - Wait for the process to complete (typically 10-15 seconds)

3. **View the Results**
   - When processing is complete, you'll be prompted to open the report
   - You can also double-click any report in the "Generated Files" list
   - Reports open in your default web browser

4. **Manage Generated Files**
   - All generated reports appear in the "Generated Files" list
   - Click "Refresh" to update the list
   - Double-click any file to open it

## Troubleshooting

**Error generating data**: Make sure you have internet access and the stock symbol exists

**No console output**: The scraper may have encountered an error - check the console for details

**Files not appearing in list**: Click the "Refresh" button to update the file list

## Advanced

The application runs the same Python script as the command-line version. You can still use the command line for advanced or batch operations:

```bash
python stock_data_scraper.py SYMBOL --html --output FILENAME.html
```