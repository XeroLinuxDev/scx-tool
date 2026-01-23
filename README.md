# Scheds and Kernel Manager (scx-km)

A comprehensive PyQt6 GUI application for managing Linux kernels and sched-ext BPF CPU schedulers on Arch Linux and derivatives.

![License](https://img.shields.io/badge/license-GPL3-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Arch%20Linux-blue.svg)

## Features

### 🐧 Kernel Manager
- **Install/Remove Kernels**: Easily manage multiple Linux kernels with automatic header installation
- **Real-time Installation**: Live output during package operations
- **Smart Detection**: Automatically scans for available and installed kernels from official and Chaotic-AUR repositories
- **One-Click Operations**: Simple interface for kernel management

### ⚡ Scheduler Switcher
- **Live Scheduler Switching**: Switch between sched-ext BPF CPU schedulers on the fly without rebooting
- **Real-time Monitoring**: Continuous status updates showing active scheduler and mode
- **Categorized Schedulers**: Organized by use case (Gaming, Desktop, Servers, Low Latency, Testing)
- **Persistence Support**: Enable schedulers to auto-start on boot via systemd service
- **Multiple Modes**: Support for auto, gaming, lowlatency, and powersave modes
- **Kernel Compatibility Check**: Automatic detection of sched-ext kernel support

### 🎯 Supported Schedulers

#### Gaming Optimized
- `scx_rusty` - General-purpose gaming scheduler
- `scx_lavd` - Latency-aware virtual deadline scheduler
- `scx_bpfland` - BPF-based scheduler for gaming workloads

#### Desktop Optimized
- `scx_cosmos` - Balanced desktop performance
- `scx_flash` - Fast interactive response

#### Server Optimized
- `scx_layered` - Multi-layer scheduling for servers
- `scx_flatcg` - Flat cgroup scheduler
- `scx_tickless` - Reduced timer interrupts

#### Low Latency
- `scx_nest` - Ultra-low latency scheduler

#### Testing/Development
- `scx_simple` - Simple reference implementation
- `scx_chaos` - Randomized scheduling for testing
- `scx_userland` - Userspace scheduling framework

## Requirements

### Dependencies
- `python` (3.11+)
- `python-pyqt6`
- `pacman`
- `scx-scheds` - sched-ext BPF scheduler collection
- `scx-tools` - scxctl utility for scheduler management
- `polkit` - For privilege escalation

### Kernel Requirements
- Linux kernel 6.12+ with sched-ext support
- Recommended kernels:
  - `linux-cachyos`
  - `linux-xero`
  - Any kernel compiled with `CONFIG_SCHED_CLASS_EXT=y`

## Installation

### From Source (Arch Linux)

1. Clone or download the repository with these files:
   - `PKGBUILD`
   - `km_scx.py`
   - `scx-km.desktop`

2. Build and install:
```bash
makepkg -si
```

### Manual Installation

```bash
# Install dependencies
sudo pacman -S python python-pyqt6 scx-scheds scx-tools polkit

# Copy the script
sudo install -Dm755 km_scx.py /usr/bin/scx-km

# Copy desktop file
sudo install -Dm644 scx-km.desktop /usr/share/applications/scx-km.desktop
```

## Usage

### Launch the Application

From terminal:
```bash
scx-km
```

Or launch from your application menu under **System** → **Scheds and Kernel Manager**

### Managing Kernels

1. Navigate to the **Kernel Manager** tab
2. View installed kernels in the left panel
3. Browse available kernels in the right panel
4. Select a kernel and click **Install** or **Remove**
5. Monitor installation progress in the activity log

### Managing Schedulers

1. Navigate to the **Scheduler Switcher** tab
2. Check kernel compatibility status
3. Select your desired scheduler from the dropdown
4. Choose a performance mode (auto, gaming, lowlatency, powersave)
5. Click **Switch/Start Scheduler** to activate
6. Enable **Persist scheduler after reboot** to auto-start on boot

### Scheduler Persistence

When you enable persistence:
- The application automatically creates a systemd service
- The service is configured with your selected scheduler and mode
- The scheduler will start automatically on boot
- You can disable persistence at any time to return to default EEVDF

The systemd service is dynamically updated whenever you enable persistence with a different scheduler or mode.

## Screenshots

*Screenshots coming soon*

## How It Works

### Kernel Management
- Uses `pacman` to search, install, and remove kernel packages
- Automatically detects and filters kernel packages (excluding firmware, docs, tools)
- Installs both kernel and headers packages together
- Provides real-time installation output

### Scheduler Management
- Uses `scxctl` from scx-tools to manage schedulers
- Monitors scheduler status every 2 seconds
- Supports switching between schedulers without stopping
- Creates/updates systemd service for boot persistence
- Checks `/sys/kernel/sched_ext` for kernel support

## Troubleshooting

### "scxctl not found" Error
Install scx-tools:
```bash
sudo pacman -S scx-tools
```

### Kernel doesn't support sched-ext
Install a compatible kernel:
```bash
sudo pacman -S linux-cachyos
```

### Persistence not working
Ensure systemd service is properly created:
```bash
systemctl status scx.service
```

### Permission Issues
The application uses `pkexec` for privilege escalation. Ensure polkit is installed and configured.

## Development

### Project Structure
```
scx-km/
├── PKGBUILD           # Arch Linux package build file
├── km_scx.py          # Main Python application
├── scx-km.desktop     # Desktop entry file
└── README.md          # This file
```

### Contributing
Contributions are welcome! Please feel free to submit pull requests or open issues.

## Credits

- **Developer**: DarkXero
- **Project**: XeroLinux
- **Website**: https://xerolinux.xyz

## License

This project is licensed under the GPL-3.0 License - see the LICENSE file for details.

## Related Projects

- [scx-scheds](https://github.com/sched-ext/scx) - sched-ext BPF scheduler collection
- [scx-tools](https://github.com/sched-ext/scx) - Tools for managing sched-ext schedulers
- [XeroLinux](https://xerolinux.xyz) - Custom Arch Linux distribution

## Changelog

### Version 1.0.0
- Initial release
- Kernel management functionality
- Scheduler switching with live monitoring
- Scheduler persistence via systemd
- Categorized scheduler selection
- Multiple performance modes
- Real-time status updates
