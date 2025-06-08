#!/usr/bin/env python3
"""
Property Editor for Solar System
Runs as a separate process to avoid threading issues with pygame
"""

import tkinter as tk
from tkinter import ttk
import json
import time
import os
import sys
from pathlib import Path

class PropertyEditor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Solar System Property Editor")
        
        self.position_window()
        
        self.data_dir = Path(__file__).parent / "property_data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.planet_data_file = self.data_dir / "current_planet.json"
        self.changes_file = self.data_dir / "property_changes.json"
        self.shutdown_file = self.data_dir / "shutdown_signal.txt"
        
        self.current_planet = None
        self.vars = {}
        
        self.setup_ui()
        self.start_monitoring()
    
    def position_window(self):
        """Position the window to appear in front of the main application"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        window_width = 400
        window_height = 700
        
        x = screen_width - window_width - 50
        y = 50
        
        if x < 0:
            x = screen_width - window_width
        if y + window_height > screen_height:
            y = screen_height - window_height
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.root.attributes('-topmost', True)
        self.root.after(1000, lambda: self.root.attributes('-topmost', False))
    
    def setup_ui(self):
        """Setup the user interface"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.no_planet_label = ttk.Label(self.scrollable_frame, 
                                        text="Select a planet in the main application\nto edit its properties", 
                                        font=('Arial', 12))
        self.no_planet_label.pack(pady=50)
    
    def clear_content(self):
        """Clear all content from the scrollable frame"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
    
    def create_property_controls(self, planet_data):
        """Create property controls for the planet"""
        self.clear_content()
        self.vars.clear()
        
        title = ttk.Label(self.scrollable_frame, 
                         text=f"{planet_data['name'].title()} Properties", 
                         font=('Arial', 14, 'bold'))
        title.pack(pady=(0, 10))
        
        info_frame = ttk.LabelFrame(self.scrollable_frame, text="Basic Information")
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text=f"Diameter: {planet_data['diameter']:,.0f} km").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=f"Distance: {planet_data['distance']:,.1f} million km").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=f"Mass: {planet_data['mass']:,.2f} × 10²⁴ kg").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=f"Moons: {planet_data['moons']}").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=f"Has Rings: {'Yes' if planet_data['has_rings'] else 'No'}").pack(anchor=tk.W, padx=5, pady=2)
        
        edit_frame = ttk.LabelFrame(self.scrollable_frame, text="Editable Properties")
        edit_frame.pack(fill=tk.X, pady=5)
        
        self.create_property_control(edit_frame, "Rotation Speed", 
                                   planet_data['rotation_speed'], -1000, 1000, 
                                   "rotation_speed", "degrees/second")
        
        self.create_property_control(edit_frame, "Orbit Speed", 
                                   planet_data['orbit_speed'], -10, 10, 
                                   "orbit_speed", "units/second")
        
        if planet_data['name'] == 'sun':
            self.create_property_control(edit_frame, "Scale", 
                                       planet_data['scale'], 1.0, 200.0, 
                                       "scale", "units")
        else:
            self.create_property_control(edit_frame, "Scale", 
                                       planet_data['scale'], 0.1, 50, 
                                       "scale", "units")
        
        if planet_data['name'] != 'sun':
            physical_frame = ttk.LabelFrame(self.scrollable_frame, text="Physical Properties")
            physical_frame.pack(fill=tk.X, pady=5)
            
            self.create_property_control(physical_frame, "Diameter", 
                                       planet_data['diameter'], 1000, 200000, 
                                       "diameter", "km")
            
            self.create_property_control(physical_frame, "Distance", 
                                       planet_data['distance'], 10, 6000, 
                                       "distance", "million km")
        
        values_frame = ttk.LabelFrame(self.scrollable_frame, text="Current Runtime Values")
        values_frame.pack(fill=tk.X, pady=5)
        
        self.orbit_angle_label = ttk.Label(values_frame, text=f"Orbit Angle: {planet_data['orbit_angle']:.1f}°")
        self.orbit_angle_label.pack(anchor=tk.W, padx=5, pady=2)
        
        self.rotation_angle_label = ttk.Label(values_frame, text=f"Rotation Angle: {planet_data['rotation_angle']:.1f}°")
        self.rotation_angle_label.pack(anchor=tk.W, padx=5, pady=2)
        
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Reset Position", 
                  command=self.reset_position).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Reset All Properties", 
                  command=self.reset_all_properties).pack(side=tk.LEFT, padx=5)
    
        ttk.Button(button_frame, text="Reset Simulation", 
                  command=self.reset_simulation).pack(side=tk.LEFT, padx=5)
    
    def create_property_control(self, parent, label, value, min_val, max_val, var_name, unit):
        """Create a property control with label, entry, and slider"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=3)
        
        ttk.Label(frame, text=f"{label} ({unit}):", width=15).pack(side=tk.LEFT)
        
        var = tk.DoubleVar(value=value)
        self.vars[var_name] = var
        
        entry = ttk.Entry(frame, textvariable=var, width=10)
        entry.pack(side=tk.LEFT, padx=5)
        
        scale = ttk.Scale(frame, from_=min_val, to=max_val, variable=var, 
                         orient=tk.HORIZONTAL, length=150)
        scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        var.trace_add('write', lambda *args, name=var_name: self.on_property_change(name))
    
    def on_property_change(self, property_name):
        """Handle property changes"""
        if property_name in self.vars:
            value = self.vars[property_name].get()
            self.send_property_change(property_name, value)
    
    def send_property_change(self, property_name, value):
        """Send property change to main application"""
        try:
            change_data = {
                'property': property_name,
                'value': value,
                'timestamp': time.time()
            }
            
            with open(self.changes_file, 'w') as f:
                json.dump(change_data, f)
        except Exception as e:
            pass
    
    def reset_position(self):
        """Reset planet position"""
        self.send_property_change('reset_position', True)
    
    def reset_all_properties(self):
        """Reset all properties"""
        self.send_property_change('reset_all', True)
    
    def reset_simulation(self):
        """Reset simulation"""
        self.send_property_change('reset_simulation', True)
    
    def start_monitoring(self):
        """Start monitoring for planet data updates and shutdown signals"""
        try:
            if self.shutdown_file.exists():
                self.shutdown_file.unlink()
                self.root.quit()
                return
        except Exception as e:
            pass
        
        self.monitor_planet_data()
        self.root.after(100, self.start_monitoring)
    
    def monitor_planet_data(self):
        """Monitor for planet data updates from main application"""
        try:
            if self.planet_data_file.exists():
                with open(self.planet_data_file, 'r') as f:
                    planet_data = json.load(f)
                
                if (self.current_planet is None or 
                    self.current_planet['name'] != planet_data['name']):
                    self.current_planet = planet_data
                    self.create_property_controls(planet_data)
                elif self.current_planet:
                    if ('reset_timestamp' in planet_data and 
                        ('reset_timestamp' not in self.current_planet or 
                         planet_data['reset_timestamp'] != self.current_planet['reset_timestamp'])):
                        self.current_planet = planet_data
                        self.create_property_controls(planet_data)
                    else:
                        if hasattr(self, 'orbit_angle_label'):
                            self.orbit_angle_label.config(text=f"Orbit Angle: {planet_data['orbit_angle']:.1f}°")
                        if hasattr(self, 'rotation_angle_label'):
                            self.rotation_angle_label.config(text=f"Rotation Angle: {planet_data['rotation_angle']:.1f}°")
                        
                        self.current_planet = planet_data
        except Exception as e:
            pass
    
    def run(self):
        """Run the property editor"""
        self.root.mainloop()

if __name__ == "__main__":
    editor = PropertyEditor()
    editor.run() 