import os
import numpy as np
from pygltflib import GLTF2
from PIL import Image
from OpenGL.GL import *
import io
from pathlib import Path

class GLBLoader:
    def __init__(self, base_path=""):
        self.base_path = base_path
        self.gltf = None
        self.meshes = []
        self.textures = []
        self.materials = []
        self.vaos = []
        self.vbos = []
        self.texture_ids = []

    def load(self, file_name):
        file_path = os.path.join(self.base_path, "models", file_name)
        
        try:
            self.gltf = GLTF2().load(file_path)
            
            self._clear_previous_data()
            self._load_textures()
            self._load_materials()
            self._load_meshes()
            self._setup_opengl_buffers()
        except Exception as e:
            raise

    def _clear_previous_data(self):
        self.meshes = []
        self.textures = []
        self.materials = []
        self.vaos = []
        self.vbos = []
        self.texture_ids = []

    def _load_textures(self):
        if not self.gltf.textures:
            return
            
        for texture in self.gltf.textures:
            texture_data = {
                'index': texture.source,
                'name': texture.name or f"texture_{len(self.textures)}"
            }
            
            if texture.source is not None and texture.source < len(self.gltf.images):
                image = self.gltf.images[texture.source]
                
                if hasattr(image, 'uri') and image.uri:
                    texture_path = os.path.join(self.base_path, "models", image.uri)
                    try:
                        with Image.open(texture_path) as img:
                            img = img.convert("RGBA")
                            texture_data.update({
                                'image': img,
                                'width': img.width,
                                'height': img.height,
                                'embedded': False
                            })
                    except Exception as e:
                        continue
                
                elif hasattr(image, 'bufferView'):
                    buffer_view = self.gltf.bufferViews[image.bufferView]
                    buffer = self.gltf.buffers[buffer_view.buffer]
                    data = self.gltf.get_data_from_buffer_uri(buffer.uri)
                    
                    start = buffer_view.byteOffset or 0
                    end = start + buffer_view.byteLength
                    image_data = data[start:end]
                    
                    try:
                        if hasattr(image, 'mimeType'):
                            if image.mimeType == 'image/png':
                                img = Image.open(io.BytesIO(image_data))
                            elif image.mimeType == 'image/jpeg':
                                img = Image.open(io.BytesIO(image_data))
                            else:
                                if hasattr(image, 'width') and hasattr(image, 'height'):
                                    img = Image.frombytes(
                                        'RGBA',
                                        (image.width, image.height),
                                        image_data,
                                        'raw',
                                        'RGBA',
                                        0, 1
                                    )
                                else:
                                    raise ValueError("Embedded texture missing dimensions")
                        else:
                            img = Image.open(io.BytesIO(image_data))
                        
                        texture_data.update({
                            'image': img,
                            'width': img.width,
                            'height': img.height,
                            'embedded': True
                        })
                    except Exception as e:
                        continue
                
                self.textures.append(texture_data)

    def _load_materials(self):
        if not self.gltf.materials:
            return
            
        for material in self.gltf.materials:
            pbr = material.pbrMetallicRoughness if hasattr(material, 'pbrMetallicRoughness') else None
            material_data = {
                'name': material.name or f"material_{len(self.materials)}",
                'baseColorFactor': pbr.baseColorFactor if pbr else [1.0, 1.0, 1.0, 1.0],
                'metallicFactor': pbr.metallicFactor if pbr else 0.5,
                'roughnessFactor': pbr.roughnessFactor if pbr else 0.5,
            }
            self.materials.append(material_data)

    def _load_meshes(self):
        if not self.gltf.meshes:
            return
                
        for mesh in self.gltf.meshes:
            mesh_data = {
                'name': mesh.name or f"mesh_{len(self.meshes)}",
                'primitives': []
            }
            
            for primitive in mesh.primitives:
                primitive_data = {
                    'attributes': {},
                    'indices': None,
                    'material': primitive.material if hasattr(primitive, 'material') else None
                }
                
                attribute_names = [attr for attr in dir(primitive.attributes) 
                                if not attr.startswith('_') and 
                                hasattr(primitive.attributes, attr)]
                
                for attr in attribute_names:
                    accessor_idx = getattr(primitive.attributes, attr)
                    if isinstance(accessor_idx, int):
                        accessor = self.gltf.accessors[accessor_idx]
                        buffer_view = self.gltf.bufferViews[accessor.bufferView]
                        buffer = self.gltf.buffers[buffer_view.buffer]
                        data = self.gltf.get_data_from_buffer_uri(buffer.uri)
                        
                        start = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
                        component_count = {
                            'SCALAR': 1,
                            'VEC2': 2,
                            'VEC3': 3,
                            'VEC4': 4,
                            'MAT2': 4,
                            'MAT3': 9,
                            'MAT4': 16
                        }.get(accessor.type, 3)
                        
                        dtype = self._get_numpy_dtype(accessor.componentType)
                        bytes_per_component = np.dtype(dtype).itemsize
                        total_bytes = accessor.count * component_count * bytes_per_component
                        buffer_data = data[start:start + total_bytes]
                        
                        try:
                            array = np.frombuffer(buffer_data, dtype=dtype)
                            if len(array) == accessor.count * component_count:
                                array = array.reshape((accessor.count, component_count))
                            primitive_data['attributes'][attr] = array
                        except ValueError as e:
                            continue
                
                if hasattr(primitive, 'indices') and isinstance(primitive.indices, int):
                    accessor = self.gltf.accessors[primitive.indices]
                    buffer_view = self.gltf.bufferViews[accessor.bufferView]
                    buffer = self.gltf.buffers[buffer_view.buffer]
                    data = self.gltf.get_data_from_buffer_uri(buffer.uri)
                    
                    start = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
                    dtype = self._get_numpy_dtype(accessor.componentType)
                    bytes_per_component = np.dtype(dtype).itemsize
                    total_bytes = accessor.count * bytes_per_component
                    buffer_data = data[start:start + total_bytes]
                    
                    try:
                        indices = np.frombuffer(buffer_data, dtype=dtype)
                        primitive_data['indices'] = indices
                    except ValueError as e:
                        continue
                
                mesh_data['primitives'].append(primitive_data)
            
            self.meshes.append(mesh_data)

    def _setup_opengl_buffers(self):
        try:
            for i, mesh in enumerate(self.meshes):
                for j, primitive in enumerate(mesh['primitives']):
                    try:
                        vao = glGenVertexArrays(1)
                        glBindVertexArray(vao)
                        
                        if 'POSITION' in primitive['attributes']:
                            positions = primitive['attributes']['POSITION'].astype(np.float32)
                            vbo = glGenBuffers(1)
                            glBindBuffer(GL_ARRAY_BUFFER, vbo)
                            glBufferData(GL_ARRAY_BUFFER, positions.nbytes, positions, GL_STATIC_DRAW)
                            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
                            glEnableVertexAttribArray(0)
                            self.vbos.append(vbo)
                        
                        if 'NORMAL' in primitive['attributes']:
                            normals = primitive['attributes']['NORMAL'].astype(np.float32)
                            vbo = glGenBuffers(1)
                            glBindBuffer(GL_ARRAY_BUFFER, vbo)
                            glBufferData(GL_ARRAY_BUFFER, normals.nbytes, normals, GL_STATIC_DRAW)
                            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
                            glEnableVertexAttribArray(1)
                            self.vbos.append(vbo)
                        
                        if 'TEXCOORD_0' in primitive['attributes']:
                            texcoords = primitive['attributes']['TEXCOORD_0'].astype(np.float32)
                            vbo = glGenBuffers(1)
                            glBindBuffer(GL_ARRAY_BUFFER, vbo)
                            glBufferData(GL_ARRAY_BUFFER, texcoords.nbytes, texcoords, GL_STATIC_DRAW)
                            glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 0, None)
                            glEnableVertexAttribArray(2)
                            self.vbos.append(vbo)
                        
                        if primitive['indices'] is not None:
                            indices = primitive['indices'].astype(np.uint32)
                            vbo = glGenBuffers(1)
                            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, vbo)
                            glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
                            self.vbos.append(vbo)
                        
                        self.vaos.append(vao)
                        
                        if primitive['material'] is not None and primitive['material'] < len(self.textures):
                            texture_data = self.textures[primitive['material']]
                            if 'image' in texture_data:
                                texture_id = glGenTextures(1)
                                glBindTexture(GL_TEXTURE_2D, texture_id)
                                
                                try:
                                    img = texture_data['image']
                                    
                                    if img.mode != 'RGBA':
                                        img = img.convert('RGBA')
                                    
                                    img_data = np.array(img)
                                    if len(img_data.shape) < 3 or img_data.shape[2] != 4:
                                        img_data = np.array(list(img.getdata()), np.uint8).reshape(img.height, img.width, 4)
                                    
                                    glTexImage2D(
                                        GL_TEXTURE_2D, 
                                        0, 
                                        GL_RGBA, 
                                        img.width, 
                                        img.height, 
                                        0, 
                                        GL_RGBA, 
                                        GL_UNSIGNED_BYTE, 
                                        img_data.flatten()
                                    )
                                    
                                    error = glGetError()
                                    
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                                    
                                    self.texture_ids.append(texture_id)
                                except Exception as tex_err:
                                    pass
                        
                        error = glGetError()
                    
                    except Exception as prim_err:
                        pass
        
        except Exception as e:
            pass

    def _get_numpy_dtype(self, component_type):
        if isinstance(component_type, int):
            type_map = {
                5120: np.int8,
                5121: np.uint8,
                5122: np.int16,
                5123: np.uint16,
                5125: np.uint32,
                5126: np.float32
            }
            return type_map.get(component_type, np.float32)
        return np.float32

    def render(self, shader_program):
        for i, mesh in enumerate(self.meshes):
            for j, primitive in enumerate(mesh['primitives']):
                vao_index = i * len(mesh['primitives']) + j
                if vao_index >= len(self.vaos):
                    continue
                
                glBindVertexArray(self.vaos[vao_index])
                
                if primitive['material'] is not None and primitive['material'] < len(self.materials):
                    material = self.materials[primitive['material']]
                    glUniform4f(
                        glGetUniformLocation(shader_program, "baseColor"), 
                        *material['baseColorFactor']
                    )
                    glUniform1f(
                        glGetUniformLocation(shader_program, "metallicFactor"), 
                        material['metallicFactor']
                    )
                    glUniform1f(
                        glGetUniformLocation(shader_program, "roughnessFactor"), 
                        material['roughnessFactor']
                    )
                
                if (primitive['material'] is not None and 
                    primitive['material'] < len(self.texture_ids) and 
                    primitive['material'] < len(self.textures) and 
                    'image' in self.textures[primitive['material']]):
                    
                    glActiveTexture(GL_TEXTURE0)
                    glBindTexture(GL_TEXTURE_2D, self.texture_ids[primitive['material']])
                    glUniform1i(glGetUniformLocation(shader_program, "texture_diffuse"), 0)
                
                if primitive['indices'] is not None:
                    glDrawElements(
                        GL_TRIANGLES, 
                        len(primitive['indices']), 
                        GL_UNSIGNED_INT, 
                        None
                    )
                else:
                    glDrawArrays(
                        GL_TRIANGLES, 
                        0, 
                        len(primitive['attributes']['POSITION'])
                    )
                
                glBindVertexArray(0)

    def cleanup(self):
        if self.vaos:
            glDeleteVertexArrays(len(self.vaos), self.vaos)
        if self.vbos:
            glDeleteBuffers(len(self.vbos), self.vbos)
        if self.texture_ids:
            glDeleteTextures(self.texture_ids)