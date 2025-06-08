#version 330 core
in vec3 FragPos;
in vec3 Normal;
in vec2 TexCoord;
in vec3 VertexColor;

out vec4 FragColor;

uniform vec3 objectColor;
uniform vec3 lightPos;
uniform vec3 lightColor;
uniform sampler2D texture_diffuse;

void main()
{
    // Check if this is a star point (no texture coordinates)
    // Stars are rendered as GL_POINTS with vertex colors
    if (TexCoord.x == 0.0 && TexCoord.y == 0.0 && length(Normal) < 0.1) {
        FragColor = vec4(VertexColor, 1.0);
        return;
    }

    // Ambient - increased for better visibility
    float ambientStrength = 0.25;
    vec3 ambient = ambientStrength * lightColor;
    
    // Diffuse 
    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    
    // Specular - enhanced for more shine
    float specularStrength = 0.7;
    vec3 viewDir = normalize(-FragPos); // Assume view is at (0,0,0)
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32);
    vec3 specular = specularStrength * spec * lightColor;
    
    // Result
    vec3 lightResult = (ambient + diffuse + specular);
    
    // Get texture color
    vec4 texColor = texture(texture_diffuse, TexCoord);
    
    // If texture has very low alpha, use the object color fully
    // This helps with orbit lines that don't have a texture
    if(texColor.a < 0.1) {
        // Enhance the brightness of non-textured objects (like orbits)
        FragColor = vec4(lightResult * objectColor * 1.3, 1.0);
    } else {
        // Enhance contrast for planets
        vec3 finalColor = lightResult * mix(objectColor, texColor.rgb, texColor.a);
        // Apply a slight contrast enhancement
        finalColor = finalColor * 1.1;
        FragColor = vec4(finalColor, texColor.a);
    }
}