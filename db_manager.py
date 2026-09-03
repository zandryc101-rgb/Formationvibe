#!/usr/bin/env python3
"""
Petite interface PyQt5 pour consulter, modifier et supprimer
les donnees SQLite gerees par db.py (fichier adminpro.db).

Lancement :
    python db_manager.py
"""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from db import AdminDB, MAX_ADMINS, email_valide, telephone_valide
from password_edit import PasswordLineEdit

BG = "#0f172a"
CARD = "#1e293b"
BORDER = "#334155"
TEXT = "#f1f5f9"
MUTED = "#94a3b8"
ACCENT = "#3b82f6"
DANGER = "#ef4444"
SUCCESS = "#10b981"


def _style_app(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(
        f"""
        QWidget {{
            color: {TEXT};
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
            background-color: {BG};
        }}
        QMainWindow, QDialog {{ background-color: {BG}; }}
        QLabel#titre {{
            font-size: 20px;
            font-weight: 700;
            color: {TEXT};
        }}
        QLabel#sous {{ color: {MUTED}; }}
        QLineEdit {{
            background-color: {CARD};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 8px 12px;
        }}
        QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
        QToolButton {{
            border: none;
            background: transparent;
        }}
        QPushButton {{
            background-color: {ACCENT};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background-color: #2563eb; }}
        QPushButton:disabled {{ background-color: {BORDER}; color: {MUTED}; }}
        QPushButton#danger {{ background-color: {DANGER}; }}
        QPushButton#danger:hover {{ background-color: #dc2626; }}
        QPushButton#ghost {{
            background-color: transparent;
            border: 1px solid {BORDER};
            color: {TEXT};
        }}
        QPushButton#ghost:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
        QTableWidget {{
            background-color: {CARD};
            alternate-background-color: #172033;
            gridline-color: {BORDER};
            border: 1px solid {BORDER};
            border-radius: 10px;
            selection-background-color: {ACCENT};
            selection-color: white;
        }}
        QHeaderView::section {{
            background-color: #111827;
            color: {MUTED};
            padding: 8px;
            border: none;
            border-bottom: 1px solid {BORDER};
            font-weight: 600;
        }}
        QListWidget {{
            background-color: {CARD};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 6px;
        }}
        QListWidget::item {{
            padding: 8px 10px;
            border-radius: 6px;
        }}
        QListWidget::item:selected {{
            background-color: {ACCENT};
            color: white;
        }}
        """
    )


class FormulaireAdmin(QDialog):
    def __init__(self, parent=None, titre="Modifier", admin=None, creer=False):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.setMinimumWidth(420)
        self.creer = creer
        self.admin = admin or {}

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        titre_lbl = QLabel(titre)
        titre_lbl.setObjectName("titre")
        layout.addWidget(titre_lbl)

        form = QFormLayout()
        form.setSpacing(10)
        self.email = QLineEdit(self.admin.get("email", ""))
        self.telephone = QLineEdit(self.admin.get("telephone", ""))
        self.mdp = PasswordLineEdit()
        if creer:
            self.mdp.setPlaceholderText("Minimum 6 caracteres")
        else:
            self.mdp.setPlaceholderText("Laisser vide pour ne pas changer")
        form.addRow("Email", self.email)
        form.addRow("Telephone", self.telephone)
        form.addRow("Mot de passe", self.mdp)
        layout.addLayout(form)

        boutons = QHBoxLayout()
        boutons.addStretch()
        annuler = QPushButton("Annuler")
        annuler.setObjectName("ghost")
        annuler.clicked.connect(self.reject)
        ok = QPushButton("Enregistrer")
        ok.clicked.connect(self._valider)
        boutons.addWidget(annuler)
        boutons.addWidget(ok)
        layout.addLayout(boutons)

    def _valider(self):
        email = self.email.text().strip()
        tel = self.telephone.text().strip()
        mdp = self.mdp.text()
        if not email_valide(email):
            QMessageBox.warning(self, "Validation", "Adresse email invalide.")
            return
        if not telephone_valide(tel):
            QMessageBox.warning(self, "Validation", "Numero de telephone invalide.")
            return
        if self.creer and len(mdp) < 6:
            QMessageBox.warning(self, "Validation", "Le mot de passe doit contenir au moins 6 caracteres.")
            return
        if (not self.creer) and mdp and len(mdp) < 6:
            QMessageBox.warning(self, "Validation", "Le mot de passe doit contenir au moins 6 caracteres.")
            return
        self.accept()

    def valeurs(self):
        mdp = self.mdp.text()
        return {
            "email": self.email.text().strip(),
            "telephone": self.telephone.text().strip(),
            "mot_de_passe": mdp if mdp else None,
        }


class DbManagerWindow(QMainWindow):
    COLONNES = ["id", "email", "telephone", "created_at", "updated_at"]

    def __init__(self):
        super().__init__()
        self.db = AdminDB()
        self.setWindowTitle("AdminPro — Gestion SQLite")
        self.resize(980, 560)

        central = QWidget()
        self.setCentralWidget(central)
        racine = QVBoxLayout(central)
        racine.setContentsMargins(20, 18, 20, 18)
        racine.setSpacing(12)

        en_tete = QHBoxLayout()
        bloc_titre = QVBoxLayout()
        titre = QLabel("Base SQLite")
        titre.setObjectName("titre")
        self.sous_titre = QLabel()
        self.sous_titre.setObjectName("sous")
        self.sous_titre.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bloc_titre.addWidget(titre)
        bloc_titre.addWidget(self.sous_titre)
        en_tete.addLayout(bloc_titre, 1)

        self.btn_rafraichir = QPushButton("Afficher / Actualiser")
        self.btn_rafraichir.clicked.connect(self.charger)
        self.btn_ajouter = QPushButton("Ajouter")
        self.btn_ajouter.clicked.connect(self.ajouter)
        self.btn_modifier = QPushButton("Update")
        self.btn_modifier.clicked.connect(self.modifier)
        self.btn_supprimer = QPushButton("Delete")
        self.btn_supprimer.setObjectName("danger")
        self.btn_supprimer.clicked.connect(self.supprimer)
        for b in (self.btn_rafraichir, self.btn_ajouter, self.btn_modifier, self.btn_supprimer):
            en_tete.addWidget(b, 0, Qt.AlignTop)
        racine.addLayout(en_tete)

        split = QSplitter(Qt.Horizontal)

        gauche = QWidget()
        g_lay = QVBoxLayout(gauche)
        g_lay.setContentsMargins(0, 0, 8, 0)
        lbl_tables = QLabel("Tables de la base")
        lbl_tables.setObjectName("sous")
        g_lay.addWidget(lbl_tables)
        self.liste_tables = QListWidget()
        self.liste_tables.currentItemChanged.connect(self._table_changee)
        g_lay.addWidget(self.liste_tables)
        split.addWidget(gauche)

        droite = QWidget()
        d_lay = QVBoxLayout(droite)
        d_lay.setContentsMargins(8, 0, 0, 0)
        self.info_table = QLabel("Selectionnez une table")
        self.info_table.setObjectName("sous")
        d_lay.addWidget(self.info_table)
        self.table = QTableWidget(0, len(self.COLONNES))
        self.table.setHorizontalHeaderLabels(self.COLONNES)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(self.modifier)
        self.table.itemSelectionChanged.connect(self._maj_boutons)
        d_lay.addWidget(self.table)
        split.addWidget(droite)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 4)
        racine.addWidget(split, 1)

        self.statut = QLabel()
        self.statut.setObjectName("sous")
        racine.addWidget(self.statut)

        self.charger()

    def _admin_selectionne(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return self.db.par_id(int(item.text()))

    def charger(self):
        self.sous_titre.setText("Fichier : {0}".format(self.db.chemin_fichier()))
        self.liste_tables.blockSignals(True)
        self.liste_tables.clear()
        tables = self.db.tables()
        for nom in tables:
            item = QListWidgetItem(nom)
            item.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
            self.liste_tables.addItem(item)
        self.liste_tables.blockSignals(False)
        if tables:
            self.liste_tables.setCurrentRow(0)
            self._afficher_table(tables[0])
        else:
            self.table.setRowCount(0)
            self.info_table.setText("Aucune table dans la base.")
        self._maj_boutons()

    def _table_changee(self, courant, _precedent):
        if courant is None:
            return
        self._afficher_table(courant.text())

    def _afficher_table(self, nom: str):
        if nom != "admins":
            self.table.setRowCount(0)
            self.info_table.setText(
                "Table « {0} » : affichage et edition prevus pour la table admins.".format(nom)
            )
            self.statut.setText("Table selectionnee : {0}".format(nom))
            self._maj_boutons()
            return

        lignes = self.db.lister()
        self.table.setRowCount(len(lignes))
        for i, admin in enumerate(lignes):
            for j, col in enumerate(self.COLONNES):
                val = "" if admin.get(col) is None else str(admin[col])
                cell = QTableWidgetItem(val)
                cell.setFlags(cell.flags() ^ Qt.ItemIsEditable)
                if j == 0:
                    cell.setForeground(QColor(ACCENT))
                self.table.setItem(i, j, cell)
        places = self.db.places_restantes()
        self.info_table.setText(
            "Table admins — {0} enregistrement(s), {1} place(s) restante(s) (max {2}).".format(
                len(lignes), places, MAX_ADMINS
            )
        )
        self.statut.setText("Donnees chargees depuis SQLite. Double-clic pour modifier.")
        if lignes:
            self.table.selectRow(0)
        self._maj_boutons()

    def _maj_boutons(self):
        table_admins = (
            self.liste_tables.currentItem() is not None
            and self.liste_tables.currentItem().text() == "admins"
        )
        a_une_ligne = table_admins and self.table.currentRow() >= 0 and self.table.rowCount() > 0
        self.btn_ajouter.setEnabled(table_admins and self.db.inscription_autorisee())
        self.btn_modifier.setEnabled(a_une_ligne)
        self.btn_supprimer.setEnabled(a_une_ligne)

    def ajouter(self):
        dlg = FormulaireAdmin(self, titre="Ajouter un administrateur", creer=True)
        if dlg.exec_() != QDialog.Accepted:
            return
        v = dlg.valeurs()
        ok, msg, _admin = self.db.creer(v["email"], v["mot_de_passe"] or "", v["telephone"])
        if ok:
            QMessageBox.information(self, "Ajout", msg)
            self.charger()
        else:
            QMessageBox.warning(self, "Ajout", msg)

    def modifier(self):
        admin = self._admin_selectionne()
        if admin is None:
            QMessageBox.information(self, "Update", "Selectionnez une ligne a modifier.")
            return
        dlg = FormulaireAdmin(self, titre="Update — administrateur #{0}".format(admin["id"]), admin=admin)
        if dlg.exec_() != QDialog.Accepted:
            return
        v = dlg.valeurs()
        ok, msg = self.db.modifier(admin["id"], v["email"], v["telephone"], v["mot_de_passe"])
        if ok:
            QMessageBox.information(self, "Update", msg)
            self.charger()
        else:
            QMessageBox.warning(self, "Update", msg)

    def supprimer(self):
        admin = self._admin_selectionne()
        if admin is None:
            QMessageBox.information(self, "Delete", "Selectionnez une ligne a supprimer.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete",
            "Supprimer l'administrateur #{0} ({1}) ?".format(admin["id"], admin["email"]),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        ok, msg = self.db.supprimer(admin["id"])
        if ok:
            QMessageBox.information(self, "Delete", msg)
            self.charger()
        else:
            QMessageBox.warning(self, "Delete", msg)


def main():
    app = QApplication(sys.argv)
    _style_app(app)
    fenetre = DbManagerWindow()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
