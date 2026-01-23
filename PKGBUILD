# Maintainer: DarkXero <info@techxero.com>

pkgname=scx-km
pkgver=1.0.0
pkgrel=1
pkgdesc="Comprehensive GUI for managing Linux kernels and sched-ext BPF CPU schedulers"
arch=('any')
url="https://github.com/XeroLinuxDev/scx-km"
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
source=(
    "km_scx.py"
    "scx-km.desktop"
)
sha256sums=('SKIP'
            'SKIP')

package() {
    # Install the main script (rename and make executable)
    install -Dm755 "${srcdir}/km_scx.py" "${pkgdir}/usr/bin/scx-km"
    
    # Install desktop file
    install -Dm644 "${srcdir}/scx-km.desktop" "${pkgdir}/usr/share/applications/scx-km.desktop"
}
