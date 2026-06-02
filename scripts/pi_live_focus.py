import os
import shutil
import subprocess
import sys

import paramiko


HOST = os.environ.get("PI_HOST", "10.131.212.253")
USER = os.environ.get("PI_USER", "kk")
PASSWORD = os.environ.get("PI_PASSWORD")


def main() -> int:
    if not PASSWORD:
        print("PI_PASSWORD is required", file=sys.stderr)
        return 2

    ffplay = shutil.which("ffplay") or shutil.which("ffplay.exe")
    if not ffplay:
        print("ffplay not found in PATH", file=sys.stderr)
        return 2

    remote_cmd = (
        "rpicam-vid -t 0 --width 1280 --height 720 --framerate 30 "
        "--codec h264 --inline --intra 30 --shutter 8500 --gain 1.0 "
        "--awbgains 1.9,2.6 --brightness 0.0 --contrast 1.0 "
        "--saturation 1.0 --sharpness 1.0 --denoise cdn_off --nopreview -o -"
    )

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST,
        username=USER,
        password=PASSWORD,
        timeout=10,
        auth_timeout=10,
        banner_timeout=10,
        look_for_keys=False,
        allow_agent=False,
    )

    transport = client.get_transport()
    if transport is None:
        raise RuntimeError("SSH transport unavailable")

    channel = transport.open_session()
    channel.exec_command(remote_cmd)

    player = subprocess.Popen(
        [
            ffplay,
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-framedrop",
            "-probesize",
            "32",
            "-analyzeduration",
            "0",
            "-sync",
            "ext",
            "-f",
            "h264",
            "-window_title",
            "Pi AI Camera Live Focus",
            "-",
        ],
        stdin=subprocess.PIPE,
    )

    try:
        while player.poll() is None:
            if channel.recv_ready():
                data = channel.recv(65536)
                if not data:
                    break
                try:
                    player.stdin.write(data)
                    player.stdin.flush()
                except BrokenPipeError:
                    break
            elif channel.exit_status_ready():
                break
    finally:
        try:
            if player.stdin:
                player.stdin.close()
        except Exception:
            pass
        if player.poll() is None:
            player.terminate()
        channel.close()
        client.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
