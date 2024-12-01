import tkinter as tk
from tkinter import font
from PIL import Image, ImageTk
import requests
import pandas as pd
from io import BytesIO

# Function to fetch weather data
def fetch_weather(city):
    api_key = "4a3390d98df844149de163210240411"  # Replace with your actual API key
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        temperature = data['current']['temp_c']
        condition = data['current']['condition']['text']
        humidity = data['current']['humidity']
        icon_url = data['current']['condition']['icon']
        return temperature, condition, humidity, icon_url
    else:
        return None, None, None, None

# Function to update weather
def update_weather():
    city = city_entry.get()
    temperature, condition, humidity, icon_url = fetch_weather(city)
    if temperature is not None:
        temp_label.config(text=f"{temperature}°C")
        condition_label.config(text=condition)
        humidity_label.config(text=f"{humidity}%")
        save_to_csv(city, temperature, condition, humidity)
        
        # Update weather icon
        icon_response = requests.get(f"http:{icon_url}")
        icon_image = Image.open(BytesIO(icon_response.content))
        icon_photo = ImageTk.PhotoImage(icon_image)
        icon_label.config(image=icon_photo)
        icon_label.image = icon_photo
    else:
        temp_label.config(text="Error fetching data")
        condition_label.config(text="")
        humidity_label.config(text="")
        icon_label.config(image='')

# Function to save data to CSV
def save_to_csv(city, temperature, condition, humidity):
    data = {
        "City": [city],
        "Temperature": [temperature],
        "Condition": [condition],
        "Humidity": [humidity]
    }
    df = pd.DataFrame(data)
    df.to_csv("weather_history.csv", mode="a", index=False, header=False)

# Periodic update function
def update_weather_periodically():
    update_weather()
    root.after(600000, update_weather_periodically)  # 10 minutes

# Tkinter GUI setup
root = tk.Tk()
root.title("Weather Dashboard")
root.geometry("400x400")
root.configure(bg="#2B2D42")

# Fonts and Styles
title_font = font.Font(family="Helvetica", size=16, weight="bold")
label_font = font.Font(family="Helvetica", size=12)
value_font = font.Font(family="Helvetica", size=14, weight="bold")

# Title Label
title_label = tk.Label(root, text="Weather Dashboard", font=title_font, fg="#EDF2F4", bg="#2B2D42")
title_label.pack(pady=10)

# City Entry
city_entry = tk.Entry(root, width=20, font=label_font, fg="#2B2D42", justify="center")
city_entry.pack(pady=10)
city_entry.insert(0, "Enter City Name")
city_entry.bind("<FocusIn>", lambda event: city_entry.delete(0, "end"))

# Fetch Button
fetch_button = tk.Button(root, text="Get Weather", font=label_font, fg="#EDF2F4", bg="#EF233C", command=update_weather)
fetch_button.pack(pady=10)

# Weather Information Frame
weather_frame = tk.Frame(root, bg="#2B2D42")
weather_frame.pack(pady=10)

# Weather Icon Display
icon_label = tk.Label(weather_frame, bg="#2B2D42")
icon_label.grid(row=0, column=0, columnspan=2, pady=10)

# Temperature Display
temp_title = tk.Label(weather_frame, text="Temperature:", font=label_font, fg="#8D99AE", bg="#2B2D42")
temp_title.grid(row=1, column=0, sticky="e")
temp_label = tk.Label(weather_frame, text="", font=value_font, fg="#EDF2F4", bg="#2B2D42")
temp_label.grid(row=1, column=1, sticky="w", padx=10)

# Condition Display
condition_title = tk.Label(weather_frame, text="Condition:", font=label_font, fg="#8D99AE", bg="#2B2D42")
condition_title.grid(row=2, column=0, sticky="e")
condition_label = tk.Label(weather_frame, text="", font=value_font, fg="#EDF2F4", bg="#2B2D42")
condition_label.grid(row=2, column=1, sticky="w", padx=10)

# Humidity Display
humidity_title = tk.Label(weather_frame, text="Humidity:", font=label_font, fg="#8D99AE", bg="#2B2D42")
humidity_title.grid(row=3, column=0, sticky="e")
humidity_label = tk.Label(weather_frame, text="", font=value_font, fg="#EDF2F4", bg="#2B2D42")
humidity_label.grid(row=3, column=1, sticky="w", padx=10)

# Start periodic updates
update_weather_periodically()
root.mainloop()
