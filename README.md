# Scheds and Kernel Manager (scx-km)

A comprehensive GUI application for managing Linux kernels and sched-ext CPU schedulers for **XeroLinux**.

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

![SCX](https://github.com/user-attachments/assets/f8df76f7-b3cb-42c5-92c4-84471ca37671)

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

P.S : This tool is also embedded in the **XeroLinux Toolkit**.

## Changelog

### Version 1.0.0

- Initial release
- Kernel management functionality
- Scheduler switching with live monitoring
- Scheduler persistence via systemd
- Categorized scheduler selection
- Multiple performance modes
- Real-time status updates
