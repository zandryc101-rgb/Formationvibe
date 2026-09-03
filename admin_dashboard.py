#!/usr/bin/env python3
"""
Dashboard Administrateur - Interface PyQt5 dynamique et animee.
Authentification SQLite : 2 administrateurs maximum, inscription,
modification, suppression et recuperation de mot de passe.

Lancement :
    python admin_dashboard.py
"""

from __future__ import annotations

import math
import random
import sys

from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QRect, QSize, QPointF, QRectF
from PyQt5.QtGui import (
    QColor, QPainter, QPen, QFont, QBrush, QPainterPath, QLinearGradient,
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QStackedWidget,
    QGraphicsDropShadowEffect, QSizePolicy, QToolButton, QMenu, QAction,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QDialog,
    QRadioButton, QButtonGroup, QMessageBox,
)

from db import AdminDB, MAX_ADMINS
from password_edit import PasswordLineEdit


# ===========================================================================
# Palette de couleurs (style plateforme web moderne)
# ===========================================================================
class Theme:
    BG_APP = QColor("#0f172a")
    BG_CARD = QColor("#1e293b")
    BG_CARD_HOVER = QColor("#273449")
    BG_SIDEBAR = QColor("#111827")
    BG_INPUT = QColor("#1e293b")
    ACCENT = QColor("#3b82f6")
    ACCENT_HOVER = QColor("#2563eb")
    ACCENT_LIGHT = QColor("#60a5fa")
    SUCCESS = QColor("#10b981")
    WARNING = QColor("#f59e0b")
    ERROR = QColor("#ef4444")
    TEXT_PRIMARY = QColor("#f1f5f9")
    TEXT_SECONDARY = QColor("#94a3b8")
    TEXT_MUTED = QColor("#64748b")
    BORDER = QColor("#334155")
    GRADIENT_START = QColor("#3b82f6")
    GRADIENT_END = QColor("#8b5cf6")


def apply_theme(app):
    app.setStyle("Fusion")
    app.setStyleSheet(f"""
        QWidget {{
            color: {Theme.TEXT_PRIMARY.name()};
            font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif;
        }}
        QMainWindow {{ background-color: {Theme.BG_APP.name()}; }}
        QDialog {{ background-color: {Theme.BG_APP.name()}; }}
        QScrollBar:vertical {{
            background: {Theme.BG_APP.name()};
            width: 10px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {Theme.BORDER.name()};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {Theme.ACCENT.name()}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """)


def shadow(blur=30, color=QColor(0, 0, 0, 120), y=10):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setColor(color)
    eff.setOffset(0, y)
    return eff


def style_input(widget):
    widget.setStyleSheet(f"""
        QLineEdit {{
            background-color: {Theme.BG_INPUT.name()};
            color: {Theme.TEXT_PRIMARY.name()};
            border: 1px solid {Theme.BORDER.name()};
            border-radius: 10px; padding: 12px 16px; font-size: 14px;
            selection-background-color: {Theme.ACCENT.name()};
        }}
        QLineEdit:focus {{ border: 1px solid {Theme.ACCENT.name()}; }}
    """)


def nom_depuis_email(email):
    local = email.split("@")[0].replace(".", " ").replace("_", " ")
    return " ".join(part.capitalize() for part in local.split() if part) or "Admin"


# ===========================================================================
# Avatar arrondi (image generee avec degrade + initiales)
# ===========================================================================
class AvatarWidget(QWidget):
    """Avatar circulaire avec degrade et initiales, comme sur les plateformes web."""

    def __init__(self, initiales="AD", taille=40, parent=None):
        super().__init__(parent)
        self.initiales = initiales
        self.taille = taille
        self.setFixedSize(taille, taille)

    def set_initiales(self, initiales):
        self.initiales = initiales
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.taille, self.taille)
        grad = QLinearGradient(0, 0, self.taille, self.taille)
        grad.setColorAt(0, Theme.GRADIENT_START)
        grad.setColorAt(1, Theme.GRADIENT_END)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(rect)
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Segoe UI", int(self.taille * 0.32), QFont.Bold))
        p.drawText(rect, Qt.AlignCenter, self.initiales)


# ===========================================================================
# Bouton anime avec effet de survol / clic
# ===========================================================================
class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None, accent=True):
        super().__init__(text, parent)
        self.accent = accent
        self.setCursor(Qt.PointingHandCursor)
        self._build_style()
        self.installEventFilter(self)

    def _build_style(self):
        if self.accent:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.ACCENT.name()};
                    color: white; border: none; border-radius: 10px;
                    padding: 12px 24px; font-size: 14px; font-weight: 600;
                }}
                QPushButton:hover {{ background-color: {Theme.ACCENT_HOVER.name()}; }}
                QPushButton:pressed {{ background-color: {Theme.ACCENT.name()}; }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Theme.TEXT_SECONDARY.name()};
                    border: 1px solid {Theme.BORDER.name()};
                    border-radius: 10px; padding: 10px 20px;
                    font-size: 13px; font-weight: 500;
                }}
                QPushButton:hover {{
                    color: {Theme.TEXT_PRIMARY.name()};
                    border-color: {Theme.ACCENT.name()};
                }}
            """)
        if self.accent:
            self.setGraphicsEffect(shadow(blur=20, y=6))

    def eventFilter(self, obj, event):
        if obj is self and event.type() in (event.Enter, event.Leave):
            self._animate_hover(event.type() == event.Enter)
        return super().eventFilter(obj, event)

    def _animate_hover(self, entering):
        if self.accent:
            start = Theme.ACCENT.name() if entering else Theme.ACCENT_HOVER.name()
            end = Theme.ACCENT_HOVER.name() if entering else Theme.ACCENT.name()
            if start in self.styleSheet():
                self.setStyleSheet(self.styleSheet().replace(start, end))


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self._couleur = Theme.ACCENT_LIGHT.name()
        self._appliquer()

    def _appliquer(self, souligne=False):
        deco = "text-decoration: underline;" if souligne else "text-decoration: none;"
        self.setStyleSheet(
            f"font-size: 12px; color: {self._couleur}; font-weight: 500; {deco}"
        )

    def enterEvent(self, event):
        self._appliquer(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._appliquer(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ===========================================================================
# Petites fenetres : inscription, recuperation, edition
# ===========================================================================
class AuthCardDialog(QDialog):
    def __init__(self, titre, sous_titre, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(titre)
        self.setMinimumWidth(440)
        self.setStyleSheet(f"QDialog {{ background-color: {Theme.BG_APP.name()}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        carte = QFrame()
        carte.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_CARD.name()}; "
            f"border-radius: 16px; border: 1px solid {Theme.BORDER.name()}; }}"
        )
        carte.setGraphicsEffect(shadow(blur=25, y=8))
        self.form = QVBoxLayout(carte)
        self.form.setContentsMargins(28, 28, 28, 28)
        self.form.setSpacing(10)

        t = QLabel(titre)
        t.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        self.form.addWidget(t)
        st = QLabel(sous_titre)
        st.setWordWrap(True)
        st.setStyleSheet(f"font-size: 13px; color: {Theme.TEXT_SECONDARY.name()}; margin-bottom: 8px;")
        self.form.addWidget(st)

        outer.addWidget(carte)

    def _champ(self, libelle, placeholder, password=False):
        lbl = QLabel(libelle)
        lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {Theme.TEXT_MUTED.name()}; letter-spacing: 1px;"
        )
        self.form.addWidget(lbl)
        champ = PasswordLineEdit() if password else QLineEdit()
        champ.setPlaceholderText(placeholder)
        style_input(champ)
        self.form.addWidget(champ)
        return champ

    def _message(self):
        lab = QLabel("")
        lab.setWordWrap(True)
        lab.setStyleSheet(f"color: {Theme.ERROR.name()}; font-size: 12px;")
        self.form.addWidget(lab)
        return lab


class InscriptionDialog(AuthCardDialog):
    compte_cree = pyqtSignal()

    def __init__(self, db, parent=None):
        super().__init__(
            "S'inscrire",
            "Creez un compte administrateur (maximum {0}).".format(MAX_ADMINS),
            parent,
        )
        self.db = db
        self.champ_email = self._champ("EMAIL", "admin@entreprise.com")
        self.champ_tel = self._champ("NUMERO DE TELEPHONE", "+261340000000")
        self.champ_mdp = self._champ("MOT DE PASSE", "••••••••", password=True)
        self.champ_mdp2 = self._champ("CONFIRMER LE MOT DE PASSE", "••••••••", password=True)
        self.label_info = self._message()

        self.form.addSpacing(8)
        actions = QHBoxLayout()
        annuler = AnimatedButton("Annuler", accent=False)
        annuler.clicked.connect(self.reject)
        self.bouton_ok = AnimatedButton("Creer le compte")
        self.bouton_ok.clicked.connect(self._creer)
        actions.addWidget(annuler)
        actions.addWidget(self.bouton_ok)
        self.form.addLayout(actions)
        self._rafraichir_limite()

    def _rafraichir_limite(self):
        if not self.db.inscription_autorisee():
            self.bouton_ok.setEnabled(False)
            self.label_info.setStyleSheet(f"color: {Theme.WARNING.name()}; font-size: 12px;")
            self.label_info.setText(
                "Limite atteinte : {0} administrateurs sont deja inscrits.".format(MAX_ADMINS)
            )
        else:
            self.bouton_ok.setEnabled(True)
            restant = self.db.places_restantes()
            self.label_info.setStyleSheet(f"color: {Theme.TEXT_SECONDARY.name()}; font-size: 12px;")
            self.label_info.setText("Places restantes : {0}/{1}.".format(restant, MAX_ADMINS))

    def _creer(self):
        if self.champ_mdp.text() != self.champ_mdp2.text():
            self.label_info.setStyleSheet(f"color: {Theme.ERROR.name()}; font-size: 12px;")
            self.label_info.setText("Les mots de passe ne correspondent pas.")
            return
        ok, msg, _admin = self.db.creer(
            self.champ_email.text(),
            self.champ_mdp.text(),
            self.champ_tel.text(),
        )
        self.label_info.setStyleSheet(
            f"color: {(Theme.SUCCESS if ok else Theme.ERROR).name()}; font-size: 12px;"
        )
        self.label_info.setText(msg)
        if ok:
            self.compte_cree.emit()
            QTimer.singleShot(500, self.accept)


class RecuperationDialog(AuthCardDialog):
    def __init__(self, db, parent=None):
        super().__init__(
            "Mot de passe oublie",
            "Un nouveau mot de passe sera envoye a l'email ou au telephone enregistre.",
            parent,
        )
        self.db = db

        choix = QHBoxLayout()
        self.radio_email = QRadioButton("Adresse email")
        self.radio_tel = QRadioButton("Numero de telephone")
        for r in (self.radio_email, self.radio_tel):
            r.setStyleSheet(f"color: {Theme.TEXT_PRIMARY.name()}; font-size: 13px;")
            r.setCursor(Qt.PointingHandCursor)
            choix.addWidget(r)
        self.radio_email.setChecked(True)
        self.groupe = QButtonGroup(self)
        self.groupe.addButton(self.radio_email)
        self.groupe.addButton(self.radio_tel)
        self.form.addLayout(choix)

        self.champ_ident = self._champ("DESTINATAIRE", "admin@entreprise.com")
        self.radio_email.toggled.connect(self._maj_placeholder)
        self.label_info = self._message()

        self.form.addSpacing(8)
        actions = QHBoxLayout()
        annuler = AnimatedButton("Annuler", accent=False)
        annuler.clicked.connect(self.reject)
        envoyer = AnimatedButton("Envoyer le mot de passe")
        envoyer.clicked.connect(self._envoyer)
        actions.addWidget(annuler)
        actions.addWidget(envoyer)
        self.form.addLayout(actions)

    def _maj_placeholder(self, email_actif):
        if email_actif:
            self.champ_ident.setPlaceholderText("admin@entreprise.com")
        else:
            self.champ_ident.setPlaceholderText("+261340000000")

    def _envoyer(self):
        canal = "email" if self.radio_email.isChecked() else "telephone"
        ok, msg, dest, nouveau = self.db.recuperer_mot_de_passe(canal, self.champ_ident.text())
        if not ok:
            self.label_info.setStyleSheet(f"color: {Theme.ERROR.name()}; font-size: 12px;")
            self.label_info.setText(msg)
            return
        canal_lib = "l'adresse email" if canal == "email" else "le numero"
        QMessageBox.information(
            self,
            "Mot de passe envoye",
            "Le mot de passe a ete envoye a {0} :\n{1}\n\n"
            "Nouveau mot de passe : {2}\n\n"
            "(Envoi local : sans serveur email/SMS, le mot de passe est affiche ici "
            "pour vous reconnecter.)".format(canal_lib, dest, nouveau),
        )
        self.accept()


class EditionAdminDialog(AuthCardDialog):
    def __init__(self, db, admin, parent=None):
        super().__init__("Modifier l'administrateur", "Laissez le mot de passe vide pour le conserver.", parent)
        self.db = db
        self.admin_id = admin["id"]
        self.champ_email = self._champ("EMAIL", "admin@entreprise.com")
        self.champ_email.setText(admin["email"])
        self.champ_tel = self._champ("NUMERO DE TELEPHONE", "+261340000000")
        self.champ_tel.setText(admin["telephone"])
        self.champ_mdp = self._champ("NOUVEAU MOT DE PASSE (optionnel)", "••••••••", password=True)
        self.label_info = self._message()

        actions = QHBoxLayout()
        annuler = AnimatedButton("Annuler", accent=False)
        annuler.clicked.connect(self.reject)
        sauver = AnimatedButton("Enregistrer")
        sauver.clicked.connect(self._sauver)
        actions.addWidget(annuler)
        actions.addWidget(sauver)
        self.form.addLayout(actions)

    def _sauver(self):
        mdp = self.champ_mdp.text().strip() or None
        ok, msg = self.db.modifier(
            self.admin_id,
            self.champ_email.text(),
            self.champ_tel.text(),
            mdp,
        )
        self.label_info.setStyleSheet(
            f"color: {(Theme.SUCCESS if ok else Theme.ERROR).name()}; font-size: 12px;"
        )
        self.label_info.setText(msg)
        if ok:
            self.accept()


# ===========================================================================
# Ecran de connexion anime
# ===========================================================================
class LoginScreen(QWidget):
    authentifie = pyqtSignal(dict)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.panneau_brand = BrandPanel()
        self.panneau_brand.setMinimumWidth(520)
        self.panneau_brand.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.panneau_brand, 1)

        form_wrap = QWidget()
        form_wrap.setStyleSheet(f"background-color: {Theme.BG_APP.name()};")
        fl = QVBoxLayout(form_wrap)
        fl.setContentsMargins(80, 80, 80, 80)
        fl.setSpacing(0)

        title = QLabel("Connexion")
        title.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        fl.addWidget(title)

        subtitle = QLabel("Accedez a votre espace d'administration")
        subtitle.setStyleSheet(f"font-size: 14px; color: {Theme.TEXT_SECONDARY.name()}; margin-bottom: 30px;")
        fl.addWidget(subtitle)

        lbl_email = QLabel("EMAIL")
        lbl_email.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {Theme.TEXT_MUTED.name()}; letter-spacing: 1px;"
        )
        fl.addWidget(lbl_email)
        self.champ_email = QLineEdit()
        self.champ_email.setPlaceholderText("admin@entreprise.com")
        style_input(self.champ_email)
        self.champ_email.setGraphicsEffect(shadow(blur=15, y=4))
        fl.addWidget(self.champ_email)

        fl.addSpacing(18)

        lbl_mdp = QLabel("MOT DE PASSE")
        lbl_mdp.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {Theme.TEXT_MUTED.name()}; letter-spacing: 1px;"
        )
        fl.addWidget(lbl_mdp)
        self.champ_mdp = PasswordLineEdit()
        self.champ_mdp.setPlaceholderText("••••••••")
        self.champ_mdp.returnPressed.connect(self._tenter_connexion)
        style_input(self.champ_mdp)
        self.champ_mdp.setGraphicsEffect(shadow(blur=15, y=4))
        fl.addWidget(self.champ_mdp)

        fl.addSpacing(12)

        liens = QHBoxLayout()
        liens.addStretch()
        oubli = ClickableLabel("Mot de passe oublie ?")
        oubli.clicked.connect(self._ouvrir_recuperation)
        inscrire = ClickableLabel("S'inscrire")
        inscrire.clicked.connect(self._ouvrir_inscription)
        liens.addWidget(oubli)
        liens.addSpacing(20)
        liens.addWidget(inscrire)
        fl.addLayout(liens)

        fl.addSpacing(24)

        self.bouton_connexion = AnimatedButton("Se connecter")
        self.bouton_connexion.clicked.connect(self._tenter_connexion)
        fl.addWidget(self.bouton_connexion)

        fl.addSpacing(20)

        self.label_erreur = QLabel("")
        self.label_erreur.setStyleSheet(f"color: {Theme.ERROR.name()}; font-size: 12px;")
        self.label_erreur.setAlignment(Qt.AlignCenter)
        fl.addWidget(self.label_erreur)

        fl.addStretch()
        root.addWidget(form_wrap, 1)

    def _ouvrir_inscription(self):
        dlg = InscriptionDialog(self.db, self)
        dlg.exec_()

    def _ouvrir_recuperation(self):
        dlg = RecuperationDialog(self.db, self)
        dlg.exec_()

    def _tenter_connexion(self):
        email = self.champ_email.text().strip()
        mdp = self.champ_mdp.text().strip()
        if not email or not mdp:
            self.label_erreur.setText("Veuillez remplir tous les champs.")
            return
        admin = self.db.authentifier(email, mdp)
        if admin is None:
            self.label_erreur.setText("Email ou mot de passe incorrect.")
            return
        self.label_erreur.setText("")
        self.bouton_connexion.setEnabled(False)
        self.bouton_connexion.setText("Connexion en cours...")
        QTimer.singleShot(700, lambda: self.authentifie.emit(admin))


class BrandPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def _tick(self):
        self._angle += 0.015
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, Theme.GRADIENT_START)
        grad.setColorAt(1, Theme.GRADIENT_END)
        p.fillRect(self.rect(), QBrush(grad))

        cx, cy = self.width() * 0.5, self.height() * 0.5
        p.setPen(Qt.NoPen)
        for i in range(6):
            r = 80 + i * 60 + 20 * math.sin(self._angle + i * 0.5)
            alpha = max(15, 40 - i * 6)
            p.setBrush(QColor(255, 255, 255, alpha))
            p.drawEllipse(QPointF(cx, cy), r, r)

        for i in range(18):
            t = self._angle + i * 0.7
            x = (math.sin(t) * 0.5 + 0.5) * self.width()
            y = (math.cos(t * 0.8 + i) * 0.5 + 0.5) * self.height()
            p.setBrush(QColor(255, 255, 255, 90))
            p.drawEllipse(QPointF(x, y), 3, 3)

        p.setPen(QColor(255, 255, 255, 240))
        p.setFont(QFont("Segoe UI", 26, QFont.Bold))
        p.drawText(self.rect().adjusted(0, -120, 0, 0), Qt.AlignCenter, "AdminPro")

        p.setFont(QFont("Segoe UI", 12))
        p.setPen(QColor(255, 255, 255, 180))
        p.drawText(self.rect().adjusted(0, -70, 0, 0), Qt.AlignCenter,
                    "Tableau de bord d'administration securise")

        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(255, 255, 255, 120))
        p.drawText(self.rect().adjusted(0, 200, 0, 0), Qt.AlignCenter,
                    "© 2026 AdminPro. Tous droits reserves.")


# ===========================================================================
# Carte de statistique (KPI) animee
# ===========================================================================
class StatCard(QFrame):
    def __init__(self, titre, valeur_initiale, icone, couleur, parent=None):
        super().__init__(parent)
        self.titre = titre
        self._valeur_cible = valeur_initiale
        self._valeur_affichee = 0.0
        self.icone = icone
        self.couleur = couleur
        self._build()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animer_valeur)
        self._timer.start(30)

    def _build(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.BG_CARD.name()};
                border-radius: 16px; border: 1px solid {Theme.BORDER.name()};
            }}
        """)
        self.setGraphicsEffect(shadow(blur=25, y=8))
        self.setMinimumHeight(130)
        self.setMaximumHeight(150)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(16)

        icone_frame = QFrame()
        icone_frame.setFixedSize(52, 52)
        icone_frame.setStyleSheet(
            f"background-color: {self.couleur.name()}; border-radius: 14px;"
        )
        il = QVBoxLayout(icone_frame)
        il.setContentsMargins(0, 0, 0, 0)
        lbl_icone = QLabel(self.icone)
        lbl_icone.setStyleSheet("font-size: 24px; color: white;")
        lbl_icone.setAlignment(Qt.AlignCenter)
        il.addWidget(lbl_icone)
        lay.addWidget(icone_frame)

        bloc = QVBoxLayout()
        bloc.setSpacing(4)
        self.label_titre = QLabel(self.titre)
        self.label_titre.setStyleSheet(
            f"font-size: 12px; color: {Theme.TEXT_SECONDARY.name()}; font-weight: 500;"
        )
        bloc.addWidget(self.label_titre)

        self.label_valeur = QLabel("0")
        self.label_valeur.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};"
        )
        bloc.addWidget(self.label_valeur)

        self.label_tendance = QLabel("▲ 12% ce mois")
        self.label_tendance.setStyleSheet(
            f"font-size: 11px; color: {Theme.SUCCESS.name()}; font-weight: 500;"
        )
        bloc.addWidget(self.label_tendance)

        lay.addLayout(bloc)
        lay.addStretch()

    def set_valeur(self, v):
        self._valeur_cible = float(v)

    def _animer_valeur(self):
        if abs(self._valeur_affichee - self._valeur_cible) < 0.5:
            self._valeur_affichee = self._valeur_cible
        else:
            self._valeur_affichee += (self._valeur_cible - self._valeur_affichee) * 0.12
        if self._valeur_cible >= 1000:
            self.label_valeur.setText(f"{int(self._valeur_affichee):,}".replace(",", " "))
        else:
            self.label_valeur.setText(f"{int(self._valeur_affichee)}")


# ===========================================================================
# Graphique en barres
# ===========================================================================
class BarChart(QFrame):
    def __init__(self, titre="Activite recente", parent=None):
        super().__init__(parent)
        self.titre_chart = titre
        self.donnees = []
        self.setStyleSheet(
            f"background-color: {Theme.BG_CARD.name()}; border-radius: 16px; border: 1px solid {Theme.BORDER.name()};"
        )
        self.setGraphicsEffect(shadow(blur=25, y=8))
        self.setMinimumHeight(260)
        self._anim_progress = 1.0

    def set_donnees(self, donnees):
        self.donnees = donnees
        self._anim_progress = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_anim)
        self._timer.start(20)

    def _tick_anim(self):
        self._anim_progress = min(1.0, self._anim_progress + 0.05)
        self.update()
        if self._anim_progress >= 1.0:
            self._timer.stop()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        marge_g, marge_d, marge_h, marge_b = 50, 30, 50, 40
        largeur = self.width() - marge_g - marge_d
        hauteur = self.height() - marge_h - marge_b

        p.setPen(Theme.TEXT_PRIMARY)
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.drawText(marge_g, 28, self.titre_chart)

        if not self.donnees:
            p.setPen(Theme.TEXT_MUTED)
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(self.rect(), Qt.AlignCenter, "Aucune donnee")
            return

        max_val = max(v for _, v in self.donnees) or 1
        nb = len(self.donnees)
        pas = largeur / nb
        largeur_barre = pas * 0.55

        p.setPen(QPen(Theme.BORDER, 1, Qt.DashLine))
        for i in range(5):
            y = marge_h + (hauteur / 4) * i
            p.drawLine(marge_g, int(y), marge_g + largeur, int(y))
            val = max_val * (1 - i / 4)
            p.setPen(Theme.TEXT_MUTED)
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(10, int(y) + 4, f"{int(val)}")
            p.setPen(QPen(Theme.BORDER, 1, Qt.DashLine))

        for i, (label, valeur) in enumerate(self.donnees):
            x = marge_g + i * pas + (pas - largeur_barre) / 2
            h = (valeur / max_val) * hauteur * self._anim_progress
            y = marge_h + hauteur - h
            grad = QLinearGradient(x, y, x, y + h)
            grad.setColorAt(0, Theme.ACCENT_LIGHT)
            grad.setColorAt(1, Theme.ACCENT)
            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRect(int(x), int(y), int(largeur_barre), int(h)), 6, 6)
            p.setPen(Theme.TEXT_SECONDARY)
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(
                QRect(int(x - 10), int(marge_h + hauteur + 8), int(largeur_barre + 20), 20),
                Qt.AlignCenter, label
            )


# ===========================================================================
# Graphique courbe
# ===========================================================================
class LineChart(QFrame):
    def __init__(self, titre="Trafic au fil du temps", parent=None):
        super().__init__(parent)
        self.titre_chart = titre
        self.valeurs = []
        self.setStyleSheet(
            f"background-color: {Theme.BG_CARD.name()}; border-radius: 16px; border: 1px solid {Theme.BORDER.name()};"
        )
        self.setGraphicsEffect(shadow(blur=25, y=8))
        self.setMinimumHeight(260)
        self._anim_progress = 1.0

    def set_valeurs(self, valeurs):
        self.valeurs = valeurs
        self._anim_progress = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(20)

    def _tick(self):
        self._anim_progress = min(1.0, self._anim_progress + 0.04)
        self.update()
        if self._anim_progress >= 1.0:
            self._timer.stop()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        marge_g, marge_d, marge_h, marge_b = 50, 30, 50, 30
        largeur = self.width() - marge_g - marge_d
        hauteur = self.height() - marge_h - marge_b

        p.setPen(Theme.TEXT_PRIMARY)
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.drawText(marge_g, 28, self.titre_chart)

        if len(self.valeurs) < 2:
            p.setPen(Theme.TEXT_MUTED)
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(self.rect(), Qt.AlignCenter, "Aucune donnee")
            return

        max_val = max(self.valeurs) or 1
        p.setPen(QPen(Theme.BORDER, 1, Qt.DashLine))
        for i in range(5):
            y = marge_h + (hauteur / 4) * i
            p.drawLine(marge_g, int(y), marge_g + largeur, int(y))
            val = max_val * (1 - i / 4)
            p.setPen(Theme.TEXT_MUTED)
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(10, int(y) + 4, f"{int(val)}")
            p.setPen(QPen(Theme.BORDER, 1, Qt.DashLine))

        n = len(self.valeurs)
        pas = largeur / (n - 1)
        points = []
        visible = int(n * self._anim_progress)
        for i in range(min(visible, n)):
            x = marge_g + i * pas
            y = marge_h + hauteur - (self.valeurs[i] / max_val) * hauteur
            points.append(QPointF(x, y))

        if len(points) >= 2:
            path = QPainterPath()
            path.moveTo(points[0])
            for pt in points[1:]:
                path.lineTo(pt)
            path.lineTo(points[-1].x(), marge_h + hauteur)
            path.lineTo(points[0].x(), marge_h + hauteur)
            path.closeSubpath()
            grad = QLinearGradient(0, marge_h, 0, marge_h + hauteur)
            grad.setColorAt(0, QColor(59, 130, 246, 120))
            grad.setColorAt(1, QColor(59, 130, 246, 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawPath(path)

            p.setPen(QPen(Theme.ACCENT_LIGHT, 2))
            p.setBrush(Qt.NoBrush)
            path2 = QPainterPath()
            path2.moveTo(points[0])
            for pt in points[1:]:
                path2.lineTo(pt)
            p.drawPath(path2)

            p.setBrush(Theme.ACCENT_LIGHT)
            p.setPen(Qt.NoPen)
            for pt in points:
                p.drawEllipse(pt, 4, 4)


# ===========================================================================
# Element de menu sidebar
# ===========================================================================
class SidebarItem(QPushButton):
    clic = pyqtSignal(int)

    def __init__(self, icone, texte, index, parent=None):
        super().__init__(parent)
        self.icone = icone
        self.texte = texte
        self.index = index
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setText(f"  {icone}   {texte}")
        self.setMinimumHeight(48)
        self.clicked.connect(lambda: self.clic.emit(self.index))
        self._update_style()
        self.toggled.connect(lambda _: self._update_style())

    def _update_style(self):
        base = f"""
            QPushButton {{
                text-align: left; padding: 12px 16px; border: none;
                border-radius: 12px; font-size: 14px; font-weight: 500;
                color: {Theme.TEXT_SECONDARY.name()}; background: transparent;
            }}
            QPushButton:hover {{
                color: {Theme.TEXT_PRIMARY.name()};
                background-color: {Theme.BG_CARD.name()};
            }}
        """
        if self.isChecked():
            base += f"""
                QPushButton {{
                    color: white; background-color: {Theme.ACCENT.name()};
                    font-weight: 600;
                }}
            """
        self.setStyleSheet(base)


# ===========================================================================
# Carte de profil pour la page Parametres
# ===========================================================================
class ProfileCard(QFrame):
    def __init__(self, nom_admin, email, parent=None):
        super().__init__(parent)
        self.nom_admin = nom_admin
        self.email = email
        self._build()

    def _build(self):
        self.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_CARD.name()}; border-radius: 16px; border: 1px solid {Theme.BORDER.name()}; }}"
        )
        self.setGraphicsEffect(shadow(blur=25, y=8))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(16)
        lay.setAlignment(Qt.AlignCenter)

        avatar = AvatarWidget(self.nom_admin[:2].upper(), taille=100)
        lay.addWidget(avatar, alignment=Qt.AlignCenter)

        nom = QLabel(self.nom_admin)
        nom.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        nom.setAlignment(Qt.AlignCenter)
        lay.addWidget(nom)

        role = QLabel("Administrateur")
        role.setStyleSheet(f"font-size: 14px; color: {Theme.TEXT_SECONDARY.name()};")
        role.setAlignment(Qt.AlignCenter)
        lay.addWidget(role)

        email = QLabel(self.email)
        email.setStyleSheet(f"font-size: 12px; color: {Theme.TEXT_MUTED.name()};")
        email.setAlignment(Qt.AlignCenter)
        lay.addWidget(email)


# ===========================================================================
# Pages du dashboard
# ===========================================================================
class PageDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)

        cartes_layout = QHBoxLayout()
        cartes_layout.setSpacing(20)
        self.cartes = []
        specs = [
            ("Total Utilisateurs", 12480, "👥", Theme.ACCENT),
            ("Revenus (€)", 84520, "💰", Theme.SUCCESS),
            ("Commandes", 1284, "📦", Theme.WARNING),
            ("Trafic Site", 38290, "📈", QColor("#8b5cf6")),
        ]
        for titre_c, val, icone, couleur in specs:
            c = StatCard(titre_c, val, icone, couleur)
            self.cartes.append(c)
            cartes_layout.addWidget(c)
        lay.addLayout(cartes_layout)

        graph_layout = QHBoxLayout()
        graph_layout.setSpacing(20)
        self.line_chart = LineChart("Trafic au fil du temps")
        self.line_chart.set_valeurs([random.randint(40, 120) for _ in range(14)])
        graph_layout.addWidget(self.line_chart, 2)
        self.bar_chart = BarChart("Activite recente")
        self.bar_chart.set_donnees(
            [(j, random.randint(20, 100)) for j in ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]]
        )
        graph_layout.addWidget(self.bar_chart, 1)
        lay.addLayout(graph_layout)

        lay.addWidget(self._table_activites())

    def _table_activites(self):
        table_frame = QFrame()
        table_frame.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_CARD.name()}; border-radius: 16px; border: 1px solid {Theme.BORDER.name()}; }}"
        )
        table_frame.setGraphicsEffect(shadow(blur=25, y=8))
        tl = QVBoxLayout(table_frame)
        tl.setContentsMargins(20, 20, 20, 20)
        titre = QLabel("Activites recentes")
        titre.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        tl.addWidget(titre)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Utilisateur", "Action", "Date", "Statut"])
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent; color: {Theme.TEXT_PRIMARY.name()};
                border: none; gridline-color: {Theme.BORDER.name()};
            }}
            QHeaderView::section {{
                background-color: transparent; color: {Theme.TEXT_SECONDARY.name()};
                border: none; border-bottom: 1px solid {Theme.BORDER.name()};
                padding: 8px; font-weight: 600;
            }}
            QTableWidget::item {{ padding: 10px; border-bottom: 1px solid {Theme.BORDER.name()}; }}
        """)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setVisible(False)

        actions = [
            ("Marie Dupont", "Connexion", "2026-08-28 14:32", "Reussie"),
            ("Jean Martin", "Cree un produit", "2026-08-28 13:15", "Reussie"),
            ("Sophie Bernard", "Modifie parametres", "2026-08-28 12:48", "Reussie"),
            ("Luc Petit", "Tentative connexion", "2026-08-28 11:20", "Echec"),
            ("Claire Moreau", "Supprime utilisateur", "2026-08-28 10:05", "Reussie"),
            ("Paul Girard", "Export donnees", "2026-08-28 09:40", "Reussie"),
        ]
        for user, action, date, statut in actions:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(user))
            table.setItem(row, 1, QTableWidgetItem(action))
            table.setItem(row, 2, QTableWidgetItem(date))
            item = QTableWidgetItem(statut)
            item.setForeground(Theme.SUCCESS if statut == "Reussie" else Theme.ERROR)
            table.setItem(row, 3, item)

        tl.addWidget(table)
        return table_frame

    def rafraichir(self):
        for c in self.cartes:
            c.set_valeur(c._valeur_cible + random.randint(-50, 80))
        self.line_chart.set_valeurs([random.randint(40, 120) for _ in range(14)])
        self.bar_chart.set_donnees(
            [(j, random.randint(20, 100)) for j in ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]]
        )


class PageUtilisateurs(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)

        barre = QHBoxLayout()
        barre.addStretch()
        bouton_ajouter = AnimatedButton("+ Ajouter un utilisateur")
        barre.addWidget(bouton_ajouter)
        lay.addLayout(barre)

        table_frame = QFrame()
        table_frame.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_CARD.name()}; border-radius: 16px; border: 1px solid {Theme.BORDER.name()}; }}"
        )
        table_frame.setGraphicsEffect(shadow(blur=25, y=8))
        tl = QVBoxLayout(table_frame)
        tl.setContentsMargins(20, 20, 20, 20)
        titre = QLabel("Liste des utilisateurs")
        titre.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        tl.addWidget(titre)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Nom", "Email", "Role", "Inscrit le", "Statut"])
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent; color: {Theme.TEXT_PRIMARY.name()};
                border: none; gridline-color: {Theme.BORDER.name()};
            }}
            QHeaderView::section {{
                background-color: transparent; color: {Theme.TEXT_SECONDARY.name()};
                border: none; border-bottom: 1px solid {Theme.BORDER.name()};
                padding: 8px; font-weight: 600;
            }}
            QTableWidget::item {{ padding: 10px; border-bottom: 1px solid {Theme.BORDER.name()}; }}
        """)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setVisible(False)

        users = [
            ("Marie Dupont", "marie.d@entreprise.com", "Admin", "2025-03-12", "Actif"),
            ("Jean Martin", "jean.m@entreprise.com", "Editeur", "2025-05-20", "Actif"),
            ("Sophie Bernard", "sophie.b@entreprise.com", "Editeur", "2025-06-01", "Actif"),
            ("Luc Petit", "luc.p@entreprise.com", "Utilisateur", "2025-07-15", "Suspendu"),
            ("Claire Moreau", "claire.m@entreprise.com", "Admin", "2025-01-08", "Actif"),
            ("Paul Girard", "paul.g@entreprise.com", "Utilisateur", "2025-08-03", "Actif"),
            ("Anna Lefevre", "anna.l@entreprise.com", "Utilisateur", "2025-04-22", "Inactif"),
            ("Tom Rousseau", "tom.r@entreprise.com", "Editeur", "2025-02-14", "Actif"),
        ]
        for nom, email, role, inscrit, statut in users:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(nom))
            table.setItem(row, 1, QTableWidgetItem(email))
            table.setItem(row, 2, QTableWidgetItem(role))
            table.setItem(row, 3, QTableWidgetItem(inscrit))
            item = QTableWidgetItem(statut)
            if statut == "Actif":
                item.setForeground(Theme.SUCCESS)
            elif statut == "Suspendu":
                item.setForeground(Theme.ERROR)
            else:
                item.setForeground(Theme.TEXT_MUTED)
            table.setItem(row, 4, item)

        tl.addWidget(table)
        lay.addWidget(table_frame)


class PageProduits(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)

        cartes = QHBoxLayout()
        cartes.setSpacing(20)
        for titre_c, val, icone, couleur in [
            ("Total Produits", 348, "📦", Theme.ACCENT),
            ("En stock", 291, "✅", Theme.SUCCESS),
            ("Rupture", 12, "⚠️", Theme.ERROR),
            ("Categories", 18, "🏷️", QColor("#8b5cf6")),
        ]:
            cartes.addWidget(StatCard(titre_c, val, icone, couleur))
        lay.addLayout(cartes)

        table_frame = QFrame()
        table_frame.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_CARD.name()}; border-radius: 16px; border: 1px solid {Theme.BORDER.name()}; }}"
        )
        table_frame.setGraphicsEffect(shadow(blur=25, y=8))
        tl = QVBoxLayout(table_frame)
        tl.setContentsMargins(20, 20, 20, 20)
        titre = QLabel("Inventaire des produits")
        titre.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        tl.addWidget(titre)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Produit", "Categorie", "Prix (€)", "Stock", "Statut"])
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent; color: {Theme.TEXT_PRIMARY.name()};
                border: none; gridline-color: {Theme.BORDER.name()};
            }}
            QHeaderView::section {{
                background-color: transparent; color: {Theme.TEXT_SECONDARY.name()};
                border: none; border-bottom: 1px solid {Theme.BORDER.name()};
                padding: 8px; font-weight: 600;
            }}
            QTableWidget::item {{ padding: 10px; border-bottom: 1px solid {Theme.BORDER.name()}; }}
        """)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setVisible(False)

        produits = [
            ("Ordinateur portable Pro 15", "Informatique", "1299", "45", "En stock"),
            ("Souris sans fil", "Accessoires", "29", "120", "En stock"),
            ("Clavier mecanique RGB", "Accessoires", "89", "0", "Rupture"),
            ("Ecran 27 pouces 4K", "Informatique", "449", "18", "En stock"),
            ("Casque audio ANC", "Audio", "199", "32", "En stock"),
            ("Webcam HD 1080p", "Accessoires", "59", "5", "Faible stock"),
            ("Disque SSD 1To", "Stockage", "109", "78", "En stock"),
            ("Routeur WiFi 6", "Reseau", "159", "0", "Rupture"),
        ]
        for nom, cat, prix, stock, statut in produits:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(nom))
            table.setItem(row, 1, QTableWidgetItem(cat))
            table.setItem(row, 2, QTableWidgetItem(prix))
            table.setItem(row, 3, QTableWidgetItem(stock))
            item = QTableWidgetItem(statut)
            if statut == "En stock":
                item.setForeground(Theme.SUCCESS)
            elif statut == "Rupture":
                item.setForeground(Theme.ERROR)
            else:
                item.setForeground(Theme.WARNING)
            table.setItem(row, 4, item)

        tl.addWidget(table)
        lay.addWidget(table_frame)


class PageStatistiques(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)

        cartes = QHBoxLayout()
        cartes.setSpacing(20)
        for titre_c, val, icone, couleur in [
            ("Visiteurs uniques", 38290, "👁️", Theme.ACCENT),
            ("Taux conversion", "4.2%", "🎯", Theme.SUCCESS),
            ("Panier moyen", "67€", "🛒", Theme.WARNING),
            ("Taux rebond", "32%", "↩️", QColor("#8b5cf6")),
        ]:
            c = StatCard(titre_c, val if isinstance(val, (int, float)) else 0, icone, couleur)
            if isinstance(val, str):
                c.label_valeur.setText(val)
                c._valeur_cible = 0
            cartes.addWidget(c)
        lay.addLayout(cartes)

        graph_row = QHBoxLayout()
        graph_row.setSpacing(20)

        self.line1 = LineChart("Visiteurs (30 derniers jours)")
        self.line1.set_valeurs([random.randint(100, 500) for _ in range(30)])
        graph_row.addWidget(self.line1, 1)

        self.line2 = LineChart("Revenus (30 derniers jours)")
        self.line2.set_valeurs([random.randint(50, 300) for _ in range(30)])
        graph_row.addWidget(self.line2, 1)

        lay.addLayout(graph_row)

        self.bar = BarChart("Top categories par ventes")
        self.bar.set_donnees([
            ("Informatique", 340), ("Accessoires", 280), ("Audio", 190),
            ("Stockage", 150), ("Reseau", 95),
        ])
        lay.addWidget(self.bar)

    def rafraichir(self):
        self.line1.set_valeurs([random.randint(100, 500) for _ in range(30)])
        self.line2.set_valeurs([random.randint(50, 300) for _ in range(30)])
        self.bar.set_donnees([
            ("Informatique", random.randint(200, 400)), ("Accessoires", random.randint(150, 300)),
            ("Audio", random.randint(100, 250)), ("Stockage", random.randint(80, 200)),
            ("Reseau", random.randint(50, 150)),
        ])


class PageParametres(QWidget):
    deconnexion_demandee = pyqtSignal()

    def __init__(self, admin, db, parent=None):
        super().__init__(parent)
        self.admin = admin
        self.db = db
        self.nom_admin = nom_depuis_email(admin["email"])
        self._build()
        self._charger_admins()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: transparent; }}"
        )

        contenu = QWidget()
        contenu.setStyleSheet("background-color: transparent;")
        cl = QVBoxLayout(contenu)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(24)

        cl.addWidget(ProfileCard(self.nom_admin, self.admin["email"]))

        info_frame = QFrame()
        info_frame.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_CARD.name()}; border-radius: 16px; border: 1px solid {Theme.BORDER.name()}; }}"
        )
        info_frame.setGraphicsEffect(shadow(blur=25, y=8))
        il = QVBoxLayout(info_frame)
        il.setContentsMargins(24, 24, 24, 24)
        il.setSpacing(16)

        titre_info = QLabel("Informations du compte")
        titre_info.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        il.addWidget(titre_info)

        for label_text, valeur in [
            ("Nom complet", self.nom_admin),
            ("Email", self.admin["email"]),
            ("Telephone", self.admin["telephone"]),
            ("Role", "Administrateur"),
        ]:
            ligne = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"font-size: 13px; color: {Theme.TEXT_SECONDARY.name()}; font-weight: 500;")
            lbl.setFixedWidth(180)
            ligne.addWidget(lbl)
            val = QLabel(valeur)
            val.setStyleSheet(f"font-size: 14px; color: {Theme.TEXT_PRIMARY.name()};")
            ligne.addWidget(val)
            ligne.addStretch()
            il.addLayout(ligne)

        cl.addWidget(info_frame)

        admin_frame = QFrame()
        admin_frame.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_CARD.name()}; border-radius: 16px; border: 1px solid {Theme.BORDER.name()}; }}"
        )
        admin_frame.setGraphicsEffect(shadow(blur=25, y=8))
        al = QVBoxLayout(admin_frame)
        al.setContentsMargins(24, 24, 24, 24)
        al.setSpacing(16)

        titre_row = QHBoxLayout()
        titre_adm = QLabel("Comptes administrateurs (max. {0})".format(MAX_ADMINS))
        titre_adm.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        titre_row.addWidget(titre_adm)
        titre_row.addStretch()
        self.bouton_nouvel_admin = AnimatedButton("+ Inscrire")
        self.bouton_nouvel_admin.clicked.connect(self._inscrire)
        titre_row.addWidget(self.bouton_nouvel_admin)
        al.addLayout(titre_row)

        self.table_admins = QTableWidget(0, 4)
        self.table_admins.setHorizontalHeaderLabels(["Email", "Telephone", "Inscrit le", "Actions"])
        self.table_admins.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent; color: {Theme.TEXT_PRIMARY.name()};
                border: none; gridline-color: {Theme.BORDER.name()};
            }}
            QHeaderView::section {{
                background-color: transparent; color: {Theme.TEXT_SECONDARY.name()};
                border: none; border-bottom: 1px solid {Theme.BORDER.name()};
                padding: 8px; font-weight: 600;
            }}
            QTableWidget::item {{ padding: 10px; border-bottom: 1px solid {Theme.BORDER.name()}; }}
        """)
        self.table_admins.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_admins.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_admins.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_admins.verticalHeader().setVisible(False)
        self.table_admins.setMinimumHeight(140)
        al.addWidget(self.table_admins)
        cl.addWidget(admin_frame)

        pref_frame = QFrame()
        pref_frame.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_CARD.name()}; border-radius: 16px; border: 1px solid {Theme.BORDER.name()}; }}"
        )
        pref_frame.setGraphicsEffect(shadow(blur=25, y=8))
        pl = QVBoxLayout(pref_frame)
        pl.setContentsMargins(24, 24, 24, 24)
        pl.setSpacing(16)

        titre_pref = QLabel("Preferences")
        titre_pref.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        pl.addWidget(titre_pref)

        for label_text in ["Notifications par email", "Notifications push", "Mode sombre", "Langue : Francais"]:
            ligne = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"font-size: 14px; color: {Theme.TEXT_PRIMARY.name()};")
            ligne.addWidget(lbl)
            ligne.addStretch()
            toggle = QPushButton("ON")
            toggle.setFixedSize(60, 28)
            toggle.setCursor(Qt.PointingHandCursor)
            toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.SUCCESS.name()}; color: white;
                    border: none; border-radius: 14px; font-size: 11px; font-weight: 700;
                }}
            """)
            ligne.addWidget(toggle)
            pl.addLayout(ligne)

        cl.addWidget(pref_frame)

        bouton_dec = AnimatedButton("Se deconnecter")
        bouton_dec.clicked.connect(self.deconnexion_demandee.emit)
        cl.addWidget(bouton_dec)

        cl.addStretch()
        scroll.setWidget(contenu)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _charger_admins(self):
        self.table_admins.setRowCount(0)
        admins = self.db.lister()
        self.bouton_nouvel_admin.setEnabled(len(admins) < MAX_ADMINS)
        for adm in admins:
            row = self.table_admins.rowCount()
            self.table_admins.insertRow(row)
            self.table_admins.setItem(row, 0, QTableWidgetItem(adm["email"]))
            self.table_admins.setItem(row, 1, QTableWidgetItem(adm["telephone"]))
            self.table_admins.setItem(row, 2, QTableWidgetItem(adm["created_at"]))
            actions = QWidget()
            hl = QHBoxLayout(actions)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(8)
            btn_mod = QPushButton("Modifier")
            btn_sup = QPushButton("Supprimer")
            for b, accent in ((btn_mod, Theme.ACCENT), (btn_sup, Theme.ERROR)):
                b.setCursor(Qt.PointingHandCursor)
                b.setStyleSheet(
                    f"QPushButton {{ background-color: {accent.name()}; color: white; "
                    f"border: none; border-radius: 8px; padding: 6px 12px; font-size: 12px; }}"
                )
            admin_id = adm["id"]
            btn_mod.clicked.connect(lambda _c=False, i=admin_id: self._modifier(i))
            btn_sup.clicked.connect(lambda _c=False, i=admin_id: self._supprimer(i))
            hl.addWidget(btn_mod)
            hl.addWidget(btn_sup)
            hl.addStretch()
            self.table_admins.setCellWidget(row, 3, actions)
            self.table_admins.setRowHeight(row, 48)

    def _inscrire(self):
        dlg = InscriptionDialog(self.db, self)
        if dlg.exec_() == QDialog.Accepted:
            self._charger_admins()

    def _modifier(self, admin_id):
        adm = self.db.par_id(admin_id)
        if not adm:
            return
        dlg = EditionAdminDialog(self.db, adm, self)
        if dlg.exec_() == QDialog.Accepted:
            self._charger_admins()

    def _supprimer(self, admin_id):
        reponse = QMessageBox.question(
            self,
            "Supprimer",
            "Supprimer cet administrateur ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reponse != QMessageBox.Yes:
            return
        ok, msg = self.db.supprimer(admin_id)
        if not ok:
            QMessageBox.warning(self, "Erreur", msg)
            return
        if admin_id == self.admin["id"]:
            self.deconnexion_demandee.emit()
            return
        self._charger_admins()


# ===========================================================================
# Dashboard principal (apres connexion)
# ===========================================================================
class Dashboard(QWidget):
    deconnexion_demandee = pyqtSignal()

    def __init__(self, admin, db, parent=None):
        super().__init__(parent)
        self.admin = admin
        self.db = db
        self.nom_admin = nom_depuis_email(admin["email"])
        self._initiales = "".join([w[0].upper() for w in self.nom_admin.split()[:2] if w]) or self.nom_admin[:2].upper()
        self._build_ui()
        self._demarrer_animations()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_SIDEBAR.name()}; border-right: 1px solid {Theme.BORDER.name()}; }}"
        )
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(16, 24, 16, 24)
        sb.setSpacing(8)

        logo = QLabel("  ⬡ AdminPro")
        logo.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()}; padding: 8px;")
        sb.addWidget(logo)
        sb.addSpacing(20)

        sec = QLabel("MENU PRINCIPAL")
        sec.setStyleSheet(
            f"font-size: 10px; font-weight: 700; color: {Theme.TEXT_MUTED.name()}; letter-spacing: 2px; padding: 8px;"
        )
        sb.addWidget(sec)

        self.items_menu = []
        menus = [
            ("📊", "Tableau de bord"),
            ("👥", "Utilisateurs"),
            ("📦", "Produits"),
            ("📈", "Statistiques"),
            ("⚙️", "Parametres"),
        ]
        for i, (icone, texte) in enumerate(menus):
            item = SidebarItem(icone, texte, i)
            item.clic.connect(self._changer_page)
            if i == 0:
                item.setChecked(True)
            self.items_menu.append(item)
            sb.addWidget(item)

        sb.addStretch()

        profil_frame = QFrame()
        profil_frame.setStyleSheet(
            f"QFrame {{ background-color: {Theme.BG_CARD.name()}; border-radius: 12px; }}"
        )
        pl = QHBoxLayout(profil_frame)
        pl.setContentsMargins(12, 10, 12, 10)
        pl.setSpacing(10)
        avatar = AvatarWidget(self._initiales, taille=38)
        pl.addWidget(avatar)
        info = QVBoxLayout()
        info.setSpacing(0)
        nom = QLabel(self.nom_admin)
        nom.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Theme.TEXT_PRIMARY.name()};")
        role = QLabel("Administrateur")
        role.setStyleSheet(f"font-size: 11px; color: {Theme.TEXT_MUTED.name()};")
        info.addWidget(nom)
        info.addWidget(role)
        pl.addLayout(info)
        sb.addWidget(profil_frame)

        root.addWidget(sidebar)

        main = QWidget()
        main.setStyleSheet(f"background-color: {Theme.BG_APP.name()};")
        ml = QVBoxLayout(main)
        ml.setContentsMargins(32, 24, 32, 24)
        ml.setSpacing(20)

        header = QHBoxLayout()
        self.label_titre = QLabel("Tableau de bord")
        self.label_titre.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Theme.TEXT_PRIMARY.name()};")
        header.addWidget(self.label_titre)
        header.addStretch()

        recherche = QLineEdit()
        recherche.setPlaceholderText("🔍  Rechercher...")
        recherche.setFixedWidth(280)
        recherche.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Theme.BG_CARD.name()}; color: {Theme.TEXT_PRIMARY.name()};
                border: 1px solid {Theme.BORDER.name()}; border-radius: 10px;
                padding: 10px 16px; font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {Theme.ACCENT.name()}; }}
        """)
        header.addWidget(recherche)

        notif = QToolButton()
        notif.setText("🔔")
        notif.setStyleSheet(
            f"QToolButton {{ background-color: {Theme.BG_CARD.name()}; border: none; border-radius: 10px; "
            f"padding: 8px 12px; font-size: 16px; }}"
            f"QToolButton:hover {{ background-color: {Theme.BG_CARD_HOVER.name()}; }}"
        )
        header.addWidget(notif)

        self.bouton_compte = QToolButton()
        self.bouton_compte.setText("  " + self._initiales + "  ")
        self.bouton_compte.setStyleSheet(
            f"QToolButton {{ background-color: {Theme.ACCENT.name()}; color: white; border-radius: 18px; "
            f"padding: 6px; font-size: 12px; font-weight: 700; min-width: 36px; max-width: 36px; }}"
        )
        self.bouton_compte.setPopupMode(QToolButton.InstantPopup)
        menu_compte = QMenu(self.bouton_compte)
        menu_compte.setStyleSheet(f"""
            QMenu {{
                background-color: {Theme.BG_CARD.name()}; color: {Theme.TEXT_PRIMARY.name()};
                border: 1px solid {Theme.BORDER.name()}; border-radius: 10px; padding: 8px;
            }}
            QMenu::item {{ padding: 8px 24px; border-radius: 6px; }}
            QMenu::item:selected {{ background-color: {Theme.BG_CARD_HOVER.name()}; }}
        """)
        action_profil = QAction("👤  Mon profil", self)
        action_parametres = QAction("⚙️  Parametres", self)
        action_parametres.triggered.connect(lambda: self._changer_page(4))
        action_profil.triggered.connect(lambda: self._changer_page(4))
        action_deconnexion = QAction("🚪  Deconnexion", self)
        action_deconnexion.triggered.connect(self.deconnexion_demandee.emit)
        menu_compte.addAction(action_profil)
        menu_compte.addAction(action_parametres)
        menu_compte.addSeparator()
        menu_compte.addAction(action_deconnexion)
        self.bouton_compte.setMenu(menu_compte)
        header.addWidget(self.bouton_compte)

        ml.addLayout(header)

        self.stack_pages = QStackedWidget()
        self.page_dashboard = PageDashboard()
        self.page_users = PageUtilisateurs()
        self.page_produits = PageProduits()
        self.page_stats = PageStatistiques()
        self.page_parametres = PageParametres(self.admin, self.db)
        self.page_parametres.deconnexion_demandee.connect(self.deconnexion_demandee.emit)

        self.stack_pages.addWidget(self.page_dashboard)
        self.stack_pages.addWidget(self.page_users)
        self.stack_pages.addWidget(self.page_produits)
        self.stack_pages.addWidget(self.page_stats)
        self.stack_pages.addWidget(self.page_parametres)

        ml.addWidget(self.stack_pages)
        root.addWidget(main, 1)

    def _changer_page(self, index):
        self.stack_pages.setCurrentIndex(index)
        titres = ["Tableau de bord", "Utilisateurs", "Produits", "Statistiques", "Parametres"]
        self.label_titre.setText(titres[index])
        for i, item in enumerate(self.items_menu):
            item.setChecked(i == index)
        if index == 4:
            self.page_parametres._charger_admins()

    def _demarrer_animations(self):
        self._timer_live = QTimer(self)
        self._timer_live.timeout.connect(self._rafraichir_live)
        self._timer_live.start(5000)

    def _rafraichir_live(self):
        self.page_dashboard.rafraichir()
        self.page_stats.rafraichir()


# ===========================================================================
# Fenetre principale
# ===========================================================================
class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("AdminPro - Dashboard Administrateur")
        self.resize(1280, 800)
        self.setMinimumSize(QSize(1100, 700))

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login = LoginScreen(self.db)
        self.login.authentifie.connect(self._on_connexion)
        self.stack.addWidget(self.login)
        self.dashboard = None

    def _on_connexion(self, admin):
        self.dashboard = Dashboard(admin, self.db)
        self.dashboard.deconnexion_demandee.connect(self._on_deconnexion)
        self.stack.addWidget(self.dashboard)
        self.stack.setCurrentWidget(self.dashboard)

    def _on_deconnexion(self):
        if self.dashboard is not None:
            self.stack.removeWidget(self.dashboard)
            self.dashboard.deleteLater()
            self.dashboard = None
        self.stack.setCurrentWidget(self.login)
        self.login.champ_mdp.clear()
        self.login.label_erreur.setText("")
        self.login.bouton_connexion.setEnabled(True)
        self.login.bouton_connexion.setText("Se connecter")


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    db = AdminDB()
    fenetre = MainWindow(db)
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
