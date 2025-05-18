# FinScan Qt - Stock Market Data Analysis Tool

FinScan Qt is a modern, feature-rich desktop application for analyzing stock market data with a user-friendly interface.

![FinScan Qt](finscan.ico)

## Features

- **Advanced Stock Data Analysis**: Collect and visualize comprehensive stock data
- **Intuitive Qt Interface**: Clean, responsive interface with collapsible sections
- **Real-time Data Collection**: Live progress tracking during data acquisition
- **Integrated File Management**: Easily access, view, and manage all your reports
- **TradingView Charts Integration**: View interactive stock charts directly in the app
- **Insider Trading Analysis**: Track buying and selling patterns of company insiders
- **Financial Metrics**: Access key valuation, technical, and growth metrics

## Requirements

- Python 3.8 or higher
- Required Python packages (automatically installed during setup)

## Quick Installation

### Windows Users

1. **One-Click Setup**: Double-click the `install_finscan.bat` file to install and set up shortcuts

The installer will:
- Install required Python packages
- Create a desktop shortcut with the FinScan icon
- Add FinScan to your Start Menu
- Offer to run the application immediately

### Manual Installation

If you prefer to install manually:

```bash
# Install requirements first
pip install -r requirements.txt

# Then simply run the launcher
launch_finscan.bat
```

## Running the Application

### Windows

There are three ways to launch FinScan:

1. **From Desktop**: Click the FinScan desktop shortcut created during installation
2. **From Start Menu**: Find and click FinScan in your Start Menu
3. **Direct Launch**: Double-click `launch_finscan.bat` file in the application folder

### Other Operating Systems

```bash
# Set required environment variables
export QTWEBENGINE_DISABLE_SANDBOX=1
export QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu"
export PYTHONIOENCODING="utf-8"

# Run the application
python finscan.py
```

## Using the Application

1. **Analyze a Stock**
   - Enter a stock symbol in the search box (e.g., "AAPL")
   - Click "Search" or press Enter to generate data
   - Watch the progress in the console output area

2. **View Analysis Results**
   - Collected data will be displayed in the main view with collapsible sections
   - TradingView chart will automatically load for visual analysis
   - Insider trading data is displayed in a dedicated section

3. **File Management**
   - All generated reports appear in the file list on the left
   - Select any file to view its contents
   - Use the View, Save, and Delete buttons to manage your files

4. **Advanced Features**
   - Use the tabs to switch between different views
   - External websites can be opened in dedicated tabs
   - Customize the display using the various view options

## Updating FinScan

To update FinScan to the latest version:

1. **Get the Latest Code**
   - Pull the latest code from the repository or download the newest release
   - Replace the existing application files with the new ones

2. **Update Dependencies**
   - Run the following command to update required packages:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. **Verify Installation**
   - Run `launch_finscan.bat` to ensure everything works correctly
   - The application will automatically use the updated files

## Troubleshooting

**Application won't start**: 
- Verify that Python is installed and in your PATH
- Check that all required packages are installed using `pip install -r requirements.txt`
- Make sure the Qt WebEngine cache is cleared (the launcher does this automatically)

**Error loading stock data**: 
- Ensure you have an active internet connection
- Verify the stock symbol exists and is correctly entered
- Some websites may temporarily block requests; wait a few minutes and try again

**UI display issues**: 
- Try clearing the Qt WebEngine cache manually by deleting the folder at `%LOCALAPPDATA%\python3\QtWebEngine`
- Restart the application using the launcher

## Advanced Usage

For power users, FinScan can be used directly from the command line:

```bash
# Generate data for a specific symbol
python stock_data_scraper.py AAPL --html

# Customize output location
python stock_data_scraper.py TSLA --html --output custom_report.html

# Generate JSON data instead of HTML
python stock_data_scraper.py MSFT --json
```

## Project Structure

The repository contains the following key files:

| File | Description |
|------|-------------|
| **launch_finscan.bat** | Primary launcher for Windows users - runs the application with proper environment settings |
| **install_finscan.bat** | Installation script that sets up shortcuts and icons |
| **update_finscan.bat** | Helper script for updating dependencies and clearing caches |
| **uninstall_finscan.bat** | Removes shortcuts created during installation |
| **finscan.py** | Main application code with the Qt interface |
| **stock_data_scraper.py** | Core data collection module |
| **openinsider_parser.py** | Module for parsing insider trading data |
| **finscan.ico** | Application icon |
| **requirements.txt** | List of Python package dependencies |

## Folder Structure

| Folder | Description |
|--------|-------------|
| **saved_data/** | Permanent storage location for saved reports |
| **temp_data/** | Temporary storage for generated reports |
| **__pycache__/** | Python bytecode cache (automatically generated) |

## Distributing FinScan

If you want to share FinScan with others who don't have the code:

1. **Create a distribution package:**
   - Include all Python files (*.py)
   - Include all batch files (*.bat)  
   - Include the icon file (finscan.ico)
   - Include requirements.txt
   - Include the LICENSE file

2. **Instructions for recipients:**
   - Install Python 3.8 or higher if they don't have it
   - Extract all files to a folder
   - Run `install_finscan.bat` to set up the application
   
The installer will handle the rest, creating shortcuts and installing dependencies.

## License

FinScan is licensed under the MIT License.

Copyright (c) 2025 Cyril Lutziger

See the [LICENSE](LICENSE) file for full details.
