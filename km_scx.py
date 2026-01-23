#!/usr/bin/env python3
"""
XeroLinux Kernel Manager & Scheduler Switcher
A comprehensive PyQt6 GUI for managing kernels and sched-ext schedulers
"""

import sys
import os
import subprocess
import json
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTextEdit, QGroupBox, QFrame,
    QMessageBox, QLineEdit, QTabWidget, QListWidget, QListWidgetItem,
    QSplitter, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QFont, QIcon, QPalette


class PackageInstallThread(QThread):
    """Background thread for installing packages with real-time output"""
    output_ready = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, packages, operation='install'):
        super().__init__()
        self.packages = packages
        self.operation = operation  # 'install' or 'remove'

    def run(self):
        """Run the installation/removal"""
        try:
            if self.operation == 'install':
                cmd = ['pkexec', 'pacman', '-S', '--noconfirm'] + self.packages
            else:  # remove
                cmd = ['pkexec', 'pacman', '-R', '--noconfirm'] + self.packages

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Stream output line by line
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.output_ready.emit(line.rstrip())

            process.wait()

            if process.returncode == 0:
                self.finished.emit(True, f"Successfully {self.operation}ed packages")
            else:
                self.finished.emit(False, f"Failed to {self.operation} packages (exit code: {process.returncode})")

        except Exception as e:
            self.finished.emit(False, f"Error: {e}")


class ScxctlMonitor(QThread):
    """Background thread to monitor scheduler status using scxctl"""
    status_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        """Monitor loop"""
        while self.running:
            status = self.get_scheduler_status()
            self.status_updated.emit(status)
            self.msleep(2000)

    def get_scheduler_status(self):
        """Get current scheduler status using scxctl"""
        try:
            result = subprocess.run(
                ['scxctl', 'get'],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                output = result.stdout.strip()

                if not output or "not running" in output.lower():
                    return {'active': False, 'name': 'EEVDF', 'mode': 'N/A'}

                if output.lower().startswith('running'):
                    parts = output.split()
                    if len(parts) >= 2:
                        scheduler_name = parts[1]
                        scheduler_display = f"scx_{scheduler_name.lower()}"

                        mode = "N/A"
                        if " in " in output and " mode" in output:
                            mode_part = output.split(" in ", 1)[1]
                            mode = mode_part.replace(" mode", "").strip()

                        return {
                            'active': True,
                            'name': scheduler_display,
                            'mode': mode
                        }

                return {'active': False, 'name': 'EEVDF', 'mode': 'N/A'}
            else:
                return {'active': False, 'name': 'EEVDF', 'mode': 'N/A'}

        except:
            return {'active': False, 'name': 'EEVDF', 'mode': 'N/A'}

    def stop(self):
        """Stop monitoring"""
        self.running = False


class KernelManagerTab(QWidget):
    """Kernel Manager Tab"""

    def __init__(self, log_callback):
        super().__init__()
        self.log = log_callback
        self.available_kernels = []
        self.installed_kernels = []
        self.setup_ui()
        self.scan_kernels()

    def setup_ui(self):
        """Setup kernel manager UI"""
        layout = QVBoxLayout(self)

        # Header with icon and description
        header_layout = QHBoxLayout()

        # Icon (using emoji)
        icon_label = QLabel("🐧")
        icon_label.setFont(QFont("Sans", 48))
        header_layout.addWidget(icon_label)

        # Title and description
        text_layout = QVBoxLayout()
        title = QLabel("Kernel Manager")
        title.setFont(QFont("Sans", 16, QFont.Weight.Bold))
        text_layout.addWidget(title)

        desc = QLabel("Install and manage Linux kernels with headers")
        text_layout.addWidget(desc)

        header_layout.addLayout(text_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Kernel lists
        lists_layout = QHBoxLayout()

        # Installed kernels
        installed_group = QGroupBox("📦 Installed Kernels")
        installed_layout = QVBoxLayout()
        self.installed_list = QListWidget()
        installed_layout.addWidget(self.installed_list)

        remove_btn = QPushButton("🗑️ Remove Selected")
        remove_btn.clicked.connect(self.remove_kernel)
        installed_layout.addWidget(remove_btn)

        installed_group.setLayout(installed_layout)
        lists_layout.addWidget(installed_group)

        # Available kernels
        available_group = QGroupBox("🌐 Available Kernels")
        available_layout = QVBoxLayout()
        self.available_list = QListWidget()
        available_layout.addWidget(self.available_list)

        install_btn = QPushButton("⬇️ Install Selected")
        install_btn.clicked.connect(self.install_kernel)
        available_layout.addWidget(install_btn)

        available_group.setLayout(available_layout)
        lists_layout.addWidget(available_group)

        layout.addLayout(lists_layout)

        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        refresh_btn = QPushButton("🔄 Refresh Kernel Lists")
        refresh_btn.clicked.connect(self.scan_kernels)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)

    def scan_kernels(self):
        """Scan for available and installed kernels"""
        self.log("Scanning for kernels...")

        try:
            # Get all available linux kernel packages
            result = subprocess.run(
                ['pacman', '-Ss', '^linux'],
                capture_output=True,
                text=True
            )

            # Parse output
            self.available_kernels = []
            for line in result.stdout.split('\n'):
                # Match lines like: extra/linux 6.6.1-1
                if line.strip() and not line.startswith(' '):
                    parts = line.split()
                    if len(parts) >= 2:
                        pkg_name = parts[0].split('/')[-1]
                        # Filter: must start with 'linux' and be a kernel (not firmware, docs, headers, etc)
                        if pkg_name.startswith('linux') and not any(x in pkg_name for x in [
                            'firmware', 'docs', 'api-headers', 'tools', 'meta', '-headers', 'linux-atm'
                        ]):
                            # Only add actual kernel packages (not headers)
                            if pkg_name == 'linux' or '-' in pkg_name:
                                self.available_kernels.append(pkg_name)

            # Get installed kernels (also filter out headers)
            result = subprocess.run(
                ['pacman', '-Q'],
                capture_output=True,
                text=True
            )

            self.installed_kernels = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    pkg_name = line.split()[0]
                    if pkg_name.startswith('linux') and not any(x in pkg_name for x in [
                        'firmware', 'docs', 'api-headers', 'tools', 'meta', '-headers', 'linux-atm'
                    ]):
                        if pkg_name == 'linux' or '-' in pkg_name:
                            self.installed_kernels.append(pkg_name)

            self.update_lists()
            self.log(f"✓ Found {len(self.available_kernels)} available kernels, {len(self.installed_kernels)} installed")

        except Exception as e:
            self.log(f"✗ Error scanning kernels: {e}")

    def update_lists(self):
        """Update the kernel lists"""
        self.installed_list.clear()
        self.available_list.clear()

        for kernel in sorted(self.installed_kernels):
            self.installed_list.addItem(kernel)

        for kernel in sorted(self.available_kernels):
            if kernel not in self.installed_kernels:
                self.available_list.addItem(kernel)

    def install_kernel(self):
        """Install selected kernel with headers"""
        selected = self.available_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a kernel to install")
            return

        kernel = selected.text()
        headers = f"{kernel}-headers"

        reply = QMessageBox.question(
            self,
            "Confirm Installation",
            f"Install {kernel} with {headers}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.log(f"→ Installing {kernel} and {headers}...")

            # Disable buttons during installation
            self.available_list.setEnabled(False)
            self.installed_list.setEnabled(False)

            # Create and start installation thread
            self.install_thread = PackageInstallThread([kernel, headers], 'install')
            self.install_thread.output_ready.connect(self.log)
            self.install_thread.finished.connect(self.on_install_finished)
            self.install_thread.start()

    def on_install_finished(self, success, message):
        """Handle installation completion"""
        self.log(message)

        # Re-enable UI
        self.available_list.setEnabled(True)
        self.installed_list.setEnabled(True)

        if success:
            self.log("✓ Installation completed successfully")
            self.scan_kernels()
        else:
            QMessageBox.critical(self, "Installation Failed", message)

    def remove_kernel(self):
        """Remove selected kernel"""
        selected = self.installed_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a kernel to remove")
            return

        kernel = selected.text()
        headers = f"{kernel}-headers"

        # Check if this is the running kernel
        try:
            running = subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.strip()
            if kernel in running:
                QMessageBox.critical(
                    self,
                    "Cannot Remove",
                    f"{kernel} is currently running!\n\nPlease reboot into another kernel first."
                )
                return
        except:
            pass

        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove {kernel} and {headers}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.log(f"→ Removing {kernel} and {headers}...")

            # Disable buttons during removal
            self.available_list.setEnabled(False)
            self.installed_list.setEnabled(False)

            # Create and start removal thread
            self.remove_thread = PackageInstallThread([kernel, headers], 'remove')
            self.remove_thread.output_ready.connect(self.log)
            self.remove_thread.finished.connect(self.on_remove_finished)
            self.remove_thread.start()

    def on_remove_finished(self, success, message):
        """Handle removal completion"""
        self.log(message)

        # Re-enable UI
        self.available_list.setEnabled(True)
        self.installed_list.setEnabled(True)

        if success:
            self.log("✓ Removal completed successfully")
            self.scan_kernels()
        else:
            QMessageBox.critical(self, "Removal Failed", message)


class SchedulerTab(QWidget):
    """Scheduler Switcher Tab"""

    def __init__(self, log_callback):
        super().__init__()
        self.log = log_callback
        self.available_schedulers = []
        self.kernel_supported = False
        self.setup_ui()

        # Start monitoring
        self.monitor = ScxctlMonitor()
        self.monitor.status_updated.connect(self.update_status_display)
        self.monitor.start()

        self.scan_schedulers()

    @staticmethod
    def humanize_scheduler_name(scheduler):
        """Convert scx_tickless to Tickless, etc"""
        if not scheduler or scheduler == "EEVDF":
            return scheduler

        # Remove scx_ prefix
        name = scheduler.replace('scx_', '')

        # Capitalize and handle special cases
        name_map = {
            'bpfland': 'BPFland',
            'beerland': 'Beerland',
            'rustland': 'Rustland',
            'lavd': 'LAVD',
            'p2dq': 'P2DQ',
        }

        return name_map.get(name, name.capitalize())

    @staticmethod
    def humanize_mode(mode):
        """Convert lowlatency to Low Latency, etc"""
        if not mode or mode == "N/A":
            return mode

        mode_map = {
            'auto': 'Auto',
            'gaming': 'Gaming',
            'lowlatency': 'Low Latency',
            'powersave': 'Power Save',
        }

        return mode_map.get(mode.lower(), mode.capitalize())

    def setup_ui(self):
        """Setup scheduler UI"""
        layout = QVBoxLayout(self)

        # Header with icon and description
        header_layout = QHBoxLayout()

        # Icon
        icon_label = QLabel("⚡")
        icon_label.setFont(QFont("Sans", 48))
        header_layout.addWidget(icon_label)

        # Title and description
        text_layout = QVBoxLayout()
        title = QLabel("Scheduler Switcher")
        title.setFont(QFont("Sans", 16, QFont.Weight.Bold))
        text_layout.addWidget(title)

        desc = QLabel("Manage sched-ext BPF CPU schedulers on the fly")
        text_layout.addWidget(desc)

        header_layout.addLayout(text_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Kernel support check
        layout.addWidget(self.create_kernel_check_panel())

        # Current status
        layout.addWidget(self.create_status_panel())

        # Scheduler selection
        layout.addWidget(self.create_selection_panel())

        # Control buttons
        layout.addWidget(self.create_control_buttons())

    def check_kernel_support(self):
        """Check if current kernel supports sched-ext"""
        try:
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
            kernel_version = result.stdout.strip()

            if os.path.exists('/sys/kernel/sched_ext'):
                return True, kernel_version, "✅ Sched-ext is SUPPORTED"

            version_parts = kernel_version.split('.')
            try:
                major = int(version_parts[0])
                minor = int(version_parts[1].split('-')[0])

                if major > 6 or (major == 6 and minor >= 12):
                    return False, kernel_version, "⚠️ Kernel 6.12+ but sched-ext not detected"
                else:
                    return False, kernel_version, f"❌ Requires kernel 6.12+"
            except:
                return False, kernel_version, "⚠️ Could not parse version"

        except Exception as e:
            return False, "Unknown", f"❌ Error: {e}"

    def create_kernel_check_panel(self):
        """Create kernel support check panel"""
        group = QGroupBox("⚙️ Kernel Support")
        layout = QVBoxLayout()

        kernel_supported, kernel_version, message = self.check_kernel_support()
        self.kernel_supported = kernel_supported

        version_label = QLabel(f"Kernel: {kernel_version}")
        version_label.setFont(QFont("Sans", 10, QFont.Weight.Bold))
        layout.addWidget(version_label)

        self.kernel_support_label = QLabel(message)
        layout.addWidget(self.kernel_support_label)

        group.setLayout(layout)
        return group

    def create_status_panel(self):
        """Create current status panel"""
        group = QGroupBox("📊 Current Status")
        layout = QVBoxLayout()

        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Active Scheduler:"))
        self.active_scheduler_label = QLabel("Checking...")
        self.active_scheduler_label.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        status_layout.addWidget(self.active_scheduler_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_label = QLabel("N/A")
        mode_layout.addWidget(self.mode_label)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        group.setLayout(layout)
        return group

    def create_selection_panel(self):
        """Create scheduler selection panel"""
        group = QGroupBox("🎯 Scheduler Selection")
        layout = QVBoxLayout()

        # Scheduler dropdown
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Scheduler:"))

        self.scheduler_combo = QComboBox()
        select_layout.addWidget(self.scheduler_combo)
        select_layout.addStretch()
        layout.addLayout(select_layout)

        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["auto", "gaming", "lowlatency", "powersave"])
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Persistence toggle
        persistence_layout = QHBoxLayout()
        self.persist_checkbox = QCheckBox("🔄 Persist scheduler after reboot")
        self.persist_checkbox.setToolTip("Enable systemd service to auto-start scheduler on boot")
        self.persist_checkbox.stateChanged.connect(self.toggle_persistence)
        persistence_layout.addWidget(self.persist_checkbox)
        persistence_layout.addStretch()
        layout.addLayout(persistence_layout)

        # Check initial persistence state
        QTimer.singleShot(500, self.check_persistence_state)

        group.setLayout(layout)
        return group

    def create_control_buttons(self):
        """Create control buttons"""
        frame = QFrame()
        layout = QHBoxLayout(frame)

        self.switch_btn = QPushButton("🔄 Switch/Start Scheduler")
        self.switch_btn.clicked.connect(self.switch_scheduler)
        self.switch_btn.setEnabled(False)

        self.stop_btn = QPushButton("⏹ Stop Scheduler")
        self.stop_btn.clicked.connect(self.stop_scheduler)
        self.stop_btn.setEnabled(False)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.scan_schedulers)

        layout.addStretch()
        layout.addWidget(self.switch_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.refresh_btn)
        layout.addStretch()

        return frame

    def scan_schedulers(self):
        """Scan for available schedulers"""
        self.log("Scanning for schedulers...")

        try:
            result = subprocess.run(
                ['scxctl', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                output = result.stdout.strip()

                if 'supported schedulers:' in output:
                    json_part = output.split('supported schedulers:', 1)[1].strip()
                    try:
                        scheduler_list = json.loads(json_part)
                        self.available_schedulers = [f'scx_{name}' for name in scheduler_list]
                    except:
                        pass

                self.log(f"✓ Found {len(self.available_schedulers)} schedulers")
                self.populate_scheduler_dropdown()

                if self.kernel_supported and self.available_schedulers:
                    self.switch_btn.setEnabled(True)
            else:
                self.log(f"✗ Failed to list schedulers")

        except Exception as e:
            self.log(f"✗ Error: {e}")

    def populate_scheduler_dropdown(self):
        """Populate dropdown with categorized schedulers"""
        self.scheduler_combo.clear()

        categories = {
            '🎮 Gaming': ['scx_rusty', 'scx_lavd', 'scx_bpfland'],
            '🖥️ Desktop': ['scx_cosmos', 'scx_flash'],
            '🖧 Servers': ['scx_layered', 'scx_flatcg', 'scx_tickless'],
            '⚡ Low Latency': ['scx_nest'],
            '🧪 Testing': ['scx_simple', 'scx_chaos', 'scx_userland'],
        }

        added = set()

        for category, schedulers in categories.items():
            available = [s for s in schedulers if s in self.available_schedulers and s not in added]

            if available:
                self.scheduler_combo.addItem(f"─── {category} ───", None)
                model = self.scheduler_combo.model()
                item = model.item(self.scheduler_combo.count() - 1)
                item.setEnabled(False)

                for sched in available:
                    self.scheduler_combo.addItem(f"  {sched}", sched)
                    added.add(sched)

        other = [s for s in self.available_schedulers if s not in added]
        if other:
            self.scheduler_combo.addItem("─── 📋 Other ───", None)
            model = self.scheduler_combo.model()
            item = model.item(self.scheduler_combo.count() - 1)
            item.setEnabled(False)

            for sched in sorted(other):
                self.scheduler_combo.addItem(f"  {sched}", sched)

        for i in range(self.scheduler_combo.count()):
            if self.scheduler_combo.itemData(i) is not None:
                self.scheduler_combo.setCurrentIndex(i)
                break

    def switch_scheduler(self):
        """Switch/start scheduler"""
        if not self.scheduler_combo.currentData():
            QMessageBox.warning(self, "Error", "Please select a scheduler!")
            return

        scheduler = self.scheduler_combo.currentData()
        mode = self.mode_combo.currentText()

        scheduler_name = scheduler.replace('scx_', '')

        status = self.monitor.get_scheduler_status()
        command = 'switch' if status['active'] else 'start'

        self.log(f"→ {command.capitalize()}ing {scheduler} ({mode})...")

        try:
            cmd = ['scxctl', command, '--sched', scheduler_name, '--mode', mode]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log(f"✓ {command.capitalize()}ed to {scheduler}")
                QTimer.singleShot(1000, lambda: self.monitor.status_updated.emit(
                    self.monitor.get_scheduler_status()
                ))
            else:
                self.log(f"✗ Failed: {result.stderr}")

        except Exception as e:
            self.log(f"✗ Error: {e}")

    def stop_scheduler(self):
        """Stop scheduler"""
        self.log("Stopping scheduler...")

        try:
            result = subprocess.run(['scxctl', 'stop'], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log("✓ Scheduler stopped")
            else:
                self.log(f"✗ Failed: {result.stderr}")

        except Exception as e:
            self.log(f"✗ Error: {e}")

    def update_status_display(self, status):
        """Update status display"""
        if status['active']:
            human_name = self.humanize_scheduler_name(status['name'])
            self.active_scheduler_label.setText(f"⚡ {human_name}")

            human_mode = self.humanize_mode(status['mode'])
            self.mode_label.setText(human_mode)
            self.stop_btn.setEnabled(True)
        else:
            self.active_scheduler_label.setText("EEVDF (Default)")
            self.mode_label.setText("N/A")
            self.stop_btn.setEnabled(False)

        if self.kernel_supported and self.available_schedulers:
            self.switch_btn.setEnabled(True)

    def check_persistence_state(self):
        """Check if scx scheduler service is enabled"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-enabled', 'scx.service'],
                capture_output=True,
                text=True
            )
            enabled = result.returncode == 0 and 'enabled' in result.stdout.lower()
            self.persist_checkbox.blockSignals(True)
            self.persist_checkbox.setChecked(enabled)
            self.persist_checkbox.blockSignals(False)
        except:
            pass

    def toggle_persistence(self, state):
        """Toggle scheduler persistence via systemd service"""
        try:
            if state == Qt.CheckState.Checked.value:
                # Get current scheduler and mode
                if not self.scheduler_combo.currentData():
                    QMessageBox.warning(self, "Error", "Please select a scheduler first!")
                    self.persist_checkbox.blockSignals(True)
                    self.persist_checkbox.setChecked(False)
                    self.persist_checkbox.blockSignals(False)
                    return

                scheduler = self.scheduler_combo.currentData()
                mode = self.mode_combo.currentText()
                scheduler_name = scheduler.replace('scx_', '')

                self.log(f"→ Enabling persistence for {scheduler} ({mode})...")

                # Create/update service file
                service_content = f"""[Unit]
Description=sched-ext BPF CPU Scheduler ({scheduler})
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/scxctl start --sched {scheduler_name} --mode {mode}
ExecStop=/usr/bin/scxctl stop
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

                # Write service file (requires root)
                temp_file = '/tmp/scx.service'
                with open(temp_file, 'w') as f:
                    f.write(service_content)

                # Copy to systemd and enable
                result = subprocess.run(
                    ['pkexec', 'sh', '-c',
                     f'cp {temp_file} /etc/systemd/system/scx.service && systemctl daemon-reload && systemctl enable scx.service'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    self.log(f"✓ {scheduler} will auto-start on boot ({mode} mode)")
                else:
                    self.log(f"✗ Failed to enable persistence: {result.stderr}")
                    self.persist_checkbox.blockSignals(True)
                    self.persist_checkbox.setChecked(False)
                    self.persist_checkbox.blockSignals(False)
            else:
                self.log("→ Disabling scheduler persistence...")
                cmd = ['pkexec', 'systemctl', 'disable', 'scx.service']

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    self.log("✓ Scheduler persistence disabled")
                else:
                    self.log(f"✗ Failed to disable persistence: {result.stderr}")
                    self.persist_checkbox.blockSignals(True)
                    self.persist_checkbox.setChecked(True)
                    self.persist_checkbox.blockSignals(False)

        except Exception as e:
            self.log(f"✗ Error: {e}")
            self.persist_checkbox.blockSignals(True)
            self.persist_checkbox.setChecked(not bool(state))
            self.persist_checkbox.blockSignals(False)

    def cleanup(self):
        """Cleanup on close"""
        self.monitor.stop()
        self.monitor.wait()


class XeroLinuxManager(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XeroLinux Kernel Manager & Scheduler Switcher")
        self.setMinimumSize(1000, 800)

        self.setup_ui()

    def setup_ui(self):
        """Setup main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Main title
        title_layout = QHBoxLayout()
        logo = QLabel("🐧")
        logo.setFont(QFont("Sans", 32))
        title_layout.addWidget(logo)

        title = QLabel("XeroLinux Kernel Manager & Scheduler Switcher")
        title.setFont(QFont("Sans", 18, QFont.Weight.Bold))
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Create log widget FIRST (before tabs that need it)
        log_group = QGroupBox("📋 Activity Log")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)

        # Tab widget (created after log_output exists)
        self.tabs = QTabWidget()

        # Kernel manager tab
        self.kernel_tab = KernelManagerTab(self.log)
        self.tabs.addTab(self.kernel_tab, "🐧 Kernel Manager")

        # Scheduler tab (only if scxctl is available)
        if self.check_scxctl():
            self.scheduler_tab = SchedulerTab(self.log)
            self.tabs.addTab(self.scheduler_tab, "⚡ Scheduler Switcher")
        else:
            dummy = QWidget()
            dummy_layout = QVBoxLayout(dummy)
            dummy_layout.addWidget(QLabel("⚠️ scxctl not found. Install scx-tools to enable this feature."))
            self.tabs.addTab(dummy, "⚡ Scheduler Switcher")

        layout.addWidget(self.tabs)

        # Add log panel at the bottom
        layout.addWidget(log_group)

        self.log("XeroLinux Manager initialized")

    def check_scxctl(self):
        """Check if scxctl is available"""
        try:
            result = subprocess.run(['which', 'scxctl'], capture_output=True)
            return result.returncode == 0
        except:
            return False

    def log(self, message):
        """Add message to log"""
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        """Cleanup on exit"""
        if hasattr(self, 'scheduler_tab') and hasattr(self.scheduler_tab, 'cleanup'):
            self.scheduler_tab.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = XeroLinuxManager()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
