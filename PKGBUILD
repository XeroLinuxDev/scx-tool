# Maintainer: DarkXero <info@xerolinux.xyz>

pkgname=scx-tool
pkgver=1.0.4
pkgrel=2
pkgdesc="Comprehensive GUI for managing sched-ext BPF CPU schedulers"
arch=('any')
url="https://github.com/XeroLinuxDev/scx-tool"
license=('GPL3')
depends=(
    'python'
    'python-pyqt6'
    'pacman'
    'scx-scheds'
    'scx-tools'
    'polkit'
)
optdepends=(
    'linux-cachyos: CachyOS kernel with sched-ext support'
)
replaces=('scx-km')
source=(
    "scx-tool.py"
    "scx-tool.desktop"
)
sha256sums=('SKIP'
            'SKIP')

package() {
    # Install the main script (rename and make executable)
    install -Dm755 "${srcdir}/scx-tool.py" "${pkgdir}/usr/bin/scx-tool"

    # Install desktop file
    install -Dm644 "${srcdir}/scx-tool.desktop" "${pkgdir}/usr/share/applications/scx-tool.desktop"
}
