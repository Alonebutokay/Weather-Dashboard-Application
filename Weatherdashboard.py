import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import pandas as pd
from datetime import datetime
from PIL import Image, ImageTk
from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from pathlib import Path
import logging
import os
from typing import Dict, Optional, Tuple
import configparser
from dataclasses import dataclass
import threading
from queue import Queue
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weather_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class WeatherData:
    """Data class for weather information"""
    temperature: float
    condition: str
    humidity: int
    wind_speed: float
    pressure: float
    feels_like: float
    icon_url: str
    
class Config:
    """Configuration manager"""
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = 'config.ini'
        self.load_config()

    def load_config(self):
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.config['API'] = {
                'key': '4a3390d98df844149de163210240411',
                'base_url': 'http://api.weatherapi.com/v1'
            }
            self.config['APP'] = {
                'default_city': 'London',
                'update_interval': '300',
                'theme': 'dark'
            }
            self.save_config()

    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def get(self, section: str, key: str) -> str:
        """Get configuration value"""
        return self.config.get(section, key)

class WeatherAPI:
    """Weather API handler"""
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.base_url = config.get('API', 'base_url')
        self.api_key = config.get('API', 'key')

    def get_weather(self, city: str) -> Optional[Dict]:
        """Fetch weather data from API"""
        try:
            params = {
                'key': self.api_key,
                'q': city,
                'aqi': 'yes'
            }
            current_response = self.session.get(
                f"{self.base_url}/current.json",
                params=params
            )
            forecast_response = self.session.get(
                f"{self.base_url}/forecast.json",
                params={**params, 'days': 1}
            )
            
            current_response.raise_for_status()
            forecast_response.raise_for_status()
            
            return {
                'current': current_response.json(),
                'forecast': forecast_response.json()
            }
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None

class DataManager:
    """Data management and persistence"""
    def __init__(self):
        self.history_file = Path('data/weather_history.csv')
        self.history_file.parent.mkdir(exist_ok=True)

    def save_weather_data(self, city: str, weather: WeatherData):
        """Save weather data to CSV"""
        try:
            data = {
                'timestamp': [datetime.now()],
                'city': [city],
                'temperature': [weather.temperature],
                'condition': [weather.condition],
                'humidity': [weather.humidity],
                'wind_speed': [weather.wind_speed],
                'pressure': [weather.pressure]
            }
            df = pd.DataFrame(data)
            df.to_csv(self.history_file, mode='a', header=not self.history_file.exists(), index=False)
        except Exception as e:
            logger.error(f"Failed to save weather data: {e}")

class WeatherDashboard(tk.Tk):
    """Main application window"""
    def __init__(self):
        super().__init__()

        self.config = Config()
        self.api = WeatherAPI(self.config)
        self.data_manager = DataManager()
        
        self.title("Professional Weather Dashboard")
        self.geometry("1024x768")
        self.configure_styles()
        self.setup_ui()
        
        # Initialize update queue and thread
        self.update_queue = Queue()
        self.start_update_thread()
        
        # Load initial data
        self.load_initial_data()

    def configure_styles(self):
        """Configure application styles"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure colors
        self.colors = {
            'bg': '#1E1E1E',
            'fg': '#FFFFFF',
            'accent': '#007ACC',
            'warning': '#FF6B6B'
        }
        
        # Configure custom styles
        self.style.configure(
            'Custom.TFrame',
            background=self.colors['bg']
        )
        self.style.configure(
            'Custom.TLabel',
            background=self.colors['bg'],
            foreground=self.colors['fg']
        )
        self.style.configure(
            'Custom.TButton',
            background=self.colors['accent'],
            foreground=self.colors['fg']
        )

    def setup_ui(self):
        """Setup user interface"""
        # Main container
        self.main_frame = ttk.Frame(self, style='Custom.TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Search frame
        self.setup_search_frame()
        
        # Content frame
        self.content_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Current weather frame
        self.setup_current_weather_frame()
        
        # Forecast graph frame
        self.setup_forecast_frame()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(
            self,
            textvariable=self.status_var,
            style='Custom.TLabel'
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_search_frame(self):
        """Setup search interface"""
        search_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        search_frame.pack(fill=tk.X)
        
        self.city_var = tk.StringVar()
        self.city_entry = ttk.Entry(
            search_frame,
            textvariable=self.city_var,
            font=('Segoe UI', 12)
        )
        self.city_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        search_btn = ttk.Button(
            search_frame,
            text="Search",
            command=self.update_weather,
            style='Custom.TButton'
        )
        search_btn.pack(side=tk.LEFT)

    def setup_current_weather_frame(self):
        """Setup current weather display"""
        self.weather_frame = ttk.Frame(
            self.content_frame,
            style='Custom.TFrame'
        )
        self.weather_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Weather icon
        self.icon_label = ttk.Label(
            self.weather_frame,
            style='Custom.TLabel'
        )
        self.icon_label.pack(pady=10)
        
        # Weather info
        self.temp_var = tk.StringVar()
        self.condition_var = tk.StringVar()
        self.humidity_var = tk.StringVar()
        self.wind_var = tk.StringVar()
        self.pressure_var = tk.StringVar()
        
        weather_info = [
            ("Temperature", self.temp_var),
            ("Condition", self.condition_var),
            ("Humidity", self.humidity_var),
            ("Wind Speed", self.wind_var),
            ("Pressure", self.pressure_var)
        ]
        
        for label, var in weather_info:
            frame = ttk.Frame(self.weather_frame, style='Custom.TFrame')
            frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(
                frame,
                text=f"{label}:",
                style='Custom.TLabel'
            ).pack(side=tk.LEFT)
            
            ttk.Label(
                frame,
                textvariable=var,
                style='Custom.TLabel'
            ).pack(side=tk.LEFT, padx=10)

    def setup_forecast_frame(self):
        """Setup forecast graph"""
        self.forecast_frame = ttk.Frame(
            self.content_frame,
            style='Custom.TFrame'
        )
        self.forecast_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.fig.patch.set_facecolor(self.colors['bg'])
        self.ax.set_facecolor(self.colors['bg'])
        
        self.canvas = FigureCanvasTkAgg(self.fig, self.forecast_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def start_update_thread(self):
        """Start background update thread"""
        self.update_thread = threading.Thread(
            target=self.update_worker,
            daemon=True
        )
        self.update_thread.start()

    def update_worker(self):
        """Background worker for updates"""
        while True:
            try:
                city = self.update_queue.get()
                self.status_var.set(f"Fetching weather data for {city}...")
                
                weather_data = self.api.get_weather(city)
                if weather_data:
                    self.process_weather_data(city, weather_data)
                else:
                    self.status_var.set("Failed to fetch weather data")
                
                self.update_queue.task_done()
            except Exception as e:
                logger.error(f"Update worker error: {e}")
                self.status_var.set("An error occurred")

    def process_weather_data(self, city: str, data: Dict):
        """Process and display weather data"""
        try:
            current = data['current']['current']
            
            weather = WeatherData(
                temperature=current['temp_c'],
                condition=current['condition']['text'],
                humidity=current['humidity'],
                wind_speed=current['wind_kph'],
                pressure=current['pressure_mb'],
                feels_like=current['feelslike_c'],
                icon_url=f"http:{current['condition']['icon']}"
            )
            
            # Update UI
            self.update_ui(city, weather)
            
            # Update graph
            self.update_forecast_graph(data['forecast'])
            
            # Save data
            self.data_manager.save_weather_data(city, weather)
            
            self.status_var.set(f"Weather updated for {city}")
            
        except Exception as e:
            logger.error(f"Failed to process weather data: {e}")
            self.status_var.set("Failed to process weather data")

    def update_ui(self, city: str, weather: WeatherData):
        """Update UI with weather data"""
        self.temp_var.set(f"{weather.temperature}°C")
        self.condition_var.set(weather.condition)
        self.humidity_var.set(f"{weather.humidity}%")
        self.wind_var.set(f"{weather.wind_speed} km/h")
        self.pressure_var.set(f"{weather.pressure} mb")
        
        # Update icon
        try:
            response = requests.get(weather.icon_url)
            img = Image.open(BytesIO(response.content))
            photo = ImageTk.PhotoImage(img)
            self.icon_label.configure(image=photo)
            self.icon_label.image = photo
        except Exception as e:
            logger.error(f"Failed to update weather icon: {e}")

    def update_forecast_graph(self, forecast_data: Dict):
        """Update forecast graph"""
        try:
            hours = forecast_data['forecast']['forecastday'][0]['hour']
            times = [datetime.fromisoformat(hour['time']) for hour in hours]
            temps = [hour['temp_c'] for hour in hours]
            
            self.ax.clear()
            self.ax.plot(times, temps, color=self.colors['accent'])
            
            self.ax.set_facecolor(self.colors['bg'])
            self.ax.tick_params(colors=self.colors['fg'])
            
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            plt.xticks(rotation=45)
            
            self.ax.set_title('24-Hour Forecast', color=self.colors['fg'])
            self.ax.set_ylabel('Temperature (°C)', color=self.colors['fg'])
            
            self.canvas.draw()
        except Exception as e:
            logger.error(f"Failed to update forecast graph: {e}")

    def update_weather(self):
        """Trigger weather update"""
        city = self.city_var.get().strip()
        if city:
            self.update_queue.put(city)
        else:
            messagebox.showwarning("Input Error", "Please enter a city name")

    def load_initial_data(self):
        """Load initial weather data"""
        default_city = self.config.get('APP', 'default_city')
        self.city_var.set(default_city)
        self.update_weather()

def main():
    try:
        app = WeatherDashboard()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Application failed to start: {e}")
        messagebox.showerror("Error", "Application failed to start. Check logs for details.")

if __name__ == "__main__":
    main()

