# FinScan Qt - All-in-One

## Overview
FinScan Qt All-in-One is a modern application for analyzing stock data. This version combines all functionality into a single executable file, eliminating the need for separate script files and fixing Unicode encoding issues that occurred in the previous version.

## Features
- **Modern Qt Interface**: Clean, responsive design with dark mode support
- **TradingView Integration**: View professional stock charts directly in the application
- **Real-time Stock Data**: Collect and analyze current stock data
- **Unicode Safe**: All text processing is Unicode-safe for Windows compatibility
- **Report Management**: Save, view, and organize your stock data reports

## Requirements
- Python 3.6 or higher
- PyQt5
- PyQtWebEngine
- Required libraries (install via pip):
  ```
  pip install pyqt5 pyqtwebengine requests beautifulsoup4
  ```

## Troubleshooting

### QtWebEngine Errors
If you see errors like:
```
[ERROR:cache_util_win.cc(21)] Unable to move the cache
[ERROR:shader_disk_cache.cc(606)] Shader Cache Creation failed
js: Uncaught SyntaxError: Unexpected token '='
```

These are normal QtWebEngine errors and usually don't affect application functionality. We've implemented several fixes:

1. The batch file launcher (`launch_finscan_qt_all_in_one.bat`) configures environment variables to minimize these errors
2. We've added custom cache path handling in the TradingView widget
3. JavaScript in the application uses ES5 syntax for wider compatibility

If you still experience issues:
- Try running with administrator privileges
- Delete the `.finscan_cache` directory in your home folder
- Ensure you have internet connectivity for TradingView charts

## Usage
1. Run the application using the provided batch file:
   ```
   launch_finscan_qt_all_in_one.bat
   ```

2. Enter a stock symbol (e.g., AAPL, MSFT, GOOG) in the search box
3. Click "Generate Data" to collect the latest stock information
4. View the TradingView chart and key metrics in the tabs
5. Save reports for future reference

## Files
- `finscan_qt_all_in_one.py`: Main application file (complete solution)
- `launch_finscan_qt_all_in_one.bat`: Windows launcher batch file
- `stock_data_scraper.py`: Core data collection module (required)
- `openinsider_parser.py`: Parser for insider trading data (required)

## Legacy Files
The following files have been moved to the legacy folder and are no longer needed:
- `finscan_app.py`: Original web-based implementation
- `finscan_basic.py`: Basic command-line implementation
- `finscan_temp.py`: Temporary development version
- `finscan_qt.py`: Previous Qt implementation (requires the wrapper)
- `stock_data_scraper_wrapper.py`: Unicode safety wrapper (now integrated)

## Improvements
This all-in-one solution addresses several issues from the previous implementation:
1. **Unicode Handling**: Properly handles emoji and special characters directly
2. **No External Dependencies**: Eliminates the need for wrapper scripts
3. **Simplified Codebase**: Combines functionality into a single file
4. **Improved TradingView Integration**: Fixed duplicate chart loading
5. **Enhanced UI**: More modern look and feel with better error handling

## Troubleshooting
If you encounter any issues:

1. Check that Python and required libraries are installed
2. Ensure Windows console is set to UTF-8 mode (chcp 65001)
3. Verify that stock_data_scraper.py is in the same directory
4. Use the built-in console output to see detailed error messages