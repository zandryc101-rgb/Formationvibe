#!/usr/bin/env python3
"""Couche SQLite pour les comptes administrateurs (maximum 2)."""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adminpro.db")
MAX_ADMINS = 2
_PBKDF2_ITERS = 120_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TEL_RE = re.compile(r"^\+?[0-9]{8,15}$")


def hasher_mot_de_passe(mot_de_passe: str, sel: Optional[str] = None) -> str:
    if sel is None:
        sel = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel.encode("utf-8"),
        _PBKDF2_ITERS,
    )
    return "{0}${1}".format(sel, digest.hex())


def verifier_mot_de_passe(mot_de_passe: str, stocke: str) -> bool:
    try:
        sel, _hex = stocke.split("$", 1)
    except ValueError:
        return False
    attendu = hasher_mot_de_passe(mot_de_passe, sel)
    return secrets.compare_digest(attendu, stocke)


def email_valide(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip().lower()))


def telephone_valide(telephone: str) -> bool:
    nettoye = telephone.strip().replace(" ", "").replace("-", "")
    return bool(_TEL_RE.match(nettoye))


class AdminDB:
    def __init__(self, chemin: str = DB_PATH) -> None:
        self.chemin = chemin
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.chemin)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    telephone TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def chemin_fichier(self) -> str:
        return self.chemin

    def tables(self) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            return [str(r[0]) for r in rows]

    def compter(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM admins").fetchone()
            return int(row["n"]) if row else 0

    def places_restantes(self) -> int:
        return max(0, MAX_ADMINS - self.compter())

    def inscription_autorisee(self) -> bool:
        return self.compter() < MAX_ADMINS

    def lister(self) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, email, telephone, created_at, updated_at FROM admins ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    def par_id(self, admin_id: int) -> Optional[Dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, email, telephone, created_at, updated_at FROM admins WHERE id = ?",
                (admin_id,),
            ).fetchone()
            return dict(row) if row else None

    def par_email(self, email: str) -> Optional[Dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM admins WHERE email = ? COLLATE NOCASE",
                (email.strip(),),
            ).fetchone()
            return dict(row) if row else None

    def par_telephone(self, telephone: str) -> Optional[Dict]:
        tel = telephone.strip().replace(" ", "").replace("-", "")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM admins WHERE telephone = ?",
                (tel,),
            ).fetchone()
            return dict(row) if row else None

    def creer(self, email: str, mot_de_passe: str, telephone: str) -> Tuple[bool, str, Optional[Dict]]:
        if not self.inscription_autorisee():
            return False, "Nombre maximum d'administrateurs atteint (2).", None
        email_n = email.strip().lower()
        tel = telephone.strip().replace(" ", "").replace("-", "")
        if not email_valide(email_n):
            return False, "Adresse email invalide.", None
        if not telephone_valide(tel):
            return False, "Numero de telephone invalide (8 a 15 chiffres).", None
        if len(mot_de_passe) < 6:
            return False, "Le mot de passe doit contenir au moins 6 caracteres.", None
        maintenant = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO admins (email, telephone, password_hash, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (email_n, tel, hasher_mot_de_passe(mot_de_passe), maintenant, maintenant),
                )
                admin_id = int(cur.lastrowid)
        except sqlite3.IntegrityError:
            return False, "Cet email ou ce numero de telephone est deja utilise.", None
        return True, "Compte administrateur cree.", self.par_id(admin_id)

    def modifier(
        self,
        admin_id: int,
        email: str,
        telephone: str,
        mot_de_passe: Optional[str] = None,
    ) -> Tuple[bool, str]:
        email_n = email.strip().lower()
        tel = telephone.strip().replace(" ", "").replace("-", "")
        if not email_valide(email_n):
            return False, "Adresse email invalide."
        if not telephone_valide(tel):
            return False, "Numero de telephone invalide (8 a 15 chiffres)."
        if mot_de_passe is not None and mot_de_passe != "" and len(mot_de_passe) < 6:
            return False, "Le mot de passe doit contenir au moins 6 caracteres."
        maintenant = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._connect() as conn:
                if mot_de_passe:
                    conn.execute(
                        """
                        UPDATE admins
                        SET email = ?, telephone = ?, password_hash = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (email_n, tel, hasher_mot_de_passe(mot_de_passe), maintenant, admin_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE admins
                        SET email = ?, telephone = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (email_n, tel, maintenant, admin_id),
                    )
                if conn.total_changes == 0:
                    return False, "Administrateur introuvable."
        except sqlite3.IntegrityError:
            return False, "Cet email ou ce numero de telephone est deja utilise."
        return True, "Compte mis a jour."

    def supprimer(self, admin_id: int) -> Tuple[bool, str]:
        with self._connect() as conn:
            conn.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
            if conn.total_changes == 0:
                return False, "Administrateur introuvable."
        return True, "Administrateur supprime."

    def authentifier(self, email: str, mot_de_passe: str) -> Optional[Dict]:
        admin = self.par_email(email)
        if admin is None:
            return None
        if not verifier_mot_de_passe(mot_de_passe, admin["password_hash"]):
            return None
        return {
            "id": admin["id"],
            "email": admin["email"],
            "telephone": admin["telephone"],
        }

    def recuperer_mot_de_passe(self, canal: str, identifiant: str) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Genere un nouveau mot de passe (les anciens sont hashes, non recuperables),
        l'enregistre, et renvoie la destination pour l'envoi simule.
        """
        canal_n = canal.strip().lower()
        ident = identifiant.strip()
        if canal_n == "email":
            admin = self.par_email(ident)
            destination = admin["email"] if admin else None
        elif canal_n in ("telephone", "sms", "tel"):
            admin = self.par_telephone(ident)
            destination = admin["telephone"] if admin else None
        else:
            return False, "Choisissez l'email ou le telephone.", None, None

        if admin is None:
            return False, "Aucun compte ne correspond a ces informations.", None, None

        nouveau = secrets.token_urlsafe(8)
        ok, msg = self.modifier(admin["id"], admin["email"], admin["telephone"], nouveau)
        if not ok:
            return False, msg, None, None
        return True, "Un nouveau mot de passe a ete envoye.", destination, nouveau
