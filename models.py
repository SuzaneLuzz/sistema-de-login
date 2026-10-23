"""Modelos do banco de dados."""

from datetime import datetime

from flask import url_for
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), default="")
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # Contas criadas só com Google/GitHub não têm senha
    password_hash = db.Column(db.String(256), nullable=True)

    # IDs das contas externas vinculadas
    google_id = db.Column(db.String(64), unique=True, nullable=True)
    github_id = db.Column(db.String(64), unique=True, nullable=True)

    # Caminho de um avatar local (ex.: "avatars/avatar3.svg") ou URL externa
    avatar = db.Column(db.String(300), nullable=True)

    # Proteção contra força bruta
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self):
        return (self.first_name[:1] + (self.last_name or "")[:1]).upper()

    @property
    def avatar_url(self):
        if not self.avatar:
            return None
        if self.avatar.startswith("http"):
            return self.avatar
        return url_for("static", filename=self.avatar)

    @property
    def login_methods(self):
        methods = []
        if self.password_hash:
            methods.append("E-mail e senha")
        if self.google_id:
            methods.append("Google")
        if self.github_id:
            methods.append("GitHub")
        return methods
