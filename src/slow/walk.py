"""Show semantic walk in embedding space with interactive visualization and path tracing"""

import argparse
import sys
import threading
from collections import deque

import dash
import numpy as np
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Input, Output

from src.slow.embed import embed  # Ensure this module is accessible

# Shared data structures
vs = deque()
buffer = ""
buffer_lock = threading.Lock()  # Lock for thread-safe buffer access

# Initialize Dash app
app = dash.Dash(__name__)

# Command-line arguments
parser = argparse.ArgumentParser(
    description="Visualize semantic walk in embedding space."
)
parser.add_argument(
    "--fps",
    type=int,
    default=5,
    help="Frames per second for the visualization (default: 5)",
)
parser.add_argument(
    "--path_length",
    type=int,
    default=50,
    help="Number of points for the path tracing effect (0 means no path) (default: 50)",
)
parser.add_argument(
    "--max_points",
    type=int,
    default=50000,
    help="Maximum number of points to keep in history (default: 50000)",
)
parser.add_argument(
    "--show_globe", action="store_true", help="Show the globe (unit sphere) wireframe"
)
parser.add_argument(
    "--track",
    action="store_true",
    help="Enable camera tracking to follow the current embedding",
)
args = parser.parse_args()

# Parameters
FPS = args.fps
PATH_LENGTH = args.path_length
MAX_POINTS = args.max_points
SHOW_GLOBE = args.show_globe
TRACK_CAMERA = args.track
INTERVAL = int(1000 / FPS)  # Interval in milliseconds

vs = deque(maxlen=MAX_POINTS)  # Maximum length of embeddings

app.layout = html.Div(
    [
        dcc.Graph(
            id="sphere-plot",
            style={
                "width": "100vw",
                "height": "100vh",
                "position": "absolute",
                "top": 0,
                "left": 0,
            },
        ),
        dcc.Interval(
            id="interval-component",
            interval=INTERVAL,  # Update based on fps
            n_intervals=0,
        ),
    ],
    style={"width": "100vw", "height": "100vh", "position": "relative"},
)


@app.callback(
    Output("sphere-plot", "figure"), Input("interval-component", "n_intervals")
)
def update_graph(n_intervals):
    global buffer, vs

    # Lock the buffer when reading to ensure thread safety
    with buffer_lock:
        current_buffer = buffer

    if current_buffer == "":
        # No data yet, return an empty figure
        fig = go.Figure()
    else:
        # Calculate the embedding of the current buffer
        v = embed(current_buffer, dimension=3)
        # Append the new embedding to vs
        vs.append(v)

        # Convert vs to a NumPy array
        vs_array = np.array(vs)
        # All points except the last one
        past_points = vs_array[:-1] if len(vs_array) > 1 else np.array([])
        # The current point
        current_point = vs_array[-1]
        # Points for the path tracing effect (last PATH_LENGTH points)
        if PATH_LENGTH > 0:
            path_points = (
                vs_array[-PATH_LENGTH:] if len(vs_array) >= PATH_LENGTH else vs_array
            )
        else:
            path_points = np.array([])

        data = []

        # Create globe wireframe if enabled
        if SHOW_GLOBE:
            # Create a wireframe sphere
            phi = np.linspace(0, np.pi, 20)
            theta = np.linspace(0, 2 * np.pi, 40)
            phi, theta = np.meshgrid(phi, theta)
            x = np.sin(phi) * np.cos(theta)
            y = np.sin(phi) * np.sin(theta)
            z = np.cos(phi)
            globe_trace = go.Surface(
                x=x,
                y=y,
                z=z,
                opacity=0.1,
                colorscale="Greys",
                showscale=False,
                hoverinfo="none",
            )
            data.append(globe_trace)

        # Create scatter plot for past points (excluding path points)
        if len(vs_array) > PATH_LENGTH:
            past_scatter_points = (
                vs_array[:-PATH_LENGTH] if PATH_LENGTH > 0 else vs_array[:-1]
            )
            past_trace = go.Scatter3d(
                x=past_scatter_points[:, 0],
                y=past_scatter_points[:, 1],
                z=past_scatter_points[:, 2],
                mode="markers",
                marker=dict(
                    size=2,
                    color="blue",
                    opacity=0.2,  # Less prominent
                ),
                name="Past Points",
            )
            data.append(past_trace)

        # Create scatter plot for path points
        if PATH_LENGTH > 0 and len(path_points) > 1:
            path_trace = go.Scatter3d(
                x=path_points[:, 0],
                y=path_points[:, 1],
                z=path_points[:, 2],
                mode="lines+markers",
                line=dict(color="green", width=4),
                marker=dict(size=3, color="green", opacity=0.8),
                name="Path Trace",
            )
            data.append(path_trace)

        # Create scatter plot for the current point
        current_trace = go.Scatter3d(
            x=[current_point[0]],
            y=[current_point[1]],
            z=[current_point[2]],
            mode="markers",
            marker=dict(
                size=6,
                color="red",
                opacity=1.0,  # Emphasized
            ),
            name="Current Point",
        )
        data.append(current_trace)

        # Draw a line from the origin to the current point
        line_trace = go.Scatter3d(
            x=[0, current_point[0]],
            y=[0, current_point[1]],
            z=[0, current_point[2]],
            mode="lines",
            line=dict(color="red", width=2),
            name="Current Direction",
        )
        data.append(line_trace)

        # Set the camera to follow the direction of the current embedding if tracking is enabled
        if TRACK_CAMERA:
            camera = dict(
                eye=dict(
                    x=current_point[0] * 2,
                    y=current_point[1] * 2,
                    z=current_point[2] * 2,
                ),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1),
            )
        else:
            # Default camera settings
            camera = dict(
                eye=dict(x=1.25, y=1.25, z=1.25),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1),
            )

        fig = go.Figure(data=data)

        fig.update_layout(
            scene=dict(
                aspectmode="data",
                xaxis=dict(range=[-1.1, 1.1], visible=False),
                yaxis=dict(range=[-1.1, 1.1], visible=False),
                zaxis=dict(range=[-1.1, 1.1], visible=False),
                camera=camera,
            ),
            margin=dict(l=0, r=0, b=0, t=0),
            showlegend=False,
            uirevision="constant",  # Preserve camera position and zoom
        )

    return fig


def read_and_stream():
    global buffer
    while True:
        try:
            # Read one character at a time
            char = sys.stdin.read(1)
            if not char:
                break  # EOF

            # Lock the buffer when modifying to ensure thread safety
            with buffer_lock:
                buffer += char

        except KeyboardInterrupt:
            break
        except EOFError:
            break


if __name__ == "__main__":
    # Start the reading thread
    reading_thread = threading.Thread(target=read_and_stream)
    reading_thread.daemon = True
    reading_thread.start()

    # Run the Dash app
    app.run_server(debug=True)
