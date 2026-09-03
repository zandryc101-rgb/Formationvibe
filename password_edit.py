#!/usr/bin/env python3
"""Champ mot de passe PyQt5 avec icone oeil / oeil barre cliquable."""

from __future__ import annotations

from PyQt5.QtCore import QEvent, QPointF, Qt, QSize
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QLineEdit, QToolButton


def _icone_oeil(couleur: QColor, barre: bool, taille: int = 40) -> QIcon:
    pm = QPixmap(taille, taille)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    epaisseur = max(2.0, taille / 16.0)
    pen = QPen(couleur, epaisseur, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    cx = taille / 2.0
    cy = taille / 2.0
    contour = QPainterPath()
    contour.moveTo(taille * 0.10, cy)
    contour.quadTo(cx, taille * 0.18, taille * 0.90, cy)
    contour.quadTo(cx, taille * 0.82, taille * 0.10, cy)
    painter.drawPath(contour)
    painter.drawEllipse(QPointF(cx, cy), taille * 0.15, taille * 0.15)

    if barre:
        painter.drawLine(
            QPointF(taille * 0.20, taille * 0.80),
            QPointF(taille * 0.80, taille * 0.20),
        )
    painter.end()
    return QIcon(pm)


class PasswordLineEdit(QLineEdit):
    """QLineEdit mot de passe avec bouton oeil pour afficher / masquer."""

    def __init__(self, parent=None, couleur="#94a3b8", survol="#60a5fa"):
        super().__init__(parent)
        self._visible = False
        self._hover = False
        self._couleur = QColor(couleur)
        self._survol = QColor(survol)
        self.setEchoMode(QLineEdit.Password)

        self._btn = QToolButton(self)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setFocusPolicy(Qt.NoFocus)
        self._btn.setAutoRaise(True)
        self._btn.setIconSize(QSize(20, 20))
        self._btn.setStyleSheet(
            "QToolButton { border: none; background: transparent; padding: 0; margin: 0; }"
        )
        self._btn.clicked.connect(self.basculer)
        self._btn.installEventFilter(self)
        self.setTextMargins(0, 0, 34, 0)
        self._rafraichir_icone()

    def est_visible(self) -> bool:
        return self._visible

    def basculer(self):
        self._visible = not self._visible
        self.setEchoMode(QLineEdit.Normal if self._visible else QLineEdit.Password)
        self._rafraichir_icone()

    def _rafraichir_icone(self):
        couleur = self._survol if self._hover else self._couleur
        # Masque : oeil barre (cliquer pour voir). Visible : oeil (cliquer pour masquer).
        self._btn.setIcon(_icone_oeil(couleur, barre=not self._visible))
        if self._visible:
            self._btn.setToolTip("Masquer le mot de passe")
        else:
            self._btn.setToolTip("Afficher le mot de passe")

    def eventFilter(self, obj, event):
        if obj is self._btn:
            if event.type() == QEvent.Enter:
                self._hover = True
                self._rafraichir_icone()
            elif event.type() == QEvent.Leave:
                self._hover = False
                self._rafraichir_icone()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cote = 22
        x = self.rect().right() - cote - 8
        y = (self.height() - cote) // 2
        self._btn.setGeometry(x, y, cote, cote)
