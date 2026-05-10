# app/services/user_service.py
# COF-31: Backend – Servicio de gestión de usuarios
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.domain import User, UserRole, UserStatus


class UserService:
    """Encapsula la lógica de negocio para la gestión de usuarios."""

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @staticmethod
    def get_all_users(active_only: bool = True) -> List[User]:
        """Retorna todos los usuarios, filtrando por estado activo por defecto."""
        query = db.session.query(User)
        if active_only:
            query = query.filter(User.status == UserStatus.ACTIVE)
        return query.order_by(User.username.asc()).all()

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        """Retorna un usuario por su UUID o None si no existe."""
        return db.session.get(User, user_id)

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Retorna un usuario por su nombre de usuario."""
        return (
            db.session.query(User)
            .filter(User.username == username)
            .first()
        )

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    @staticmethod
    def create_user(data: dict) -> User:
        """
        Crea un nuevo usuario.

        Campos esperados en *data*:
            username (str, obligatorio)
            password (str, obligatorio – texto plano, se hashea aquí)
            role     (str | UserRole, obligatorio)
            first_name, last_name, phone, email, avatar_url (opcionales)
        """
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username:
            raise ValueError("El nombre de usuario es obligatorio.")
        if not password:
            raise ValueError("La contraseña es obligatoria.")

        role_raw = data.get("role")
        if role_raw is None:
            raise ValueError("El rol del usuario es obligatorio.")
        try:
            role = UserRole(role_raw) if isinstance(role_raw, str) else role_raw
        except ValueError:
            raise ValueError(f"Rol inválido: '{role_raw}'.")

        # Verificar unicidad de username
        if UserService.get_user_by_username(username):
            raise ValueError(f"Ya existe un usuario con el nombre '{username}'.")

        try:
            user = User(
                username=username,
                role=role,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                phone=data.get("phone"),
                email=data.get("email"),
                avatar_url=data.get("avatar_url"),
                status=UserStatus.ACTIVE,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al crear usuario: {e}") from e

    @staticmethod
    def update_user(user_id: str, data: dict) -> User:
        """
        Actualiza los campos permitidos de un usuario existente.

        No permite cambiar la contraseña aquí; usar *change_password* para eso.
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado.")

        updatable_fields = [
            "first_name", "last_name", "phone", "email", "avatar_url",
        ]
        try:
            for field in updatable_fields:
                if field in data:
                    setattr(user, field, data[field])

            # Actualizar username con verificación de unicidad
            if "username" in data:
                new_username = data["username"].strip()
                existing = UserService.get_user_by_username(new_username)
                if existing and str(existing.id) != str(user_id):
                    raise ValueError(
                        f"Ya existe un usuario con el nombre '{new_username}'."
                    )
                user.username = new_username

            # Actualizar rol
            if "role" in data:
                role_raw = data["role"]
                user.role = (
                    UserRole(role_raw) if isinstance(role_raw, str) else role_raw
                )

            # Actualizar status
            if "status" in data:
                status_raw = data["status"]
                user.status = (
                    UserStatus(status_raw)
                    if isinstance(status_raw, str)
                    else status_raw
                )

            db.session.commit()
            return user
        except (SQLAlchemyError, ValueError):
            db.session.rollback()
            raise

    @staticmethod
    def delete_user(user_id: str) -> bool:
        """
        Borrado lógico: cambia el status del usuario a INACTIVE.
        No elimina el registro físicamente.
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado.")

        try:
            user.status = UserStatus.INACTIVE
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al desactivar usuario: {e}") from e

    @staticmethod
    def change_password(user_id: str, new_password: str) -> bool:
        """Cambia la contraseña de un usuario validando que no esté vacía."""
        if not new_password or not new_password.strip():
            raise ValueError("La nueva contraseña no puede estar vacía.")

        user = UserService.get_user_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado.")

        try:
            user.set_password(new_password.strip())
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            raise RuntimeError(f"Error al cambiar contraseña: {e}") from e
