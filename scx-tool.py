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
    QMessageBox, QLineEdit, QCheckBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt, QRect
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QPainter, QPen, QBrush


class CircuitBannerWidget(QWidget):
    """Decorative PCB circuit banner drawn with QPainter"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(78)
        self.setMinimumWidth(200)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx = w // 2

        DIM     = QColor("#5a1e7a")
        BRIGHT  = QColor("#b44fd4")
        GLOW    = QColor("#f06bff")
        CHIP_BG = QColor("#1a0a24")

        def draw_node(x, y, r=3):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(GLOW))
            painter.drawEllipse(x - r, y - r, r * 2, r * 2)

        # ── rails ──────────────────────────────────────────────
        TOP, BOT = 12, 65
        painter.setPen(QPen(BRIGHT, 1))
        painter.drawLine(8, TOP, cx - 55, TOP)
        painter.drawLine(cx + 55, TOP, w - 8, TOP)

        painter.setPen(QPen(DIM, 2))
        painter.drawLine(8, BOT, w - 8, BOT)

        # ── left branch: drop from top rail, run right, drop to bottom ──
        painter.setPen(QPen(BRIGHT, 1))
        lx1 = max(8, cx - 190)
        painter.drawLine(lx1, TOP, lx1, 38)
        painter.drawLine(lx1, 38, cx - 135, 38)
        painter.drawLine(cx - 135, 38, cx - 135, BOT)

        # ── right branch mirrored ──
        rx1 = min(w - 8, cx + 190)
        painter.drawLine(rx1, TOP, rx1, 38)
        painter.drawLine(rx1, 38, cx + 135, 38)
        painter.drawLine(cx + 135, 38, cx + 135, BOT)

        # ── left inner trace: chip pin to top rail ──
        painter.setPen(QPen(DIM, 2))
        painter.drawLine(cx - 110, TOP, cx - 110, 29)
        painter.drawLine(cx - 110, 29, cx - 55, 29)   # meets chip left edge

        # ── right inner trace mirrored ──
        painter.drawLine(cx + 110, TOP, cx + 110, 29)
        painter.drawLine(cx + 110, 29, cx + 55, 29)

        # ── chip down to bottom rail ──
        painter.drawLine(cx, 52, cx, BOT)

        # ── center chip ──────────────────────────────────────
        cw, ch = 110, 40
        chip_rect = QRect(cx - cw // 2, 14, cw, ch)
        painter.fillRect(chip_rect, CHIP_BG)
        painter.setPen(QPen(BRIGHT, 1))
        painter.drawRect(chip_rect)

        # pins left & right
        painter.setPen(QPen(DIM, 1))
        for py in [22, 29, 36, 44]:
            if 14 <= py <= 54:
                painter.drawLine(cx - cw // 2 - 9, py, cx - cw // 2, py)
                painter.drawLine(cx + cw // 2, py, cx + cw // 2 + 9, py)

        # chip label
        painter.setPen(QPen(GLOW, 1))
        font = QFont("Monospace", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, "⚡ SCX")

        # ── nodes at every junction ───────────────────────────
        nodes = [
            (8, TOP), (w - 8, TOP), (8, BOT), (w - 8, BOT),
            (lx1, TOP), (rx1, TOP),
            (lx1, 38), (rx1, 38),
            (cx - 135, 38), (cx + 135, 38),
            (cx - 135, BOT), (cx + 135, BOT),
            (cx - 110, TOP), (cx + 110, TOP),
            (cx - 110, 29), (cx + 110, 29),
            (cx, BOT),
        ]
        for nx, ny in nodes:
            draw_node(nx, ny)

        painter.end()


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
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(6)

        layout.addWidget(self.create_kernel_check_panel())
        layout.addWidget(self.create_status_panel())
        layout.addWidget(self.create_selection_panel())
        layout.addStretch()
        layout.addWidget(CircuitBannerWidget())
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
        group = QGroupBox()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(4)

        title = QLabel("⚙️ Kernel Support")
        title.setFont(QFont("Sans", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        desc = QLabel("Verifies your kernel has sched-ext compiled in. Requires Linux 6.12 or newer.")
        desc.setStyleSheet("QLabel { color: #aaaaaa; font-size: 12px; }")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        kernel_supported, kernel_version, message = self.check_kernel_support()
        self.kernel_supported = kernel_supported

        info_row = QHBoxLayout()
        version_label = QLabel(f"Kernel: {kernel_version}")
        version_label.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        info_row.addWidget(version_label)
        self.kernel_support_label = QLabel(message)
        info_row.addWidget(self.kernel_support_label)
        info_row.addStretch()
        layout.addLayout(info_row)

        group.setLayout(layout)
        return group

    def create_status_panel(self):
        """Create current status panel"""
        group = QGroupBox()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(4)

        title = QLabel("📊 Current Status")
        title.setFont(QFont("Sans", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        desc = QLabel("Live view of the active sched-ext scheduler and its operating mode. Updates every 500ms.")
        desc.setStyleSheet("QLabel { color: #aaaaaa; font-size: 12px; }")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        info_row = QHBoxLayout()
        info_row.setSpacing(16)
        info_row.addWidget(QLabel("Active Scheduler:"))
        self.active_scheduler_label = QLabel("Checking...")
        self.active_scheduler_label.setFont(QFont("Sans", 12, QFont.Weight.Bold))
        info_row.addWidget(self.active_scheduler_label)
        info_row.addWidget(QLabel("Mode:"))
        self.mode_label = QLabel("N/A")
        info_row.addWidget(self.mode_label)
        info_row.addStretch()
        layout.addLayout(info_row)

        group.setLayout(layout)
        return group

    def create_selection_panel(self):
        """Create scheduler selection panel"""
        group = QGroupBox()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        title = QLabel("🎯 Scheduler Selection")
        title.setFont(QFont("Sans", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        desc = QLabel("Choose a scheduler and performance mode. Enable persistence to auto-start on every boot via systemd.")
        desc.setStyleSheet("QLabel { color: #aaaaaa; font-size: 12px; }")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(QLabel("Scheduler:"))
        self.scheduler_combo = QComboBox()
        row.addWidget(self.scheduler_combo)
        row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        for display_name, value in [("Auto", "auto"), ("Gaming", "gaming"),
                                     ("Low Latency", "lowlatency"), ("Power Save", "powersave")]:
            self.mode_combo.addItem(display_name, value)
        row.addWidget(self.mode_combo)
        row.addStretch()
        layout.addLayout(row)

        self.persist_checkbox = QCheckBox("🔄 Persist scheduler after reboot")
        self.persist_checkbox.setToolTip("Enable systemd service to auto-start scheduler on boot")
        self.persist_checkbox.stateChanged.connect(self.toggle_persistence)
        layout.addWidget(self.persist_checkbox)

        QTimer.singleShot(0, self.check_persistence_state)

        group.setLayout(layout)
        return group

    def create_control_buttons(self):
        """Create control buttons"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(6)

        self.switch_btn = QPushButton("🔄 Switch / Start Scheduler")
        self.switch_btn.clicked.connect(self.switch_scheduler)
        self.switch_btn.setEnabled(False)

        self.stop_btn = QPushButton("⏹ Stop Scheduler")
        self.stop_btn.clicked.connect(self.stop_scheduler)
        self.stop_btn.setEnabled(False)

        self.refresh_btn = QPushButton("🔃 Refresh List")
        self.refresh_btn.clicked.connect(self.scan_schedulers)

        for btn in (self.switch_btn, self.stop_btn, self.refresh_btn):
            btn.setMinimumHeight(36)
            layout.addWidget(btn)

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


class FlagsTab(QWidget):
    """Flags Reference Tab - shows available scheduler flags and their descriptions"""

    SCHEDULER_FLAGS = [
        # scx_bpfland
        ("scx_bpfland", "--slice-us", "optional",
         "Tune slice duration in microseconds. Lower = more responsive. Default: 2000. Try 500-1000 for low-latency."),
        ("scx_bpfland", "--freq-to-lowfreq", "optional",
         "CPU frequency governor hint: 'performance' keeps clocks high, 'powersave' allows down-clocking."),
        ("scx_bpfland", "--partial", "optional",
         "Enable partial scheduling mode. Only selected tasks go through the BPF scheduler."),
        ("scx_bpfland", "--nr-cpus-big", "optional",
         "Number of 'big' CPUs for asymmetric systems (e.g. big.LITTLE). Set to 0 to disable."),
        # scx_lavd
        ("scx_lavd", "--no-preempt-idle", "optional",
         "Prevents idle CPUs from running tasks from other scheduling domains. Useful for kernel task isolation."),
        ("scx_lavd", "--autopilot", "optional",
         "Automatically tune scheduler parameters based on detected workload characteristics."),
        ("scx_lavd", "--slice-us", "optional",
         "Slice duration in microseconds. Controls task scheduling granularity. Lower = more responsive."),
        ("scx_lavd", "--performance", "optional",
         "Prefer performance over power efficiency. Keeps CPUs running at higher frequencies."),
        # scx_nest
        ("scx_nest", "--print-cpumask", "optional",
         "Print per-core idle CPUmask to stdout. Useful for debugging CPU affinity issues."),
        ("scx_nest", "--delay-us", "optional",
         "How long a CPU waits idle before it is considered for task removal. Lower = lower power, fewer task dispatches."),
        ("scx_nest", "--lowlatency", "optional",
         "Target percentage of idle CPUs to maintain. Higher = more power usage, lower = fewer task dispatch opportunities."),
        # scx_rusty
        ("scx_rusty", "--no-preempt", "optional",
         "Disable slice preemption. Tasks spread freely across all cores rather than being consolidated."),
        ("scx_rusty", "--load-half-life", "optional",
         "Load tracking half-life in seconds. Lower values track workload changes faster."),
        ("scx_rusty", "--verbose", "optional",
         "Enable verbose logging output. Useful for debugging scheduler behaviour."),
        # scx_tickless
        ("scx_tickless", "--slice-us", "optional",
         "Tune slice duration in microseconds for the tickless scheduler. Lower = more responsive."),
        ("scx_tickless", "--no-preempt", "optional",
         "Disable slice preemption. Tasks spread freely across all cores rather than being consolidated."),
        # scx_layered
        ("scx_layered", "--stats", "optional",
         "Print per-layer scheduling statistics periodically. Useful for performance analysis and tuning."),
        ("scx_layered", "--slice-us", "optional",
         "Slice duration in microseconds. Controls how long a task runs before being preempted."),
        ("scx_layered", "--verbose", "optional",
         "Enable verbose logging. Helps diagnose layer assignment and scheduling decisions."),
        # scx_userland
        ("scx_userland", "--interval-us", "optional",
         "Scheduler decision interval in microseconds. Default: 1000. Reduce for interactive use, increase for throughput."),
        ("scx_userland", "--partial", "optional",
         "Enable partial scheduling. Only selected tasks are managed by the userland scheduler."),
        # scx_flatcg
        ("scx_flatcg", "--nr-dom-slabs", "optional",
         "Number of per-domain scheduling slabs. Affects memory usage and scheduling granularity."),
        ("scx_flatcg", "--slice-us", "optional",
         "Slice duration in microseconds. Controls task scheduling time quantum."),
        # scx_simple
        ("scx_simple", "--fifo", "optional",
         "Run all tasks in FIFO order. Useful for real-time workloads or debugging scheduler behaviour."),
        ("scx_simple", "--slice-us", "optional",
         "Slice duration in microseconds for simple round-robin scheduling."),
        # scx_chaos
        ("scx_chaos", "--seed", "optional",
         "Random seed for chaos scheduling decisions. Use a fixed value for reproducible testing."),
        ("scx_chaos", "--slice-us", "optional",
         "Slice duration in microseconds. Lower values increase scheduling frequency and chaos."),
    ]

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        howto = QGroupBox()
        howto.setStyleSheet(
            "QGroupBox { background: rgba(80, 20, 110, 0.18); "
            "border: 1px solid rgba(180, 79, 212, 0.45); border-radius: 6px; }"
        )
        howto_layout = QVBoxLayout(howto)
        howto_layout.setContentsMargins(10, 8, 10, 10)
        howto_layout.setSpacing(5)

        howto_title = QLabel("📖 How to use flags")
        howto_title.setFont(QFont("Sans", 13, QFont.Weight.Bold))
        howto_title.setStyleSheet("QLabel { color: #d88eff; background: transparent; }")
        howto_layout.addWidget(howto_title)

        howto_desc = QLabel(
            "Flags are extra options you pass on the command line when starting a scheduler manually. "
            "They let you tune behaviour beyond what the GUI exposes. "
            "The table below lists every known flag, whether it is optional or required, and what it does."
        )
        howto_desc.setWordWrap(True)
        howto_desc.setStyleSheet("QLabel { color: #ccbbdd; font-size: 12px; background: transparent; }")
        howto_layout.addWidget(howto_desc)

        example_label = QLabel("Example usage:")
        example_label.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        example_label.setStyleSheet("QLabel { color: #d88eff; background: transparent; }")
        howto_layout.addWidget(example_label)

        example = QLabel("  scxctl start --sched bpfland -- --slice-us 500 --freq-to-lowfreq performance")
        example.setFont(QFont("Monospace", 11))
        example.setStyleSheet(
            "QLabel { background: rgba(60, 10, 90, 0.55); color: #f06bff; padding: 6px 10px; "
            "border-radius: 4px; border: 1px solid rgba(180, 79, 212, 0.5); }"
        )
        example.setWordWrap(True)
        howto_layout.addWidget(example)

        note = QLabel(
            "💡  Flags specific to the scheduler go after a bare  --  separator. "
            "Required flags must always be provided; optional ones fall back to their defaults if omitted."
        )
        note.setWordWrap(True)
        note.setStyleSheet("QLabel { color: #aa99bb; font-size: 11px; background: transparent; }")
        howto_layout.addWidget(note)

        layout.addWidget(howto)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter by scheduler, flag, or description…")
        self.filter_edit.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_edit)
        layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Scheduler", "Flag", "Status", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        layout.addWidget(self.table)

        self.populate_table(self.SCHEDULER_FLAGS)

    def populate_table(self, flags_data):
        self.table.setRowCount(len(flags_data))
        for row, (scheduler, flag, status, desc) in enumerate(flags_data):
            self.table.setItem(row, 0, QTableWidgetItem(scheduler))
            self.table.setItem(row, 1, QTableWidgetItem(flag))

            status_item = QTableWidgetItem(status)
            color = QColor("#ff6b6b") if status == "required" else QColor("#69db7c")
            status_item.setForeground(color)
            self.table.setItem(row, 2, status_item)

            self.table.setItem(row, 3, QTableWidgetItem(desc))

        self.table.resizeRowsToContents()

    def apply_filter(self, text):
        text = text.lower()
        filtered = [
            row for row in self.SCHEDULER_FLAGS
            if text in row[0].lower() or text in row[1].lower() or text in row[3].lower()
        ]
        self.populate_table(filtered)


class SCXInfoTab(QWidget):
    """SCX Info Tab - explains what each available scheduler does"""

    SCHEDULER_INFO = [
        (
            "scx_bpfland", "BPFland",
            "🎮 Gaming / Interactive",
            "A vruntime-based scheduler prioritizing interactive workloads by identifying tasks that "
            "block frequently. It considers cache layout when assigning cores, excelling under heavy "
            "load and gaming scenarios while supporting hybrid CPU topologies."
        ),
        (
            "scx_lavd", "LAVD",
            "🎮 Gaming / Low Latency",
            "Designed for gaming and latency-sensitive tasks. Calculates a 'latency criticality' score "
            "per task and assigns virtual deadlines accordingly. Features Core Compaction for power "
            "savings and Autopilot mode for automatic power profile adjustment."
        ),
        (
            "scx_rusty", "Rusty",
            "🖥️ Desktop / Server",
            "A load-balancing focused scheduler that groups CPUs by Last-Level Cache and maintains "
            "task locality. Highly tunable with flags, it includes Autopower mode and suits general "
            "desktop and server workloads."
        ),
        (
            "scx_rustland", "Rustland",
            "🧪 Userspace / Educational",
            "The userspace predecessor to BPFland with similar scheduling logic but running in "
            "userspace. More readable for understanding scheduler behaviour, though with slight "
            "throughput trade-offs compared to its BPF counterpart."
        ),
        (
            "scx_flash", "Flash",
            "🖥️ Desktop / Soft Real-Time",
            "Emphasises fairness and performance predictability over prioritising interactive tasks. "
            "It replaced the lowlatency mode in BPFland and targets soft real-time workloads such "
            "as audio processing."
        ),
        (
            "scx_layered", "Layered",
            "⚙️ Power Users",
            "A highly configurable scheduler enabling task classification into named 'layers' with "
            "independent scheduling policies per layer. Suited for power users needing fine-grained "
            "control over how different workloads are handled."
        ),
        (
            "scx_cosmos", "Cosmos",
            "🖥️ General Purpose",
            "A lightweight scheduler optimising task-to-CPU locality, maintaining cache warmth and "
            "reducing migration overhead. Designed for general-purpose desktop use."
        ),
        (
            "scx_simple", "Simple",
            "🧪 Reference / Learning",
            "A minimal reference scheduler serving as documentation and learning material. Maintains "
            "per-CPU locality but is not intended for production use — useful for understanding "
            "how sched-ext schedulers are built."
        ),
    ]

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(5, 5, 5, 5)
        outer_layout.setSpacing(5)

        hint = QLabel("Descriptions sourced from the XeroLinux Wiki. Click a card to learn more.")
        hint.setWordWrap(True)
        hint.setStyleSheet("QLabel { color: #aaaaaa; }")
        outer_layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for scx_name, display_name, category, description in self.SCHEDULER_INFO:
            card = QGroupBox()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(3)

            header_layout = QHBoxLayout()
            name_label = QLabel(display_name)
            name_label.setFont(QFont("Sans", 13, QFont.Weight.Bold))
            header_layout.addWidget(name_label)

            tech_label = QLabel(f"({scx_name})")
            tech_label.setStyleSheet("QLabel { color: #888888; }")
            header_layout.addWidget(tech_label)

            header_layout.addStretch()

            cat_label = QLabel(category)
            cat_label.setStyleSheet(
                "QLabel { color: #aaaaff; font-size: 12px; padding: 2px 6px; "
                "border: 1px solid #555577; border-radius: 4px; }"
            )
            header_layout.addWidget(cat_label)
            card_layout.addLayout(header_layout)

            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("QLabel { color: #cccccc; font-size: 12px; }")
            card_layout.addWidget(desc_label)

            layout.addWidget(card)

        layout.addStretch()
        scroll.setWidget(container)
        outer_layout.addWidget(scroll)


class XeroLinuxManager(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XeroLinux Scheduler Switcher Tool")
        self.setMinimumWidth(900)

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
        title.setFont(QFont("Sans", 18, QFont.Weight.Bold))
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Description under title
        desc = QLabel("Manage sched-ext BPF CPU schedulers on the fly")
        desc.setFont(QFont("Sans", 12))
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

        # Tab widget
        tab_widget = QTabWidget()
        tab_widget.tabBar().setExpanding(False)
        tab_widget.setStyleSheet("QTabWidget::tab-bar { alignment: center; }")

        # Tab 1: Scheduler
        if self.check_scxctl():
            self.scheduler_tab = SchedulerTab(self.log)
            tab_widget.addTab(self.scheduler_tab, "⚙️ Scheduler")
        else:
            warning_widget = QWidget()
            warning_layout = QVBoxLayout(warning_widget)
            warning_layout.addStretch()
            warning_label = QLabel("⚠️ scxctl not found. Install scx-tools to enable this feature.")
            warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            warning_label.setFont(QFont("Sans", 14))
            warning_layout.addWidget(warning_label)
            warning_layout.addStretch()
            tab_widget.addTab(warning_widget, "⚙️ Scheduler")

        # Tab 2: Flags Reference
        tab_widget.addTab(FlagsTab(), "🚩 Flags Reference")

        # Tab 3: SCX Info
        tab_widget.addTab(SCXInfoTab(), "ℹ️ SCX Info")

        layout.addWidget(tab_widget)

        # Log panel at the bottom
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
