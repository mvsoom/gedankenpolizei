import argparse
import os

# Installed system-wide in `apt-install` file
from screeninfo import get_monitors  # type: ignore

monitors = list(get_monitors())


def get_display_info(display_name):
    for monitor in monitors:
        if monitor.name == display_name:
            return monitor.width, monitor.height
    return None, None


def main(args):
    p_display = args.primary
    s_display = args.secondary

    p_width, p_height = get_display_info(p_display)
    s_width, s_height = get_display_info(s_display)

    if p_width is None or s_width is None:
        print("Error: Could not find display dimensions.")
        return

    x_off = -(s_width - p_width) // 2
    y_off = -(s_height - p_height) // 2

    cmd = (
        f"xrandr --output {s_display} --fb {s_width}x{s_height} "
        f"--panning {p_width}x{p_height} --mode {s_width}x{s_height} "
        f"--transform 1,0,{x_off},0,1,{y_off},0,0,1"
    )

    print(cmd)
    os.system(cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Center the primary display output on a secondary display."
    )
    parser.add_argument(
        "--primary", type=str, required=True, help="Primary display name"
    )
    parser.add_argument(
        "--secondary", type=str, required=True, help="Secondary display name"
    )
    args = parser.parse_args()

    main(args)
