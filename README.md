# Arducam_Capturing

Capturing the video with USB arducam.

## Setup (Raspberry Pi OS)

`libcamera` and `picamera2` are **not** available on PyPI — they are shipped as
compiled Debian packages for the system Python only. The venv must therefore be
built from the system interpreter with access to system site-packages.

```bash
# 1. System packages (once)
sudo apt install python3-libcamera python3-picamera2

# 2. Venv based on the system Python, with system packages visible
rm -rf .venv
uv venv --python /usr/bin/python3 --system-site-packages

# 3. Project dependencies (this does not install picamera2; it comes from apt)
uv sync

# 4. Verify
uv run python -c "import libcamera, picamera2; print('camera stack OK')"
```

If you ever see `ModuleNotFoundError: No module named 'libcamera'`, the venv was
created without `--system-site-packages`; recreate it with the commands above.
