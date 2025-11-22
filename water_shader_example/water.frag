#version 330

uniform sampler2D u_texture;
uniform float u_time;
uniform vec2 u_resolution;

in vec2 v_uv;
out vec4 f_color;

void main() {
    vec2 uv = v_uv;

    // Animated UV offsets for simple ripples
    float wave1 = sin(uv.y * 25.0 + u_time * 1.5) * 0.005;
    float wave2 = cos(uv.x * 20.0 + u_time * 1.1) * 0.005;
    uv += vec2(wave1, wave2);

    vec4 base = texture(u_texture, uv);
    vec3 tint = vec3(0.0, 0.3, 0.6);

    // Use resolution to create a subtle vertical gradient (darker at the top)
    float gradient = gl_FragCoord.y / u_resolution.y;
    vec3 color = mix(base.rgb, tint, 0.3 + 0.2 * gradient);

    f_color = vec4(color, base.a);
}
