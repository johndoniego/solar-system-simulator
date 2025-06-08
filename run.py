import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = ['numpy', 'pygame', 'PyOpenGL', 'PyOpenGL_accelerate', 'glm']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        for package in missing_packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def ensure_directories():
    """Ensure all required directories exist"""
    for directory in ['models', 'shaders']:
        os.makedirs(directory, exist_ok=True)

def create_shader_files():
    """Create shader files if they don't exist"""
    shader_dir = Path("shaders")
    
    # Vertex shader
    vertex_shader = """#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;
layout(location = 2) in vec3 aNormal;

out vec3 FragPos;
out vec3 Normal;
out vec3 Color;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

void main() {
    FragPos = vec3(model * vec4(aPos, 1.0));
    Normal = mat3(transpose(inverse(model))) * aNormal;
    Color = aColor;
    
    gl_Position = projection * view * vec4(FragPos, 1.0);
}"""

    # Fragment shader
    fragment_shader = """#version 330 core
in vec3 FragPos;
in vec3 Normal;
in vec3 Color;

out vec4 FragColor;

uniform vec3 lightPos;
uniform vec3 lightColor;
uniform vec3 objectColor;

void main() {
    // Ambient
    float ambientStrength = 0.3;
    vec3 ambient = ambientStrength * lightColor;
    
    // Diffuse
    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    
    vec3 result = (ambient + diffuse) * objectColor;
    
    // If color attributes were provided (e.g. for stars), use them
    if (length(Color) > 0.01) {
        result = Color;
    }
    
    FragColor = vec4(result, 1.0);
}"""

    if not (shader_dir / "vertex.glsl").exists():
        (shader_dir / "vertex.glsl").write_text(vertex_shader)
    
    if not (shader_dir / "fragment.glsl").exists():
        (shader_dir / "fragment.glsl").write_text(fragment_shader)

def create_dummy_models():
    """Create placeholder .glb files for models that might be missing"""
    model_dir = Path("models")
    
    # List of required model files
    model_files = [
        "sun.glb", "mercury.glb", "venus.glb", "earth.glb", 
        "mars.glb", "jupiter.glb", "saturn.glb", "uranus.glb", "neptune.glb"
    ]
    
    # Create empty placeholder files if they don't exist
    for model_file in model_files:
        model_path = model_dir / model_file
        if not model_path.exists():
            model_path.write_bytes(b'glTF\x02\x00\x00\x00\x0c\x00\x00\x00\x4a\x53\x4f\x4e\x7b\x7d\x00')

def create_glb_loader():
    """Create the GLB loader class file if it doesn't exist"""
    if Path("glb_loader.py").exists():
        return
    
    glb_loader_code = '''import os
from OpenGL.GL import *
import numpy as np
import ctypes

class GLBLoader:
    def __init__(self, base_path):
        self.base_path = base_path
        self.vao = None
        self.vbo = None
        self.vertex_count = 0
    
    def load(self, file_path):
        # In a real implementation, this would parse the GLB file
        # Here, we just create a simple sphere as a placeholder
        
        # Generate a sphere mesh
        radius = 1.0
        sectors = 36
        stacks = 18
        vertices = []
        
        for i in range(stacks + 1):
            V = i / stacks
            phi = V * np.pi
            
            for j in range(sectors + 1):
                U = j / sectors
                theta = U * 2 * np.pi
                
                # Calculate vertex position
                x = radius * np.sin(phi) * np.cos(theta)
                y = radius * np.cos(phi)
                z = radius * np.sin(phi) * np.sin(theta)
                
                # Calculate vertex normal
                nx = x / radius
                ny = y / radius
                nz = z / radius
                
                # Add vertex (position, color, normal)
                vertices.extend([x, y, z, 0.8, 0.8, 0.8, nx, ny, nz])
        
        # Create triangles
        indices = []
        for i in range(stacks):
            for j in range(sectors):
                first = i * (sectors + 1) + j
                second = first + sectors + 1
                
                indices.extend([first, second, first + 1])
                indices.extend([second, second + 1, first + 1])
        
        # Convert to numpy arrays
        vertices = np.array(vertices, dtype=np.float32)
        indices = np.array(indices, dtype=np.uint32)
        
        # Create VAO and VBO
        self.vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        ebo = glGenBuffers(1)
        
        glBindVertexArray(self.vao)
        
        # Vertices
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        
        # Position attribute
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 9 * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        
        # Color attribute
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 9 * 4, ctypes.c_void_p(3 * 4))
        glEnableVertexAttribArray(1)
        
        # Normal attribute
        glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, 9 * 4, ctypes.c_void_p(6 * 4))
        glEnableVertexAttribArray(2)
        
        self.vertex_count = len(indices)
        self.vbos = [vbo, ebo]
    
    def render(self, shader_program):
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.vertex_count, GL_UNSIGNED_INT, None)
    
    def cleanup(self):
        if self.vao:
            glDeleteVertexArrays(1, [self.vao])
            for vbo in self.vbos:
                glDeleteBuffers(1, [vbo])
'''
    Path("glb_loader.py").write_text(glb_loader_code)

def create_shader_class():
    """Create the Shader class file if it doesn't exist"""
    if Path("shader.py").exists():
        return
    
    shader_code = '''from OpenGL.GL import *
import numpy as np

class Shader:
    def __init__(self, vertex_path, fragment_path):
        # Read vertex shader code
        with open(vertex_path, 'r') as file:
            vertex_code = file.read()
            
        # Read fragment shader code
        with open(fragment_path, 'r') as file:
            fragment_code = file.read()
            
        # Compile shaders
        vertex = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vertex, vertex_code)
        glCompileShader(vertex)
        self._check_compile_errors(vertex, "VERTEX")
        
        fragment = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fragment, fragment_code)
        glCompileShader(fragment)
        self._check_compile_errors(fragment, "FRAGMENT")
        
        # Shader program
        self.id = glCreateProgram()
        glAttachShader(self.id, vertex)
        glAttachShader(self.id, fragment)
        glLinkProgram(self.id)
        self._check_compile_errors(self.id, "PROGRAM")
        
        # Delete shaders as they're linked into the program and no longer needed
        glDeleteShader(vertex)
        glDeleteShader(fragment)
        
    def use(self):
        glUseProgram(self.id)
        
    def set_bool(self, name, value):
        glUniform1i(glGetUniformLocation(self.id, name), int(value))
    
    def set_int(self, name, value):
        glUniform1i(glGetUniformLocation(self.id, name), value)
        
    def set_float(self, name, value):
        glUniform1f(glGetUniformLocation(self.id, name), value)
        
    def set_vec2(self, name, value):
        glUniform2fv(glGetUniformLocation(self.id, name), 1, value)
        
    def set_vec3(self, name, value):
        glUniform3fv(glGetUniformLocation(self.id, name), 1, value)
        
    def set_vec4(self, name, value):
        glUniform4fv(glGetUniformLocation(self.id, name), 1, value)
        
    def set_mat2(self, name, value):
        glUniformMatrix2fv(glGetUniformLocation(self.id, name), 1, GL_FALSE, value)
        
    def set_mat3(self, name, value):
        glUniformMatrix3fv(glGetUniformLocation(self.id, name), 1, GL_FALSE, value)
        
    def set_mat4(self, name, value):
        glUniformMatrix4fv(glGetUniformLocation(self.id, name), 1, GL_FALSE, value)
        
    def _check_compile_errors(self, shader, type):
        if type != "PROGRAM":
            if not glGetShaderiv(shader, GL_COMPILE_STATUS):
                info_log = glGetShaderInfoLog(shader).decode('utf-8')
                print(f"ERROR::SHADER_COMPILATION_ERROR of type: {type}\\n{info_log}\\n")
        else:
            if not glGetProgramiv(shader, GL_LINK_STATUS):
                info_log = glGetProgramInfoLog(shader).decode('utf-8')
                print(f"ERROR::PROGRAM_LINKING_ERROR of type: {type}\\n{info_log}\\n")
'''
    Path("shader.py").write_text(shader_code)

def run_application():
    """Run the main.py application"""
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
    except subprocess.CalledProcessError:
        return False
    except KeyboardInterrupt:
        pass
    return True

if __name__ == "__main__":
    check_dependencies()
    ensure_directories()
    create_shader_files()
    create_dummy_models()
    create_glb_loader()
    create_shader_class()
    run_application() 