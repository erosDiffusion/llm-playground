# Linux Mint: ComfyUI autostart (user systemd)

This documents the setup used on the local Mint box to start ComfyUI automatically at boot.

## What was done

1. Added a launcher script that runs ComfyUI from its venv and supports optional update-on-boot.
2. Added a user-level `systemd` unit (`comfyui.service`) and enabled it.
3. Confirmed it starts and serves on port `8188`.
4. Confirmed `linger` is enabled so user services can start at boot without interactive login.

## Why this pattern

- User services are safer than root services for desktop workflows.
- Boot launch and maintenance are separated:
  - startup path is reliable (`UPDATE_ON_BOOT=0` by default)
  - updates are optional and can be run manually or by a separate timer
- `COMFYUI_ARGS` handling disables shell globbing to preserve `--enable-cors-header "*"`.

## Install from templates

1. Copy the template `local-boot-user-systemd.service.template` to `~/.config/systemd/user/comfyui.service` and set `<COMFYUI_DIR>`.
2. Place `start_comfyui_service.sh` in your ComfyUI directory (or adapt `ExecStart` to where it lives).
3. Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now comfyui.service
```

4. Optional boot-without-login:

```bash
sudo loginctl enable-linger "$USER"
```

## Ops commands

```bash
systemctl --user status comfyui.service
journalctl --user -u comfyui.service -f
systemctl --user restart comfyui.service
systemctl --user stop comfyui.service
systemctl --user disable comfyui.service
```