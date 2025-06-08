# Solar System Simulator

An interactive 3D solar system simulator built with OpenGL and Python. Explore the planets of our solar system with realistic 3D models, orbital mechanics, and an intuitive property editor.

![Solar System Simulator](https://img.shields.io/badge/Python-3.7+-blue.svg)
![OpenGL](https://img.shields.io/badge/OpenGL-3.3+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **Interactive 3D Visualization**: Navigate through the solar system with mouse controls
- **Realistic Planet Models**: High-quality 3D models for all planets and the sun
- **Real-time Property Editor**: Modify planet properties like rotation speed, orbit speed, scale, and more
- **Authentic Solar System Data**: Based on real astronomical data including:
  - Planet diameters and distances
  - Orbital speeds and rotation periods
  - Number of moons and ring systems
- **Smooth Camera Controls**: Target specific planets with smooth transitions
- **Starfield Background**: Beautiful star field for immersive space experience
- **Pause/Resume Simulation**: Control simulation time

## Screenshots

*Add screenshots of your simulator here*

## Requirements

- Python 3.7+
- OpenGL 3.3+ compatible graphics card
- Required Python packages:
  - `pygame`
  - `PyOpenGL`
  - `numpy`
  - `PyGLM`

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/johndoniego/solar-system-simulator.git
   cd solar-system-simulator
   ```

2. **Install required dependencies:**
   ```bash
   pip install pygame PyOpenGL numpy PyGLM
   ```

3. **Run the simulator:**
   ```bash
   python main.py
   ```

## Controls

### Mouse Controls
- **Left Click + Drag**: Rotate camera around the solar system
- **Mouse Wheel**: Zoom in/out

### Keyboard Controls
- **Space**: Pause/Resume simulation
- **1-9**: Focus on specific planets:
  - `1` - Sun
  - `2` - Mercury
  - `3` - Venus
  - `4` - Earth
  - `5` - Mars
  - `6` - Jupiter
  - `7` - Saturn
  - `8` - Uranus
  - `9` - Neptune
- **Escape**: Exit application

## Property Editor

When you focus on a planet (using number keys 1-9), a property editor window opens allowing you to:

- Adjust rotation speed
- Modify orbital speed
- Change planet scale
- Reset planet position
- Reset all properties
- Reset entire simulation

## Project Structure

```
solar-system-simulator/
│
├── main.py                 # Main application file
├── run.py                  # Alternative runner with simpler interface
├── property_editor.py      # Real-time property editing interface
├── glb_loader.py          # 3D model loader for GLB files
├── shader.py              # OpenGL shader management
├── models/                # Planet 3D models
│   ├── sun.glb
│   ├── mercury.glb
│   ├── venus.glb
│   ├── earth.glb
│   ├── mars.glb
│   ├── jupiter.glb
│   ├── saturn.glb
│   ├── uranus.glb
│   └── neptune.glb
├── shaders/               # OpenGL shaders
│   ├── vertex.glsl
│   └── fragment.glsl
└── property_data/         # Runtime data for property editor
    ├── current_planet.json
    └── property_changes.json
```

## Technical Details

- **Graphics**: OpenGL 3.3+ with modern shader pipeline
- **3D Models**: GLB format models for all celestial bodies
- **Lighting**: Simple directional lighting from the sun
- **Camera**: Free-look camera with smooth planet targeting
- **Physics**: Simplified orbital mechanics for educational purposes

## Astronomical Data

The simulator uses real astronomical data:

| Planet  | Diameter (km) | Distance (million km) | Moons | Rings |
|---------|---------------|----------------------|-------|-------|
| Sun     | 1,392,700     | 0                    | 0     | No    |
| Mercury | 4,879         | 57.9                 | 0     | No    |
| Venus   | 12,104        | 108.2                | 0     | No    |
| Earth   | 12,756        | 149.6                | 1     | No    |
| Mars    | 6,792         | 228.0                | 2     | No    |
| Jupiter | 142,984       | 778.5                | 95    | Yes   |
| Saturn  | 120,536       | 1,432.0              | 274   | Yes   |
| Uranus  | 51,118        | 2,867.0              | 28    | Yes   |
| Neptune | 49,528        | 4,515.0              | 16    | Yes   |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- 3D planet models from various open-source astronomy projects
- OpenGL tutorials and documentation
- NASA for astronomical data and references

## Known Issues

- Large model files (>50MB) may cause slow loading on some systems
- Property editor requires Python tkinter (usually included with Python)

## Future Enhancements

- [ ] Add asteroid belt visualization
- [ ] Include planet moons
- [ ] Implement realistic physics simulation
- [ ] Add comet trajectories
- [ ] Include more detailed planetary information
- [ ] VR support for immersive exploration
