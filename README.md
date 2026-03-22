# Surveyor Suite

A comprehensive web-based application for surveying calculations and conversions, built with [NiceGUI](https://nicegui.io/) for an intuitive user experience.

## Features

### Angle Tools
- **Decimal Degrees to DMS**: Convert decimal degree coordinates to Degrees-Minutes-Seconds format
- **Azimuth & Bearings**: Convert between azimuth (0-360°) and quadrant bearings (NE, SE, SW, NW)
- **Batch Processing**: Upload CSV files for bulk conversions

### Distance
- **Unit Converter**: Convert between various length units (meters, chains, links, rods, feet)
- **Map Scale Calculator**: Calculate ground distances from map measurements
- **Batch Processing**: Process multiple values via CSV upload

### Coordinates
- **CRS Transformations**: Transform coordinates between different EPSG coordinate reference systems
- **Interactive Map**: Visualize converted coordinates on a Folium-powered map
- **Batch Processing**: Transform coordinate pairs from CSV files

### Area
- **Unit Converter**: Convert between area units (sq_meters, hectares, acres, sq_feet)
- **Batch Processing**: Bulk area conversions from CSV data

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd converters
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

5. **Open in browser**: Navigate to `http://localhost:8080`

## Usage

- **Single Mode**: Enter values manually and convert individually
- **Batch Mode**: Upload CSV files for bulk processing
- **Map Visualization**: For coordinate conversions, view results on an interactive map
- **Download Results**: Processed data can be downloaded as CSV files

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`
- Web browser for accessing the interface

## Project Structure

```
converters/
├── main.py                 # Main application file
├── converter_functions.py  # Conversion logic and utilities
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is open-source. Please check the license file for details.

## Built With

- [NiceGUI](https://nicegui.io/) - Web framework
- [Folium](https://python-visualization.github.io/folium/) - Interactive maps
- [Pandas](https://pandas.pydata.org/) - Data manipulation
- [PyProj](https://pyproj4.github.io/pyproj/) - Coordinate transformations