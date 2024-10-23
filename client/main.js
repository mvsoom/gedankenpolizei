import * as THREE from 'three';
import { GUI } from 'three/addons/libs/lil-gui.module.min.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { Pass, FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { LuminosityShader } from 'three/addons/shaders/LuminosityShader.js';
import { SobelOperatorShader } from 'three/addons/shaders/SobelOperatorShader.js';
import { LensDistortionPassGen } from 'three-lens-distortion';
import { vertexShader, fragmentShader } from './shaders.js';

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

// Controls GUI
let gui; // Declare gui globally
let controlsVisible = false; // Track the visibility of controls

// Webcam stream
const NEAR_CLIPPING = 2012;
const FAR_CLIPPING = 4000;
const Z_OFFSET = 706;
const POINT_SIZE = 2;

// Text display
const TEXT_CANVAS_WIDTH = 600;
const TEXT_CANVAS_HEIGHT = 480;
const MAX_TEXT_WIDTH = TEXT_CANVAS_WIDTH - 40;

const FONT_SIZE = 20;
const FONT_FAMILY = 'Arial';
const TEXT_STYLE = `rgba(255, 255, 255, 1.0)`;

const LINE_HEIGHT = 24;
const TEXT_X_OFFSET = 20;
const TEXT_Y_OFFSET = 50;

// Audio
const AUDIO_GAIN = 5.0;
const CLICK_SOUND_DURATION = 80; // msec

// Websocket
const WS_VIDEO_URL = 'ws://localhost:8765';
const WS_VIDEO_FPS = 100; // msec
const WS_VIDEO_RETRY = 500; // msec

const WS_TEXT_URL = 'ws://localhost:8766';
const WS_TEXT_RETRY = 500; // msec

// Scene
let scene, camera, renderer, composer, bloomPass, effectSobel, lensDistortionPass;
let mouse, center;
const initialCameraPosition = new THREE.Vector3(-63.984445903689256, 64.01760287088358, 686.1194448349208);
let targetCameraPosition = initialCameraPosition.clone();
let textMesh;
let textBuffer = ""; // List of text lines
let cameraLocked = true; // Flag to lock the camera

// Variables for PositionalAudio
let listener, pinkNoise, gainNode, currentGain = AUDIO_GAIN;
let isMuted = false; // Flag to mute the sound

// Add event listener to start button
const startButton = document.getElementById('startButton');
startButton.addEventListener('click', init);

// Request webcam permission immediately
const webcamstream = navigator.mediaDevices.getUserMedia({ video: true });

// ---------------------------------------------------------------------------
// Setup scene and websockets
// ---------------------------------------------------------------------------
async function init() {
    // Remove overlay after click
    const overlay = document.getElementById('overlay');
    overlay.remove();

    const container = document.createElement('div');
    document.body.appendChild(container);

    // Setup camera
    camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 1, 10000);
    camera.position.copy(initialCameraPosition);

    // Setup scene and renderer
    scene = new THREE.Scene();
    center = new THREE.Vector3();
    center.z = -1000;

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setAnimationLoop(animate);
    container.appendChild(renderer.domElement);

    // Setup postprocessing
    composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));

    // Bloom pass
    bloomPass = new UnrealBloomPass(
        new THREE.Vector2(window.innerWidth, window.innerHeight),
        1.5, // Strength
        0.4, // Radius
        0.85 // Threshold
    );
    composer.addPass(bloomPass);

    // Color to grayscale conversion
    const effectGrayScale = new ShaderPass(LuminosityShader);
    composer.addPass(effectGrayScale);

    // Sobel operator
    effectSobel = new ShaderPass(SobelOperatorShader);
    effectSobel.uniforms['resolution'].value.x = window.innerWidth * window.devicePixelRatio;
    effectSobel.uniforms['resolution'].value.y = window.innerHeight * window.devicePixelRatio;
    effectSobel.enabled = false;
    composer.addPass(effectSobel);

    // Lens distortion
    const LensDistortionPass = LensDistortionPassGen({ THREE, Pass, FullScreenQuad });
    lensDistortionPass = new LensDistortionPass({
        distortion: new THREE.Vector2(0.1, 0.1),
        principalPoint: new THREE.Vector2(0.0, 0.0),
        focalLength: new THREE.Vector2(1.0, 1.0),
        skew: 0.0
    });
    composer.addPass(lensDistortionPass);

    // Handle user input
    mouse = new THREE.Vector3(0, 0, 1);
    document.addEventListener('mousemove', onDocumentMouseMove);
    document.addEventListener('mouseleave', onDocumentMouseLeave);
    window.addEventListener('resize', onWindowResize);
    document.addEventListener('wheel', onDocumentMouseWheel);

    document.addEventListener('touchstart', onDocumentTouchStart, false);
    document.addEventListener('touchmove', onDocumentTouchMove, false);

    document.addEventListener('keydown', onDocumentKeyDown);

    // Hide the GUI by default
    gui = new GUI();
    gui.hide();

    // Add bloom controls to GUI
    const bloomFolder = gui.addFolder('Bloom');
    bloomFolder.add(bloomPass, 'strength', 0, 3, 0.01).name('Strength');
    bloomFolder.add(bloomPass, 'radius', 0, 1, 0.01).name('Radius');
    bloomFolder.add(bloomPass, 'threshold', 0, 1, 0.01).name('Threshold');
    bloomFolder.open();

    // Add Sobel edge detection enable/disable control to GUI
    const sobelFolder = gui.addFolder('Sobel Edge Detection');
    sobelFolder.add(effectSobel, 'enabled').name('Enable');
    sobelFolder.open();

    // Add lens distortion controls to GUI
    const lensDistortionFolder = gui.addFolder('Lens Distortion');
    lensDistortionFolder.add(lensDistortionPass.distortion, 'x', -1, 1, 0.01).name('Distortion X');
    lensDistortionFolder.add(lensDistortionPass.distortion, 'y', -1, 1, 0.01).name('Distortion Y');
    lensDistortionFolder.add(lensDistortionPass.principalPoint, 'x', -0.5, 0.5, 0.01).name('Principal Point X');
    lensDistortionFolder.add(lensDistortionPass.principalPoint, 'y', -0.5, 0.5, 0.01).name('Principal Point Y');
    lensDistortionFolder.add(lensDistortionPass.focalLength, 'x', 0, 2, 0.01).name('Focal Length X');
    lensDistortionFolder.add(lensDistortionPass.focalLength, 'y', 0, 2, 0.01).name('Focal Length Y');
    lensDistortionFolder.add(lensDistortionPass, 'skew', -Math.PI / 2, Math.PI / 2, 0.01).name('Skew');
    lensDistortionFolder.open();

    setupWebcam(webcamstream);
    setupTextCanvas();
    connectWebSocketVideo();
    connectWebSocketText();
    setupAudio();
}

function animate() {
    if (!cameraLocked) {
        camera.position.lerp(targetCameraPosition, 0.05);
        camera.lookAt(center);
    }
    composer.render(); // Use composer instead of renderer
}

// ---------------------------------------------------------------------------
// Audio
// ---------------------------------------------------------------------------
function setupAudio() {
    listener = new THREE.AudioListener();
    camera.add(listener);
    pinkNoise = createPinkNoise(listener.context);

    // Create GainNode to control pinkNoise volume
    gainNode = listener.context.createGain();
    gainNode.gain.value = currentGain;

    // Add gain control to Controls GUI
    const audioFolder = gui.addFolder('Audio');

    const gainControl = audioFolder.add(gainNode.gain, 'value', 0.0, AUDIO_GAIN * 2, 1).name('Volume').listen();
    gainControl.onChange((value) => {
        if (!isMuted) {
            currentGain = AUDIO_GAIN; // Update current gain value when not muted
        }
    });
}

function normalRandom() {
    let u = 0, v = 0;
    while (u === 0) u = Math.random(); // Converting [0,1) to (0,1)
    while (v === 0) v = Math.random();
    return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}

function createPinkNoise(audioContext) {
    const bufferSize = 4096;
    const node = audioContext.createScriptProcessor(bufferSize, 1, 1);
    let b0, b1, b2, b3, b4, b5, b6;
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0;

    node.onaudioprocess = function (e) {
        const output = e.outputBuffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            const white = normalRandom();
            b0 = 0.99886 * b0 + white * 0.0555179;
            b1 = 0.99332 * b1 + white * 0.0750759;
            b2 = 0.96900 * b2 + white * 0.1538520;
            b3 = 0.86650 * b3 + white * 0.3104856;
            b4 = 0.55000 * b4 + white * 0.5329522;
            b5 = -0.7616 * b5 - white * 0.0168980;
            output[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
            output[i] *= 0.11; // (roughly) compensate for gain
            b6 = white * 0.115926;

            output[i] /= 400; // Normalize the pink noise
            output[i] /= Math.sqrt(1 - i / bufferSize); // Fade out the pink noise
        }
    };

    return node;
}

function playClickSound() {
    // Start and stop the pink noise after a short duration
    pinkNoise.connect(gainNode).connect(listener.context.destination);
    setTimeout(() => {
        pinkNoise.disconnect();
    }, CLICK_SOUND_DURATION);
}

function toggleMute(mute) {
    if (mute) {
        currentGain = gainNode.gain.value; // Remember the current gain
        gainNode.gain.value = 0;
    } else {
        gainNode.gain.value = currentGain; // Restore the remembered gain
    }
    isMuted = mute;
}

// ---------------------------------------------------------------------------
// Setup webcam stream and transformation to 3D
// ---------------------------------------------------------------------------
async function setupWebcam(webcamstream) {
    const video = document.getElementById('video');
    const stream = await webcamstream;
    video.srcObject = stream;

    video.onloadedmetadata = () => {
        // Use video's native width and height
        const nativeWidth = video.videoWidth;
        const nativeHeight = video.videoHeight;

        const texture = new THREE.VideoTexture(video);
        texture.minFilter = THREE.NearestFilter;

        const geometry = new THREE.BufferGeometry();
        const vertices = new Float32Array(nativeWidth * nativeHeight * 3);
        for (let i = 0, j = 0, l = vertices.length; i < l; i += 3, j++) {
            vertices[i] = j % nativeWidth;
            vertices[i + 1] = Math.floor(j / nativeWidth);
        }
        geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));

        // Rest of the material and mesh setup remains the same
        const material = new THREE.ShaderMaterial({
            uniforms: {
                'map': { value: texture },
                'width': { value: TEXT_CANVAS_WIDTH },
                'height': { value: TEXT_CANVAS_HEIGHT },
                'nearClipping': { value: NEAR_CLIPPING },
                'farClipping': { value: FAR_CLIPPING },
                'pointSize': { value: POINT_SIZE },
                'zOffset': { value: Z_OFFSET }
            },
            vertexShader: vertexShader,
            fragmentShader: fragmentShader,
            blending: THREE.AdditiveBlending,
            depthTest: false,
            depthWrite: false,
            transparent: true
        });

        const mesh = new THREE.Points(geometry, material);
        scene.add(mesh);

        const webcamFolder = gui.addFolder('Webcam');

        webcamFolder.add(material.uniforms.nearClipping, 'value', 1, 10000, 1.0).name('Near Clipping');
        webcamFolder.add(material.uniforms.farClipping, 'value', 1, 10000, 1.0).name('Far Clipping');
        webcamFolder.add(material.uniforms.pointSize, 'value', 1, 10, 1.0).name('Point Size');
        webcamFolder.add(material.uniforms.zOffset, 'value', 0, 4000, 1.0).name('Z Offset');
    };
}

// ---------------------------------------------------------------------------
// Setup text canvas to display incoming text
// ---------------------------------------------------------------------------
function setupTextCanvas() {
    const canvas = document.createElement('canvas');
    canvas.width = TEXT_CANVAS_WIDTH;
    canvas.height = TEXT_CANVAS_HEIGHT;
    const context = canvas.getContext('2d');

    const textTexture = new THREE.CanvasTexture(canvas);
    textTexture.needsUpdate = true;

    const textMaterial = new THREE.MeshBasicMaterial({
        map: textTexture,
        transparent: true,
    });
    const textGeometry = new THREE.PlaneGeometry(TEXT_CANVAS_WIDTH, TEXT_CANVAS_HEIGHT);
    textMesh = new THREE.Mesh(textGeometry, textMaterial);
    textMesh.position.set(0, 0, 100);
    scene.add(textMesh);
}

// ---------------------------------------------------------------------------
// Setup retrying websocket for binary MJPEG out stream
// ---------------------------------------------------------------------------
function connectWebSocketVideo() {
    const socket = new WebSocket(WS_VIDEO_URL);
    socket.binaryType = 'arraybuffer';

    socket.onopen = () => {
        console.log('WebSocket connection for video opened');
        setInterval(() => sendFrame(socket), WS_VIDEO_FPS);
    };

    socket.onclose = () => {
        console.log('WebSocket connection for video closed, retrying...');
        setTimeout(connectWebSocketVideo, WS_VIDEO_RETRY);
    };

    socket.onerror = (error) => {
        console.log('WebSocket video error:', error);
        socket.close();
    };
}

// Send video frame through WebSocket
function sendFrame(socket) {
    const video = document.getElementById('video');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
        if (blob && socket && socket.readyState === WebSocket.OPEN) {
            blob.arrayBuffer().then(buffer => {
                socket.send(buffer);
            });
            console.log('Sent video frame');
        }
    }, 'image/jpeg');
}

// ---------------------------------------------------------------------------
// Setup retrying websocket for binary text in stream
// ---------------------------------------------------------------------------
function connectWebSocketText() {
    const socket = new WebSocket(WS_TEXT_URL);
    socket.binaryType = 'arraybuffer';

    socket.onopen = () => {
        console.log('WebSocket connection for text opened');
    };

    // Decode incoming text messages from possibly incomplete binary UTF-8 chunks
    const decoder = new TextDecoder('utf-8', { stream: true });

    socket.onmessage = (event) => {
        const text = decoder.decode(event.data, { stream: true });
        console.log('Received message:', text);
        if (text) {
            // Add text chunk to textBuffer (a list of lines)
            textBuffer += text;

            updateTextCanvas();

            if (text.trim().length !== 0)
                playClickSound();
        }
    };

    socket.onclose = () => {
        console.log('WebSocket connection for text closed, retrying...');
        setTimeout(connectWebSocketText, WS_TEXT_RETRY);
    };

    socket.onerror = (error) => {
        console.log('WebSocket text error:', error);
        socket.close();
    };
}

// Update the text canvas with new messages
function updateTextCanvas() {
    const canvas = textMesh.material.map.image;
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.font = `bold ${FONT_SIZE}px ${FONT_FAMILY}`;
    context.fillStyle = TEXT_STYLE;
    context.textAlign = 'left';

    const MAX_TEXT_WIDTH = canvas.width - TEXT_X_OFFSET * 2;
    const maxLines = Math.floor((canvas.height - TEXT_Y_OFFSET) / LINE_HEIGHT);
    let currentY = TEXT_Y_OFFSET;

    let wrappedText = '';
    let lastWhitespaceIndex = -1;
    let lineStartIndex = 0;

    for (let i = 0; i < textBuffer.length; i++) {
        let char = textBuffer[i];
        wrappedText += char;

        // Handle newlines as hard wraps
        if (char === '\n') {
            lineStartIndex = wrappedText.length;
            lastWhitespaceIndex = -1;
            continue;
        }

        if (/\s/.test(char)) {
            lastWhitespaceIndex = wrappedText.length - 1;
        }

        let currentLine = wrappedText.substring(lineStartIndex);
        let lineWidth = context.measureText(currentLine).width;

        if (lineWidth > MAX_TEXT_WIDTH) {
            if (lastWhitespaceIndex >= lineStartIndex) {
                // Insert a newline *at* the last whitespace position
                wrappedText = wrappedText.substring(0, lastWhitespaceIndex) + '\n' + wrappedText.substring(lastWhitespaceIndex);
                lineStartIndex = lastWhitespaceIndex;
            } else {
                // No whitespace found, but must wrap anyway; insert a newline before the current character to break the line
                wrappedText = wrappedText.substring(0, wrappedText.length - 1) + '\n' + char;
                lineStartIndex = wrappedText.length;
            }
            lastWhitespaceIndex = -1;
        }
    }

    let visibleText = wrappedText.split('\n');
    if (visibleText.length > maxLines) {
        visibleText = visibleText.slice(-maxLines);
    }
    for (let line of visibleText) {
        context.fillText(line, TEXT_X_OFFSET, currentY);
        currentY += LINE_HEIGHT;
    }

    textBuffer = visibleText.join('\n');

    textMesh.material.map.needsUpdate = true;
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    composer.setSize(window.innerWidth, window.innerHeight); // Update composer size
    effectSobel.uniforms['resolution'].value.x = window.innerWidth * window.devicePixelRatio;
    effectSobel.uniforms['resolution'].value.y = window.innerHeight * window.devicePixelRatio;
}

function onDocumentMouseMove(event) {
    if (!cameraLocked) {
        mouse.x = (event.clientX - window.innerWidth / 2) * 8;
        mouse.y = (event.clientY - window.innerHeight / 2) * 8;
        targetCameraPosition.set(mouse.x, -mouse.y, camera.position.z);
    }
}

function onDocumentMouseLeave(event) {
    if (!cameraLocked) {
        targetCameraPosition.copy(initialCameraPosition);
    }
}

function onDocumentMouseWheel(event) {
    camera.position.z += event.deltaY * 0.5;
}

function onDocumentTouchStart(event) {
    if (event.touches.length === 1 && !cameraLocked) {
        mouse.x = (event.touches[0].clientX - window.innerWidth / 2) * 8;
        mouse.y = (event.touches[0].clientY - window.innerHeight / 2) * 8;
        targetCameraPosition.set(mouse.x, -mouse.y, camera.position.z);
    }
}

function onDocumentTouchMove(event) {
    if (event.touches.length === 1 && !cameraLocked) {
        mouse.x = (event.touches[0].clientX - window.innerWidth / 2) * 8;
        mouse.y = (event.touches[0].clientY - window.innerHeight / 2) * 8;
        targetCameraPosition.set(mouse.x, -mouse.y, camera.position.z);
    }
}

function onDocumentKeyDown(event) {
    if (event.code === 'Space') {
        cameraLocked = !cameraLocked;
        console.log('Camera (un)locked at:', camera.position);
    } else if (event.code === 'Delete') {
        textBuffer = "";
        updateTextCanvas();
    } else if (event.key === 'm') {
        toggleMute(!isMuted);
    } else if (event.key === 'c') {
        controlsVisible = !controlsVisible;
        if (controlsVisible) {
            gui.show();
        } else {
            gui.hide();
        }
    } else if (event.key === 'h') {
        const infoBox = document.getElementById('infoBox');
        if (infoBox.style.display === 'none') {
            infoBox.style.display = 'block';
        } else {
            infoBox.style.display = 'none';
        }
    }
}