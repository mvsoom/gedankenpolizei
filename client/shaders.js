export const vertexShader = `
    uniform sampler2D map;
    uniform float width;
    uniform float height;
    uniform float nearClipping, farClipping;
    uniform float pointSize;
    uniform float zOffset;
    varying vec2 vUv;
    const float XtoZ = 1.11146;
    const float YtoZ = 0.83359;
    void main() {
        vUv = vec2(position.x / width, position.y / height);
        vec4 color = texture2D(map, vUv);
        float depth = (color.r + color.g + color.b) / 3.0;
        float z = (1.0 - depth) * (farClipping - nearClipping) + nearClipping;
        vec4 pos = vec4(
            (position.x / width - 0.5) * z * XtoZ,
            (position.y / height - 0.5) * z * YtoZ,
            -z + zOffset,
            1.0);
        gl_PointSize = pointSize;
        gl_Position = projectionMatrix * modelViewMatrix * pos;
    }
`;

export const fragmentShader = `
    uniform sampler2D map;
    varying vec2 vUv;
    void main() {
        vec4 color = texture2D(map, vUv);
        gl_FragColor = vec4(color.r, color.g, color.b, 0.2);
    }
`;