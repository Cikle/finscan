// Stock Statistics Visualization Module

/**
 * Populates the stock dashboard with data extracted from HTML tables
 */
function populateStockDashboard() {
    console.log("Initializing stock dashboard...");

    // Extract all stock data from tables
    const stockData = extractStockData();

    // Populate key metrics
    populateKeyMetrics(stockData);

    // Create performance chart if available
    createPerformanceChart(stockData);

    // Create recommendation gauge if available
    createRecommendationGauge(stockData);

    console.log("Dashboard initialization complete");
}

/**
 * Extract stock data from HTML tables in the document
 * @returns {Object} Extracted stock data
 */
function extractStockData() {
    console.log("Extracting stock data from tables...");
    const stockData = {};

    // Find the Finviz table
    const finvizSection = findSectionByTitle("Finviz Data");
    if (finvizSection) {
        const finvizTable = finvizSection.querySelector("table");
        if (finvizTable) {
            extractTableData(finvizTable, stockData);
        }
    }

    // Find Yahoo Finance table
    const yahooSection = findSectionByTitle("Yahoo Finance Data");
    if (yahooSection) {
        const yahooTable = yahooSection.querySelector("table");
        if (yahooTable) {
            extractTableData(yahooTable, stockData);
        }
    }

    // Find other useful tables
    const analystSection = findSectionByTitle("Analyst Recommendations");
    if (analystSection) {
        const analystTable = analystSection.querySelector("table");
        if (analystTable) {
            extractTableData(analystTable, stockData);
        }
    }

    console.log(`Extracted ${Object.keys(stockData).length} data points`);
    return stockData;
}

/**
 * Find a section by its title text
 * @param {string} title - The title to search for
 * @returns {Element|null} The found section or null
 */
function findSectionByTitle(title) {
    const sections = document.querySelectorAll('.section');
    for (const section of sections) {
        const heading = section.querySelector('h2');
        if (heading && heading.textContent.includes(title)) {
            return section;
        }
    }
    return null;
}

/**
 * Extract data from a table into the stockData object
 * @param {Element} table - The table element
 * @param {Object} stockData - The object to populate with extracted data
 */
function extractTableData(table, stockData) {
    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 2) {
            const key = cells[0].textContent.trim();
            const value = cells[1].textContent.trim();
            stockData[key] = value;
            console.log(`Found data: ${key} = ${value}`);
        }
    });
}

/**
 * Populate key metrics on the dashboard
 * @param {Object} stockData - The stock data
 */
function populateKeyMetrics(stockData) {
    console.log("Populating key metrics...");

    // Elements to populate and their possible data keys
    const elements = {
        'marketCap': ['Market Cap', 'marketCap'],
        'peRatio': ['P/E', 'trailingPE', 'P/E Ratio'],
        'stockPrice': ['Price', 'currentPrice', 'Last Price'],
        'priceChange': ['Change', 'priceChange'],
        'volume': ['Volume', 'volume', 'Volume'],
        'beta': ['Beta', 'beta']
    };

    // Populate each element if data is available
    for (const [elementId, possibleKeys] of Object.entries(elements)) {
        const element = document.getElementById(elementId);
        if (element) {
            for (const key of possibleKeys) {
                if (stockData[key]) {
                    element.textContent = stockData[key];

                    // Format price change to show +/- and color
                    if (elementId === 'priceChange' && stockData[key]) {
                        formatPriceChange(element, stockData[key]);
                    }
                    break;
                }
            }
        }
    }
}

/**
 * Format price change element with color and +/- sign
 * @param {Element} element - The element to format
 * @param {string} changeText - The change text
 */
function formatPriceChange(element, changeText) {
    // Remove any % sign for parsing
    const cleanValue = changeText.replace('%', '');
    const change = parseFloat(cleanValue);

    if (!isNaN(change)) {
        if (change > 0) {
            element.classList.add('trend-positive');
            if (!changeText.startsWith('+')) {
                element.textContent = '+' + changeText;
            }
        } else if (change < 0) {
            element.classList.add('trend-negative');
        }
    }
}

/**
 * Create the performance chart
 * @param {Object} stockData - The stock data
 */
function createPerformanceChart(stockData) {
    console.log("Creating performance chart...");

    const chartCanvas = document.getElementById('performanceChart');
    if (!chartCanvas) return;

    const performanceLabels = ['Week', 'Month', 'Quarter', 'Half Year', 'Year', 'YTD'];
    const performanceKeys = ['Perf Week', 'Perf Month', 'Perf Quarter', 'Perf Half Y', 'Perf Year', 'Perf YTD'];
    const performanceData = [];

    // Collect performance data
    for (const key of performanceKeys) {
        if (stockData[key]) {
            // Extract percentage value
            const valueStr = stockData[key].replace('%', '');
            const value = parseFloat(valueStr);
            performanceData.push(isNaN(value) ? 0 : value);
            console.log(`Found performance data for ${key}: ${value}`);
        } else {
            performanceData.push(0);
        }
    }

    // Create chart
    const ctx = chartCanvas.getContext('2d');
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
                        callback: function (value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create the recommendation gauge
 * @param {Object} stockData - The stock data
 */
function createRecommendationGauge(stockData) {
    console.log("Creating recommendation gauge...");

    const gaugeCanvas = document.getElementById('recommendationGauge');
    const ratingElement = document.getElementById('recommendationRating');

    if (!gaugeCanvas || !ratingElement) return;

    // Default to neutral if no recommendation found
    let recommendationValue = 3;
    let recommendationText = 'Hold';

    if (stockData['Recom']) {
        recommendationValue = parseFloat(stockData['Recom']);
        console.log(`Found recommendation: ${recommendationValue}`);

        // Set text and color based on value
        if (recommendationValue <= 1.5) {
            recommendationText = 'Strong Buy';
            ratingElement.className = 'rating rating-strong';
        } else if (recommendationValue <= 2.5) {
            recommendationText = 'Buy';
            ratingElement.className = 'rating rating-good';
        } else if (recommendationValue <= 3.5) {
            recommendationText = 'Hold';
            ratingElement.className = 'rating rating-neutral';
        } else if (recommendationValue <= 4.5) {
            recommendationText = 'Sell';
            ratingElement.className = 'rating rating-warning';
        } else {
            recommendationText = 'Strong Sell';
            ratingElement.className = 'rating rating-poor';
        }

        ratingElement.textContent = `${recommendationText} (${recommendationValue})`;
    }

    // Create gauge chart
    const ctx = gaugeCanvas.getContext('2d');
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
    });
}

// Initialize dashboard when document is loaded
document.addEventListener('DOMContentLoaded', populateStockDashboard);