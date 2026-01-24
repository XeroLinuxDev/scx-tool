#!/usr/bin/env python3
"""
XeroLinux Scheduler Switcher Tool
A comprehensive PyQt6 GUI for managing sched-ext schedulers
"""

import sys
import os
import subprocess
import json
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTextEdit, QGroupBox, QFrame,
    QMessageBox, QLineEdit, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QFont, QIcon, QPalette


class ScxctlMonitor(QThread):
    """Background thread to monitor scheduler status using scxctl"""
    status_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        """Monitor loop"""
        # Check immediately on start (no delay)
        status = self.get_scheduler_status()
        self.status_updated.emit(status)

        while self.running:
            self.msleep(500)  # Only 500ms between checks for very responsive updates
            status = self.get_scheduler_status()
            self.status_updated.emit(status)

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


class SchedulerTab(QWidget):
    """Scheduler Switcher Tab"""

    def __init__(self, log_callback):
        super().__init__()
        self.log = log_callback
        self.available_schedulers = []
        self.kernel_supported = False
        self.setup_ui()

        # Get and display status IMMEDIATELY (before any blocking operations)
        self.monitor = ScxctlMonitor()
        initial_status = self.monitor.get_scheduler_status()

        # Start monitor thread
        self.monitor.status_updated.connect(self.update_status_display)
        self.monitor.start()

        # Display the initial status NOW
        self.update_status_display(initial_status)

        # THEN scan schedulers (which might take time but status is already shown)
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
        layout.setContentsMargins(5, 0, 5, 5)  # Remove top margin
        layout.setSpacing(5)  # Compact spacing

        # Kernel support check
        layout.addWidget(self.create_kernel_check_panel())

        # Separator line - text based for visibility
        separator1 = QLabel("─" * 60)  # Shorter for narrow window
        separator1.setStyleSheet("QLabel { color: #666666; }")
        layout.addWidget(separator1)

        # Current status
        layout.addWidget(self.create_status_panel())

        # Separator line - text based for visibility
        separator2 = QLabel("─" * 60)  # Shorter for narrow window
        separator2.setStyleSheet("QLabel { color: #666666; }")
        layout.addWidget(separator2)

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
        # Add modes with humanized display names but keep technical names as data
        modes = [
            ("Auto", "auto"),
            ("Gaming", "gaming"),
            ("Low Latency", "lowlatency"),
            ("Power Save", "powersave")
        ]
        for display_name, value in modes:
            self.mode_combo.addItem(display_name, value)
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

        # Check initial persistence state immediately
        QTimer.singleShot(0, self.check_persistence_state)

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
                    display_name = self.humanize_scheduler_name(sched)
                    self.scheduler_combo.addItem(f"  {display_name}", sched)
                    added.add(sched)

        other = [s for s in self.available_schedulers if s not in added]
        if other:
            self.scheduler_combo.addItem("─── 📋 Other ───", None)
            model = self.scheduler_combo.model()
            item = model.item(self.scheduler_combo.count() - 1)
            item.setEnabled(False)

            for sched in sorted(other):
                display_name = self.humanize_scheduler_name(sched)
                self.scheduler_combo.addItem(f"  {display_name}", sched)

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
        mode = self.mode_combo.currentData()  # Use currentData instead of currentText

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
                mode = self.mode_combo.currentData()  # Use currentData instead of currentText
                scheduler_name = scheduler.replace('scx_', '')

                self.log(f"→ Enabling persistence for {scheduler} ({mode})...")

                # Create/update service file with better timing and error handling
                service_content = f"""[Unit]
Description=sched-ext BPF CPU Scheduler ({scheduler})
After=sysinit.target local-fs.target
DefaultDependencies=no

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c '/usr/bin/scxctl stop 2>/dev/null || true; /usr/bin/scxctl start --sched {scheduler_name} --mode {mode}'
ExecStop=/usr/bin/scxctl stop
TimeoutStartSec=30

[Install]
WantedBy=sysinit.target
"""

                # Write service file (requires root)
                temp_file = '/tmp/scx.service'
                with open(temp_file, 'w') as f:
                    f.write(service_content)

                # Copy to systemd, enable, and start the service
                # Start early in boot process using sysinit.target
                result = subprocess.run(
                    ['pkexec', 'sh', '-c',
                     f'cp {temp_file} /etc/systemd/system/scx.service && '
                     f'systemctl daemon-reload && '
                     f'systemctl enable --now scx.service && '
                     f'mkdir -p /etc/systemd/system/sysinit.target.wants && '
                     f'ln -sf /etc/systemd/system/scx.service /etc/systemd/system/sysinit.target.wants/scx.service && '
                     f'systemctl is-enabled scx.service'],
                    capture_output=True,
                    text=True,
                    timeout=45
                )

                if result.returncode == 0:
                    # Check if the output confirms it's enabled
                    if 'enabled' in result.stdout.lower():
                        self.log(f"✓ {scheduler} enabled and will auto-start on boot ({mode} mode)")
                        self.log(f"✓ Symlink verified: {result.stdout.strip()}")
                    else:
                        self.log(f"✓ {scheduler} service created ({mode} mode)")
                    self.log("✓ Service started immediately for testing")
                    # Verify the service started
                    QTimer.singleShot(3000, self.verify_service_started)
                else:
                    self.log(f"✗ Failed to enable persistence: {result.stderr}")
                    self.persist_checkbox.blockSignals(True)
                    self.persist_checkbox.setChecked(False)
                    self.persist_checkbox.blockSignals(False)
            else:
                self.log("→ Disabling scheduler persistence...")
                cmd = ['pkexec', 'sh', '-c',
                       'systemctl stop scx.service && systemctl disable scx.service']

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

    def verify_service_started(self):
        """Verify that the service actually started"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'scx.service'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and 'active' in result.stdout:
                self.log("✓ Service verified as running")
            else:
                self.log("⚠ Service may not have started - check 'systemctl status scx.service'")
        except:
            pass

    def cleanup(self):
        """Cleanup on close"""
        self.monitor.stop()
        self.monitor.wait()


class XeroLinuxManager(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XeroLinux Scheduler Switcher Tool")
        self.setMinimumSize(550, 600)  # Compact width for scheduler tool

        self.setup_ui()

    def setup_ui(self):
        """Setup main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)  # Compact margins
        layout.setSpacing(5)  # Compact spacing

        # Main title
        title_layout = QHBoxLayout()
        logo = QLabel("⚡")
        logo.setFont(QFont("Sans", 28))  # Slightly smaller icon
        title_layout.addWidget(logo)

        title = QLabel("XeroLinux Scheduler Switcher Tool")
        title.setFont(QFont("Sans", 16, QFont.Weight.Bold))  # Slightly smaller title
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Description under title
        desc = QLabel("Manage sched-ext BPF CPU schedulers on the fly")
        desc.setFont(QFont("Sans", 11))
        desc.setContentsMargins(45, 0, 0, 5)  # Adjust left margin to align with title
        layout.addWidget(desc)

        # Separator line - text based for visibility
        separator = QLabel("─" * 60)  # Shorter for narrow window
        separator.setStyleSheet("QLabel { color: #666666; }")
        separator.setContentsMargins(0, 5, 0, 0)  # Remove bottom margin
        layout.addWidget(separator)

        # Create log widget FIRST (before scheduler that needs it)
        log_group = QGroupBox("📋 Activity Log")
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(5, 5, 5, 5)  # Compact margins
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)  # Compact log area
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)

        # Scheduler content (only if scxctl is available)
        if self.check_scxctl():
            self.scheduler_tab = SchedulerTab(self.log)
            layout.addWidget(self.scheduler_tab)
        else:
            warning_widget = QWidget()
            warning_layout = QVBoxLayout(warning_widget)
            warning_layout.addStretch()
            warning_label = QLabel("⚠️ scxctl not found. Install scx-tools to enable this feature.")
            warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            warning_label.setFont(QFont("Sans", 14))
            warning_layout.addWidget(warning_label)
            warning_layout.addStretch()
            layout.addWidget(warning_widget)

        # Add log panel at the bottom
        layout.addWidget(log_group)

        self.log("XeroLinux Scheduler Switcher Tool initialized")

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
