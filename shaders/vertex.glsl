#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;
layout (location = 2) in vec2 aTexCoord;

out vec3 FragPos;
out vec3 Normal;
out vec2 TexCoord;
out vec3 VertexColor;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

void main()
{
    FragPos = vec3(model * vec4(aPos, 1.0));
    
    // Check if this is a star (no texture coordinates and normals are used for color)
    bool isStar = (aTexCoord.x == 0.0 && aTexCoord.y == 0.0 && length(aNormal) > 0.1);
    
    if (isStar) {
        // For stars: use normal attribute as color, set point size
        VertexColor = aNormal;
        Normal = vec3(0.0, 0.0, 0.0); // Zero normal indicates star to fragment shader
        gl_PointSize = 2.0; // Set star point size
    } else {
        // For planets: normal lighting calculations
        Normal = mat3(transpose(inverse(model))) * aNormal;
        VertexColor = vec3(1.0, 1.0, 1.0); // Default color for planets
    }
    
    // Pass texture coordinates
    TexCoord = aTexCoord;
    
    gl_Position = projection * view * model * vec4(aPos, 1.0);
}