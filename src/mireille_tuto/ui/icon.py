"""Générateur du logo et icône de l'application Mireille Tuto."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

_CACHED_ICON: QIcon | None = None


def render_app_pixmap(size: int = 256) -> QPixmap:
    """Dessine le logo de l'application Mireille Tuto :
    
    Un globe terrestre stylisé bleu océan avec continents émeraude,
    le Japon mis en valeur en rouge corail, et une frontière de décision
    mathématique dorée en pointillés qui isole le pays.
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.05
    d = size - 2 * margin
    globe_rect = QRectF(margin, margin, d, d)

    # 1. Fond océan avec dégradé subtil
    ocean_grad = QLinearGradient(margin, margin, size - margin, size - margin)
    ocean_grad.setColorAt(0.0, QColor("#1e40af"))  # Bleu profond
    ocean_grad.setColorAt(0.4, QColor("#0284c7"))  # Bleu ciel azur
    ocean_grad.setColorAt(1.0, QColor("#0369a1"))  # Bleu océan

    painter.setPen(QPen(QColor("#0f172a"), max(1.0, size * 0.02)))
    painter.setBrush(QBrush(ocean_grad))
    painter.drawEllipse(globe_rect)

    # Masque circulaire pour couper les éléments qui dépassent du globe
    clip = QPainterPath()
    clip.addEllipse(globe_rect)
    painter.save()
    painter.setClipPath(clip)

    # 2. Lignes de coordonnées (Méridiens et Parallèles)
    grid_pen = QPen(QColor(255, 255, 255, 55), max(1.0, size * 0.015))
    painter.setPen(grid_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(margin + d * 0.22, margin, d * 0.56, d))
    painter.drawLine(QPointF(margin, size / 2), QPointF(size - margin, size / 2))
    painter.drawLine(QPointF(size / 2, margin), QPointF(size / 2, size - margin))
    painter.drawLine(QPointF(margin + d * 0.08, size * 0.32), QPointF(size - margin - d * 0.08, size * 0.32))
    painter.drawLine(QPointF(margin + d * 0.08, size * 0.68), QPointF(size - margin - d * 0.08, size * 0.68))

    # 3. Continents stylisés (Vert émeraude)
    land_brush = QBrush(QColor("#10b981"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(land_brush)

    # Masse eurasienne stylisée
    eurasia = QPainterPath()
    eurasia.moveTo(size * 0.28, size * 0.22)
    eurasia.cubicTo(size * 0.52, size * 0.16, size * 0.76, size * 0.26, size * 0.74, size * 0.46)
    eurasia.cubicTo(size * 0.68, size * 0.64, size * 0.44, size * 0.58, size * 0.34, size * 0.48)
    eurasia.cubicTo(size * 0.24, size * 0.42, size * 0.18, size * 0.32, size * 0.28, size * 0.22)
    painter.drawPath(eurasia)

    # Péninsule sud / Océanie stylisée
    aust = QPainterPath()
    aust.addEllipse(QRectF(size * 0.64, size * 0.66, size * 0.16, size * 0.14))
    painter.drawPath(aust)

    # 4. Archipel du Japon en rouge vif
    jp_pen = QPen(QColor("#dc2626"), max(1.5, size * 0.045), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(jp_pen)
    jp_path = QPainterPath()
    jp_path.moveTo(size * 0.78, size * 0.30)
    jp_path.quadTo(size * 0.73, size * 0.40, size * 0.66, size * 0.48)
    painter.drawPath(jp_path)

    # 5. Frontière de décision mathématique f(x, y) = 0 (courbe dorée)
    curve_pen = QPen(QColor("#fbbf24"), max(1.2, size * 0.035), Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(curve_pen)
    curve = QPainterPath()
    curve.moveTo(size * 0.50, size * 0.62)
    curve.quadTo(size * 0.68, size * 0.44, size * 0.88, size * 0.24)
    painter.drawPath(curve)

    painter.restore()

    # 6. Reflet brillant (highlight) en haut à gauche
    shine = QLinearGradient(margin, margin, margin + d * 0.45, margin + d * 0.45)
    shine.setColorAt(0.0, QColor(255, 255, 255, 110))
    shine.setColorAt(0.6, QColor(255, 255, 255, 20))
    shine.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(shine))
    painter.drawEllipse(QRectF(margin + d * 0.05, margin + d * 0.05, d * 0.42, d * 0.32))

    # 7. Nœud d'activation / Cible rouge avec cerclage blanc brillant
    node_x, node_y = size * 0.72, size * 0.39
    r_node = max(2.5, size * 0.045)
    painter.setPen(QPen(QColor("#ffffff"), max(1.0, size * 0.02)))
    painter.setBrush(QBrush(QColor("#ef4444")))
    painter.drawEllipse(QPointF(node_x, node_y), r_node, r_node)

    painter.end()
    return pix


def get_app_icon() -> QIcon:
    """Retourne l'icône de l'application multi-résolution (16, 24, 32, 48, 64, 128, 256)."""
    global _CACHED_ICON
    if _CACHED_ICON is not None:
        return _CACHED_ICON

    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        pix = render_app_pixmap(s)
        icon.addPixmap(pix)

    _CACHED_ICON = icon
    return icon
