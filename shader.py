from OpenGL.GL import *
import os

class Shader:
    def __init__(self, vertex_path, fragment_path):
        if not os.path.exists(vertex_path):
            raise FileNotFoundError(f"Vertex shader not found at: {vertex_path}")
        if not os.path.exists(fragment_path):
            raise FileNotFoundError(f"Fragment shader not found at: {fragment_path}")
        
        self.id = self._compile_shader(vertex_path, fragment_path)
    
    def _compile_shader(self, vertex_path, fragment_path):
        with open(vertex_path, 'r', encoding='utf-8') as f:
            vertex_src = f.read()
        with open(fragment_path, 'r', encoding='utf-8') as f:
            fragment_src = f.read()
        
        vertex = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vertex, vertex_src)
        glCompileShader(vertex)
        if not glGetShaderiv(vertex, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(vertex).decode()
            raise RuntimeError(f"Vertex shader compilation error:\n{error}")
        
        fragment = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fragment, fragment_src)
        glCompileShader(fragment)
        if not glGetShaderiv(fragment, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(fragment).decode()
            raise RuntimeError(f"Fragment shader compilation error:\n{error}")
        
        program = glCreateProgram()
        glAttachShader(program, vertex)
        glAttachShader(program, fragment)
        glLinkProgram(program)
        if not glGetProgramiv(program, GL_LINK_STATUS):
            error = glGetProgramInfoLog(program).decode()
            raise RuntimeError(f"Shader linking error:\n{error}")
        
        glDeleteShader(vertex)
        glDeleteShader(fragment)
        
        return program
    
    def use(self):
        glUseProgram(self.id)
    
    def set_mat4(self, name, value):
        glUniformMatrix4fv(glGetUniformLocation(self.id, name), 1, GL_FALSE, value)
    
    def set_vec3(self, name, value):
        glUniform3fv(glGetUniformLocation(self.id, name), 1, value)
    
    def set_float(self, name, value):
        glUniform1f(glGetUniformLocation(self.id, name), value)