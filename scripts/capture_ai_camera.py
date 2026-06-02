import argparse
import posixpath
import re
import sys
import time
from pathlib import Path

import paramiko


DEFAULT_HOST = "10.131.212.253"
DEFAULT_USER = "kk"
DEFAULT_PASSWORD = "kk1355315"
REMOTE_DIR = "/tmp/eai_camera_captures"

# Keep these values fixed between captures so the training set is not affected
# by auto exposure, auto gain, or auto white balance changing frame to frame.
CAMERA_ARGS = [
    "--width",
    "4056",
    "--height",
    "3040",
    "--quality",
    "95",
    "--encoding",
    "jpg",
    "--shutter",
    "8500",
    "--gain",
    "1.0",
    "--awbgains",
    "1.9,2.6",
    "--brightness",
    "0.0",
    "--contrast",
    "1.0",
    "--saturation",
    "1.0",
    "--sharpness",
    "1.0",
    "--denoise",
    "cdn_off",
    "--nopreview",
    "--immediate",
]


def safe_stem_and_suffix(name: str) -> tuple[str, str]:
    path = Path(name)
    suffix = path.suffix or ".jpg"
    if suffix.lower() not in {".jpg", ".jpeg"}:
        raise ValueError("只支持 .jpg 或 .jpeg，训练图片格式要保持一致")
    stem = path.stem if path.suffix else name
    stem = stem.strip()
    if not stem:
        raise ValueError("图片名不能为空")
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', stem):
        raise ValueError("图片名不能包含 Windows 文件名非法字符")
    return stem, suffix


def next_local_path(folder: Path, requested_name: str) -> Path:
    stem, suffix = safe_stem_and_suffix(requested_name)
    candidate = folder / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = folder / f"{stem}{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def run_remote_capture(client: paramiko.SSHClient, remote_path: str) -> None:
    quoted_args = " ".join(shell_quote(arg) for arg in CAMERA_ARGS)
    command = (
        f"mkdir -p {shell_quote(REMOTE_DIR)} && "
        f"rm -f {shell_quote(remote_path)} && "
        f"rpicam-still {quoted_args} -o {shell_quote(remote_path)}"
    )
    stdin, stdout, stderr = client.exec_command(command, timeout=45)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    if exit_code != 0:
        detail = "\n".join(part for part in [out, err] if part)
        raise RuntimeError(f"远端拍照失败，退出码 {exit_code}\n{detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture one Raspberry Pi AI Camera image to this folder.")
    parser.add_argument("name", help="本地图片名，例如 苹果.jpg")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"树莓派 IP，默认 {DEFAULT_HOST}")
    parser.add_argument("--user", default=DEFAULT_USER, help=f"SSH 用户名，默认 {DEFAULT_USER}")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="SSH 密码")
    args = parser.parse_args()

    local_folder = Path(__file__).resolve().parent / "photo"
    local_folder.mkdir(exist_ok=True)
    local_path = next_local_path(local_folder, args.name)
    remote_name = f"{int(time.time() * 1000)}_{local_path.name}"
    remote_path = posixpath.join(REMOTE_DIR, remote_name)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            args.host,
            username=args.user,
            password=args.password,
            timeout=10,
            auth_timeout=10,
            banner_timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )
        run_remote_capture(client, remote_path)
        with client.open_sftp() as sftp:
            sftp.get(remote_path, str(local_path))
            try:
                sftp.remove(remote_path)
            except OSError:
                pass
    except Exception as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return 1
    finally:
        client.close()

    print(str(local_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
