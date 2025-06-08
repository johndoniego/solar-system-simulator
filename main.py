import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import time
from pathlib import Path
from glb_loader import GLBLoader
from shader import Shader
import glm
from dataclasses import dataclass
from typing import List, Dict, Tuple
import traceback
import json
import subprocess
import os

@dataclass
class PlanetConfig:
    name: str
    model_file: str
    diameter: float         # in km
    distance: float         # in million km
    mass: float             # in 10^24 kg
    orbit_speed: float      # km/s
    rotation_period: float  # hours
    color: Tuple[float, float, float]
    moons: int
    has_rings: bool

class PropertyEditorCommunicator:
    def __init__(self, solar_system):
        self.solar_system = solar_system
        self.current_planet = None
        
        # Data files for communication
        self.data_dir = Path(__file__).parent / "property_data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.planet_data_file = self.data_dir / "current_planet.json"
        self.changes_file = self.data_dir / "property_changes.json"
        
        self.last_change_time = 0
        self.property_editor_process = None
        
    def close_property_editor(self):
        try:
            if self.property_editor_process and self.property_editor_process.poll() is None:
                shutdown_file = self.data_dir / "shutdown_signal.txt"
                shutdown_file.write_text("shutdown")
                
                try:
                    self.property_editor_process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.property_editor_process.kill()
                    self.property_editor_process.wait(timeout=1.0)
                
            self.property_editor_process = None
            self.current_planet = None
            
        except Exception as e:
            self.property_editor_process = None
            self.current_planet = None
    
    def start_property_editor(self):
        try:
            if self.property_editor_process is None or self.property_editor_process.poll() is not None:
                script_path = Path(__file__).parent / "property_editor.py"
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                self.property_editor_process = subprocess.Popen([
                    "python", str(script_path)
                ], creationflags=creation_flags)
        except Exception as e:
            pass
    
    def _create_planet_data(self, planet, include_reset_timestamp=False):
        data = {
            'name': planet.config.name,
            'diameter': planet.config.diameter,
            'distance': planet.config.distance,
            'mass': planet.config.mass,
            'moons': planet.config.moons,
            'has_rings': planet.config.has_rings,
            'rotation_speed': planet.rotation_speed,
            'orbit_speed': planet.orbit_speed,
            'rotation_angle': planet.rotation_angle,
            'scale': planet.scale,
            'color': planet.config.color,
            'orbit_angle': planet.orbit_angle
        }
        if include_reset_timestamp:
            data['reset_timestamp'] = time.time()
        return data
    
    def update_planet_data(self, planet):
        try:
            data = self._create_planet_data(planet, include_reset_timestamp=True)
            
            with open(self.planet_data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
        except Exception as e:
            pass
    
    def show_planet_properties(self, planet):
        try:
            self.close_property_editor()
            time.sleep(0.1)
            
            self.current_planet = planet
            
            data = self._create_planet_data(planet)
            
            with open(self.planet_data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.start_property_editor()
            
        except Exception as e:
            pass
    
    def check_property_changes(self):
        """Check for property changes from property editor"""
        try:
            if self.changes_file.exists():
                mtime = self.changes_file.stat().st_mtime
                
                if mtime > self.last_change_time:
                    self.last_change_time = mtime
                    
                    with open(self.changes_file, 'r') as f:
                        change_data = json.load(f)
                    
                    self.apply_property_change(change_data)
                    
        except Exception as e:
            pass  # File might be being written, ignore errors
    
    def apply_property_change(self, change_data):
        if not self.current_planet:
            return
        
        try:
            property_name = change_data['property']
            value = change_data['value']
            
            if property_name == "rotation_speed":
                self.current_planet.rotation_speed = value
            elif property_name == "orbit_speed":
                self.current_planet.orbit_speed = value
            elif property_name == "rotation_angle":
                self.current_planet.rotation_angle = value
            elif property_name == "scale":
                self.current_planet.scale = value
            elif property_name == "diameter":
                self.current_planet.config.diameter = value
                self._recalculate_scale(self.current_planet)
            elif property_name == "distance":
                self.current_planet.config.distance = value
                self._recalculate_orbit_radius(self.current_planet)
            elif property_name == "reset_position":
                self.current_planet.reset_position()
            elif property_name == "reset_all":
                self.reset_all_properties()
            elif property_name == "reset_simulation":
                self.solar_system.reset_all_simulation()
            
        except Exception as e:
            pass
    
    def _recalculate_orbit_radius(self, planet):
        """Recalculate orbit radius when distance changes"""
        try:
            if planet.config.name == "sun":
                planet.orbit_radius = 0
                return
            
            all_configs = self.solar_system._get_planet_configs()
            max_real_distance = max(p.distance for p in all_configs if p.name != "sun")
            distance_scale = 4000.0 / max_real_distance
            
            # Calculate minimum separation based on sun's size plus buffer
            sun_radius = 20.0  # Sun's visual scale
            buffer_space = 150.0  # Much larger buffer space to prevent swallowing
            min_separation = sun_radius + buffer_space
            
            scaled_distance = planet.config.distance * distance_scale
            planet.orbit_radius = max(scaled_distance, min_separation)
            
        except Exception as e:
            pass
    
    def _recalculate_scale(self, planet):
        """Recalculate scale when diameter changes"""
        try:
            # Get original diameter for this planet
            original_configs = self.solar_system._get_planet_configs()
            original_diameter = None
            
            for config in original_configs:
                if config.name == planet.config.name:
                    original_diameter = config.diameter
                    break
            
            if original_diameter is None:
                return
            
            # Get the original scale from VISUAL_SIZES
            if planet.config.name in self.solar_system.VISUAL_SIZES:
                original_scale = self.solar_system.VISUAL_SIZES[planet.config.name]
                
                # Calculate proportional scale based on diameter ratio
                diameter_ratio = planet.config.diameter / original_diameter
                planet.scale = original_scale * diameter_ratio
                
                # Apply reasonable limits to prevent extreme sizes
                if planet.config.name == "sun":
                    planet.scale = max(1.0, min(500.0, planet.scale))
                else:
                    planet.scale = max(0.1, min(100.0, planet.scale))
            
        except Exception as e:
            pass
    
    def reset_all_properties(self):
        if not self.current_planet:
            return
        
        try:
            original_configs = self.solar_system._get_planet_configs()
            original_config = None
            
            for config in original_configs:
                if config.name == self.current_planet.config.name:
                    original_config = config
                    break
            
            if original_config:
                self.current_planet.config.diameter = original_config.diameter
                self.current_planet.config.distance = original_config.distance
                self.current_planet.config.mass = original_config.mass
                self.current_planet.config.orbit_speed = original_config.orbit_speed
                self.current_planet.config.rotation_period = original_config.rotation_period
                
                self.current_planet.orbit_speed = original_config.orbit_speed * 0.02
                
                if original_config.name == "sun":
                    self.current_planet.rotation_speed = 2.0
                else:
                    direction = -1 if original_config.rotation_period < 0 else 1
                    rotation_hours = abs(original_config.rotation_period)
                    self.current_planet.rotation_speed = direction * (360.0 / (rotation_hours * 3600)) * 100
                
                if original_config.name in self.solar_system.VISUAL_SIZES:
                    self.current_planet.scale = self.solar_system.VISUAL_SIZES[original_config.name]
                
                # Restore original orbital position instead of recalculating
                if original_config.name in self.solar_system.original_orbit_positions:
                    self.current_planet.orbit_radius = self.solar_system.original_orbit_positions[original_config.name]
                
                self.current_planet.reset_position()
                
                self.update_planet_data(self.current_planet)
            
        except Exception as e:
            pass
    
    def update(self):
        """Update communicator (called from main loop)"""
        self.check_property_changes()
    
    def cleanup(self):
        """Clean up property editor process"""
        try:
            self.close_property_editor()
        except Exception as e:
            pass

class Camera:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.distance = 3000.0  # Reduced from 5000.0 to zoom closer to solar system
        self.yaw = 45.0
        self.pitch = -30.0
        
        # Planet targeting
        self.target_planet = None
        self.zoom_distance = None
        
        # Smooth transition properties
        self.transition_time = 0.0
        self.transition_duration = 2.0  # 2 seconds for smooth transition
        self.is_transitioning = False
        
        # Store start and end positions for smooth interpolation
        self.start_distance = 3000.0  # Updated default
        self.start_yaw = 45.0
        self.start_pitch = -30.0
        self.target_distance = 3000.0  # Updated default
        self.target_yaw = 45.0
        self.target_pitch = -30.0
        self.start_position = glm.vec3(0, 0, 0)
        self.target_position = glm.vec3(0, 0, 0)
    
    def smooth_lerp(self, t):
        """Smooth interpolation function (ease in-out)"""
        return t * t * (3.0 - 2.0 * t)
    
    def get_planet_position(self, planet):
        """Get current position of a planet"""
        if planet.config.name == "sun":
            return glm.vec3(0, 0, 0)
        orbit_x = planet.orbit_radius * math.cos(math.radians(planet.orbit_angle))
        orbit_z = planet.orbit_radius * math.sin(math.radians(planet.orbit_angle))
        return glm.vec3(orbit_x, 0, orbit_z)
    
    def get_view_matrix(self) -> glm.mat4:
        current_distance = self.distance
        current_yaw = self.yaw
        current_pitch = self.pitch
        look_at_pos = glm.vec3(0, 0, 0)
        
        # Handle smooth transitions
        if self.is_transitioning and self.transition_time < self.transition_duration:
            t = self.transition_time / self.transition_duration
            smooth_t = self.smooth_lerp(t)
            
            # Interpolate camera properties
            current_distance = self.start_distance + (self.target_distance - self.start_distance) * smooth_t
            current_yaw = self.start_yaw + (self.target_yaw - self.start_yaw) * smooth_t
            current_pitch = self.start_pitch + (self.target_pitch - self.start_pitch) * smooth_t
            
            # Interpolate look-at position
            look_at_pos = self.start_position + (self.target_position - self.start_position) * smooth_t
        elif self.target_planet is not None:
            # Follow the target planet
            look_at_pos = self.get_planet_position(self.target_planet)
            current_distance = self.zoom_distance if self.zoom_distance else self.target_planet.scale * 5
        
        cam_x = look_at_pos.x + current_distance * math.cos(math.radians(current_pitch)) * math.cos(math.radians(current_yaw))
        cam_y = look_at_pos.y + current_distance * math.sin(math.radians(current_pitch))
        cam_z = look_at_pos.z + current_distance * math.cos(math.radians(current_pitch)) * math.sin(math.radians(current_yaw))
        
        return glm.lookAt(
            glm.vec3(cam_x, cam_y, cam_z),
            look_at_pos,
            glm.vec3(0, 1, 0)
        )
    
    def get_projection_matrix(self) -> glm.mat4:
        return glm.perspective(math.radians(45.0), self.width / self.height, 1.0, 50000.0)
    
    def handle_rotation(self, rel_x, rel_y):
        if not self.is_transitioning:
            self.yaw += rel_x * 0.5
            self.pitch = max(-85, min(85, self.pitch - rel_y * 0.5))
    
    def handle_zoom(self, zoom_amount):
        if not self.is_transitioning:
            if self.target_planet is not None and self.zoom_distance is not None:
                # Zooming while focused on a planet
                # Set different minimum distances based on planet type
                if self.target_planet.config.name == "sun":
                    planet_min = max(200, self.target_planet.scale * 10)  # Sun minimum farther
                    planet_max = max(1000, self.target_planet.scale * 50)  # Sun maximum much farther
                else:
                    planet_min = max(15, self.target_planet.scale * 1.2)   # Planets minimum closer
                    planet_max = max(500, self.target_planet.scale * 20)   # Planets maximum reasonable
                
                # Correct zoom direction: positive zoom_amount = zoom in (decrease distance)
                self.zoom_distance = max(planet_min, min(planet_max, self.zoom_distance - zoom_amount))
            else:
                # Default zoom - correct direction
                self.distance = max(100, min(15000, self.distance - zoom_amount))
    
    def set_target(self, planet, zoom_distance=None):
        self.start_distance = self.distance
        self.start_yaw = self.yaw
        self.start_pitch = self.pitch
        self.start_position = glm.vec3(0, 0, 0) if self.target_planet is None else self.get_planet_position(self.target_planet)
        
        self.target_planet = planet
        self.target_position = self.get_planet_position(planet)
        
        if zoom_distance is None:
            if planet.config.name == "sun":
                zoom_distance = max(planet.scale * 30, 600)
            else:
                zoom_distance = max(planet.scale * 2.5, 30)
        
        self.target_distance = zoom_distance
        self.zoom_distance = zoom_distance
        
        self.target_yaw = 45.0
        self.target_pitch = -20.0
        
        self.is_transitioning = True
        self.transition_time = 0.0
    
    def clear_target(self):
        self.start_distance = self.zoom_distance if self.zoom_distance else self.distance
        self.start_yaw = self.yaw
        self.start_pitch = self.pitch
        self.start_position = self.get_planet_position(self.target_planet) if self.target_planet else glm.vec3(0, 0, 0)
        
        self.target_distance = 3000.0
        self.target_yaw = 45.0
        self.target_pitch = -30.0
        self.target_position = glm.vec3(0, 0, 0)
        
        self.target_planet = None
        self.zoom_distance = None
        
        self.is_transitioning = True
        self.transition_time = 0.0
    
    def update(self, dt):
        """Update camera transitions"""
        if self.is_transitioning:
            self.transition_time += dt
            if self.transition_time >= self.transition_duration:
                # Transition complete
                self.is_transitioning = False
                self.distance = self.target_distance
                self.yaw = self.target_yaw
                self.pitch = self.target_pitch

class Starfield:
    def __init__(self, num_stars=2000):
        self.num_stars = num_stars
        self.star_positions = []
        self.star_colors = []
        self.star_brightness = []
        
        # OpenGL buffers
        self.VAO = None
        self.VBO_pos = None
        self.VBO_color = None
        
        self._generate_stars()
        self._setup_opengl_buffers()
    
    def _generate_stars(self):
        """Generate random star positions and colors"""
        np.random.seed(42)  # For consistent star pattern
        
        # Generate stars in a large sphere around the solar system
        for i in range(self.num_stars):
            # Random spherical coordinates
            phi = np.random.uniform(0, 2 * np.pi)  # azimuth
            theta = np.random.uniform(0, np.pi)    # polar angle
            radius = np.random.uniform(8000, 20000)  # Distance from center
            
            # Convert to cartesian coordinates
            x = radius * np.sin(theta) * np.cos(phi)
            y = radius * np.sin(theta) * np.sin(phi)
            z = radius * np.cos(theta)
            
            self.star_positions.extend([x, y, z])
            
            # Generate star colors (mostly white/blue/yellow with some variety)
            star_type = np.random.random()
            brightness = np.random.uniform(0.3, 1.0)
            
            if star_type < 0.6:  # White stars
                color = [brightness, brightness, brightness]
            elif star_type < 0.8:  # Blue-white stars
                color = [brightness * 0.8, brightness * 0.9, brightness]
            elif star_type < 0.95:  # Yellow stars
                color = [brightness, brightness * 0.9, brightness * 0.7]
            else:  # Red stars
                color = [brightness, brightness * 0.6, brightness * 0.4]
            
            self.star_colors.extend(color)
            self.star_brightness.append(brightness)
    
    def _setup_opengl_buffers(self):
        try:
            self.VAO = glGenVertexArrays(1)
            self.VBO_pos = glGenBuffers(1)
            self.VBO_color = glGenBuffers(1)
            
            glBindVertexArray(self.VAO)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.VBO_pos)
            positions_array = np.array(self.star_positions, dtype=np.float32)
            glBufferData(GL_ARRAY_BUFFER, positions_array.nbytes, positions_array, GL_STATIC_DRAW)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(0)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.VBO_color)
            colors_array = np.array(self.star_colors, dtype=np.float32)
            glBufferData(GL_ARRAY_BUFFER, colors_array.nbytes, colors_array, GL_STATIC_DRAW)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(1)
            
            glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 0, None)
            glDisableVertexAttribArray(2)
            
            glBindVertexArray(0)
            
        except Exception as e:
            pass
    
    def render(self, shader):
        try:
            if self.VAO is None:
                return
            
            glEnable(GL_PROGRAM_POINT_SIZE)
            
            identity = glm.mat4(1.0)
            shader.set_mat4("model", glm.value_ptr(identity))
            shader.set_vec3("objectColor", [1.0, 1.0, 1.0])
            shader.set_vec3("lightPos", [0, 0, 0])
            shader.set_vec3("lightColor", [1.0, 1.0, 1.0])
            
            glBindVertexArray(self.VAO)
            glDrawArrays(GL_POINTS, 0, self.num_stars)
            glBindVertexArray(0)
            
            glDisable(GL_PROGRAM_POINT_SIZE)
            
        except Exception as e:
            pass
    
    def cleanup(self):
        try:
            if self.VAO:
                glDeleteVertexArrays(1, [self.VAO])
            if self.VBO_pos:
                glDeleteBuffers(1, [self.VBO_pos])
            if self.VBO_color:
                glDeleteBuffers(1, [self.VBO_color])
        except Exception as e:
            pass

class Planet:
    def __init__(self, config: PlanetConfig, loader: GLBLoader, scale: float, orbit_radius: float):
        self.config = config
        self.loader = loader
        self.scale = scale
        self.orbit_radius = orbit_radius
        
        self.orbit_speed = config.orbit_speed * 0.02
        
        if config.name == "sun":
            self.rotation_speed = 2.0
        else:
            direction = -1 if config.rotation_period < 0 else 1
            rotation_hours = abs(config.rotation_period)
            self.rotation_speed = direction * (360.0 / (rotation_hours * 3600)) * 100
        
        self.orbit_angle = np.random.uniform(0, 360)
        self.rotation_angle = 0
    
    def update(self, dt: float):
        self.orbit_angle = (self.orbit_angle + self.orbit_speed * dt) % 360
        self.rotation_angle = (self.rotation_angle + self.rotation_speed * dt) % 360
    
    def render(self, shader):
        try:
            model = glm.mat4(1.0)
            
            if self.config.name != "sun":
                orbit_x = self.orbit_radius * math.cos(math.radians(self.orbit_angle))
                orbit_z = self.orbit_radius * math.sin(math.radians(self.orbit_angle))
                model = glm.translate(model, glm.vec3(orbit_x, 0, orbit_z))
            
            # Special handling for Jupiter - fix incorrect pivot point
            if self.config.name == "jupiter":
                # Manually center Jupiter by offsetting its incorrect pivot point
                jupiter_center_offset = glm.vec3(-0.3, 0, 0)
                
                # Move to correct center, rotate, then move back
                model = glm.translate(model, jupiter_center_offset)
                model = glm.rotate(model, glm.radians(self.rotation_angle), glm.vec3(0, 1, 0))
                model = glm.translate(model, -jupiter_center_offset)
                
                model = glm.scale(model, glm.vec3(self.scale, self.scale, self.scale))
            else:
                model = glm.rotate(model, glm.radians(self.rotation_angle), glm.vec3(0, 1, 0))
                model = glm.scale(model, glm.vec3(self.scale, self.scale, self.scale))
            
            shader.set_mat4("model", glm.value_ptr(model))
            shader.set_vec3("objectColor", self.config.color)
            shader.set_vec3("lightPos", [0, 0, 0])
            shader.set_vec3("lightColor", [1.0, 1.0, 1.0])
            
            if self.loader:
                self.loader.render(shader.id)
        except Exception as e:
            pass
    
    def reset_position(self):
        """Reset planet to a random orbital position"""
        self.orbit_angle = np.random.uniform(0, 360)
        self.rotation_angle = 0

class SolarSystem:
    VISUAL_SIZES = {
        "sun": 20.0, "mercury": 1.0, "venus": 2.0, "earth": 2.2, "mars": 1.5,
        "jupiter": 12.0, "saturn": 10.0, "uranus": 4.0, "neptune": 3.8
    }
    
    PLANET_KEYS = {
        pygame.K_1: "sun", pygame.K_2: "mercury", pygame.K_3: "venus", pygame.K_4: "earth",
        pygame.K_5: "mars", pygame.K_6: "jupiter", pygame.K_7: "saturn", pygame.K_8: "uranus", pygame.K_9: "neptune"
    }
    
    def __init__(self):
        try:
            self._initialize_pygame()
            self._setup_opengl()
            self._load_shaders()
            
            self.camera = Camera(self.width, self.height)
            self._initialize_planets()
            
            # Store original orbital positions for reset functionality
            self.original_orbit_positions = {planet.config.name: planet.orbit_radius for planet in self.planets}
            
            self.paused = False
            self.clock = pygame.time.Clock()
            self.last_mouse_pos = None
            
            self.property_editor = PropertyEditorCommunicator(self)
            
        except Exception as e:
            traceback.print_exc()
            raise
    
    def _initialize_pygame(self):
        pygame.init()
        display_info = pygame.display.Info()
        self.width = min(1280, display_info.current_w - 100)
        self.height = min(720, display_info.current_h - 100)
        
        pygame.display.set_caption("Solar System - Simple")
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        
        try:
            self.display = pygame.display.set_mode((self.width, self.height), DOUBLEBUF|OPENGL)
        except Exception as e:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 2)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 1)
            self.display = pygame.display.set_mode((self.width, self.height), DOUBLEBUF|OPENGL)
    
    def _setup_opengl(self):
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glClearColor(0.0, 0.0, 0.05, 1.0)
    
    def _load_shaders(self):
        base_dir = Path(__file__).parent.resolve()
        vertex_path = base_dir / "shaders" / "vertex.glsl"
        fragment_path = base_dir / "shaders" / "fragment.glsl"
        
        if not vertex_path.exists() or not fragment_path.exists():
            raise FileNotFoundError("Shader files not found")
        
        self.shader = Shader(str(vertex_path), str(fragment_path))
    
    def _get_planet_configs(self) -> List[PlanetConfig]:
        return [
            PlanetConfig(
                name="sun",
                model_file="sun.glb",
                diameter=1392700,
                distance=0,
                mass=1988400.00,
                orbit_speed=0,
                rotation_period=587.28,
                color=(1.0, 1.0, 0.7),
                moons=0,
                has_rings=False
            ),
            PlanetConfig(
                name="mercury",
                model_file="mercury.glb",
                diameter=4879,
                distance=57.9,
                mass=0.33,
                orbit_speed=47.4,
                rotation_period=1407.6,
                color=(0.8, 0.8, 0.7),
                moons=0,
                has_rings=False
            ),
            PlanetConfig(
                name="venus",
                model_file="venus.glb",
                diameter=12104,
                distance=108.2,
                mass=4.87,
                orbit_speed=35.0,
                rotation_period=-5832.5,
                color=(0.9, 0.7, 0.4),
                moons=0,
                has_rings=False
            ),
            PlanetConfig(
                name="earth",
                model_file="earth.glb",
                diameter=12756,
                distance=149.6,
                mass=5.97,
                orbit_speed=29.8,
                rotation_period=23.9,
                color=(0.2, 0.4, 0.9),
                moons=1,
                has_rings=False
            ),
            PlanetConfig(
                name="mars",
                model_file="mars.glb",
                diameter=6792,
                distance=228.0,
                mass=0.642,
                orbit_speed=24.1,
                rotation_period=24.6,
                color=(0.9, 0.4, 0.2),
                moons=2,
                has_rings=False
            ),
            PlanetConfig(
                name="jupiter",
                model_file="jupiter.glb",
                diameter=142984,
                distance=778.5,
                mass=1898,
                orbit_speed=13.1,
                rotation_period=9.9,
                color=(0.9, 0.8, 0.6),
                moons=95,
                has_rings=True
            ),
            PlanetConfig(
                name="saturn",
                model_file="saturn.glb",
                diameter=120536,
                distance=1432.0,
                mass=568,
                orbit_speed=9.7,
                rotation_period=10.7,
                color=(0.95, 0.85, 0.65),
                moons=274,
                has_rings=True
            ),
            PlanetConfig(
                name="uranus",
                model_file="uranus.glb",
                diameter=51118,
                distance=2867.0,
                mass=86.8,
                orbit_speed=6.8,
                rotation_period=-17.2,
                color=(0.7, 0.85, 0.95),
                moons=28,
                has_rings=True
            ),
            PlanetConfig(
                name="neptune",
                model_file="neptune.glb",
                diameter=49528,
                distance=4515.0,
                mass=102,
                orbit_speed=5.4,
                rotation_period=16.1,
                color=(0.3, 0.5, 0.9),
                moons=16,
                has_rings=True
            )
        ]
    
    def _calculate_orbit_distances(self, planet_configs: List[PlanetConfig]) -> Dict[str, float]:
        max_real_distance = max(p.distance for p in planet_configs if p.name != "sun")
        distance_scale = 4000.0 / max_real_distance
        min_separation = 170.0  # sun radius (20) + buffer (150)
        
        orbit_distances = {"sun": 0}
        last_position = min_separation
        
        for planet in planet_configs[1:]:
            scaled_distance = planet.distance * distance_scale
            orbit_distances[planet.name] = max(scaled_distance, last_position + min_separation)
            last_position = orbit_distances[planet.name]
        
        return orbit_distances
    
    def _initialize_planets(self):
        base_dir = Path(__file__).parent.resolve()
        planet_configs = self._get_planet_configs()
        orbit_distances = self._calculate_orbit_distances(planet_configs)
        
        self.planets = []
        models_dir = base_dir / "models"
        
        if not models_dir.exists():
            models_dir.mkdir(exist_ok=True)
        
        for config in planet_configs:
            try:
                loader = GLBLoader(str(base_dir))
                model_path = models_dir / config.model_file
                
                if model_path.exists():
                    loader.load(config.model_file)
                    planet = Planet(
                        config=config,
                        loader=loader,
                        scale=self.VISUAL_SIZES[config.name],
                        orbit_radius=orbit_distances[config.name]
                    )
                    self.planets.append(planet)
                else:
                    pass
            except Exception as e:
                pass
        
        try:
            self.starfield = Starfield()
        except Exception as e:
            self.starfield = None
    
    def update(self, dt: float):
        try:
            self.camera.update(dt)
            
            self.property_editor.update()
            
            if not self.paused:
                for planet in self.planets:
                    planet.update(dt)
        except Exception as e:
            pass
    
    def render(self):
        try:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.shader.use()
            
            view = self.camera.get_view_matrix()
            projection = self.camera.get_projection_matrix()
            
            self.shader.set_mat4("projection", glm.value_ptr(projection))
            self.shader.set_mat4("view", glm.value_ptr(view))
            
            for planet in self.planets:
                if planet.loader:
                    planet.render(self.shader)
            
            if hasattr(self, 'starfield') and self.starfield:
                self.starfield.render(self.shader)
            
            pygame.display.flip()
            
        except Exception as e:
            pass
    
    def handle_events(self) -> bool:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return False
                    elif event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key in self.PLANET_KEYS:
                        self.select_planet(self.PLANET_KEYS[event.key])
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.last_mouse_pos = pygame.mouse.get_pos()
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.last_mouse_pos = None
                elif event.type == pygame.MOUSEMOTION and self.last_mouse_pos and pygame.mouse.get_pressed()[0]:
                    x, y = event.pos
                    rel_x = x - self.last_mouse_pos[0]
                    rel_y = y - self.last_mouse_pos[1]
                    self.camera.handle_rotation(rel_x, rel_y)
                    self.last_mouse_pos = (x, y)
                elif event.type == pygame.MOUSEWHEEL:
                    self.camera.handle_zoom(event.y * 30)
            
            return True
        except Exception as e:
            return True
    
    def run(self):
        running = True
        last_time = time.time()
        
        try:
            while running:
                current_time = time.time()
                dt = current_time - last_time
                last_time = current_time
                
                running = self.handle_events()
                self.update(dt)
                self.render()
                
                self.clock.tick(60)
        except Exception as e:
            traceback.print_exc()
        finally:
            self.cleanup()
            pygame.quit()
    
    def cleanup(self):
        try:
            for planet in self.planets:
                if planet.loader:
                    planet.loader.cleanup()
            
            if hasattr(self, 'shader') and self.shader.id:
                glDeleteProgram(self.shader.id)
            
            self.property_editor.cleanup()
            
            if hasattr(self, 'starfield') and self.starfield:
                self.starfield.cleanup()
        except Exception as e:
            pass
    
    def select_planet(self, planet_name):
        for planet in self.planets:
            if planet.config.name == planet_name:
                self.camera.set_target(planet)
                self.property_editor.show_planet_properties(planet)
                break
    
    def reset_all_simulation(self):
        try:
            original_configs = self._get_planet_configs()
            visual_sizes = self.VISUAL_SIZES
            
            for planet in self.planets:
                original_config = None
                for config in original_configs:
                    if config.name == planet.config.name:
                        original_config = config
                        break
                
                if original_config:
                    planet.config.diameter = original_config.diameter
                    planet.config.distance = original_config.distance
                    planet.config.mass = original_config.mass
                    planet.config.orbit_speed = original_config.orbit_speed
                    planet.config.rotation_period = original_config.rotation_period
                    
                    planet.orbit_speed = original_config.orbit_speed * 0.02
                    
                    if original_config.name == "sun":
                        planet.rotation_speed = 2.0
                    else:
                        direction = -1 if original_config.rotation_period < 0 else 1
                        rotation_hours = abs(original_config.rotation_period)
                        planet.rotation_speed = direction * (360.0 / (rotation_hours * 3600)) * 100
                    
                    if original_config.name in visual_sizes:
                        planet.scale = visual_sizes[original_config.name]
                
                planet.reset_position()
            
            # Restore original orbital positions instead of recalculating
            for planet in self.planets:
                if planet.config.name in self.original_orbit_positions:
                    planet.orbit_radius = self.original_orbit_positions[planet.config.name]
            
            self.camera.clear_target()
            self.camera.distance = 3000.0
            self.camera.yaw = 45.0
            self.camera.pitch = -30.0
            
        except Exception as e:
            pass

if __name__ == "__main__":
    try:
        system = SolarSystem()
        system.run()
        
    except Exception as e:
        traceback.print_exc()
        input("Press Enter to exit...")
    finally:
        try:
            pygame.quit()
        except:
            pass