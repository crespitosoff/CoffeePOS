from app.models.domain import User
from app.extensions import db
from flask_jwt_extended import create_access_token

class AuthService:
    @staticmethod
    def login(username, password):
        # 1. Buscar usuario
        user = db.session.query(User).filter(User.username == username).first()
        
        # 2. Validar existencia y contraseña utilizando el método creado en COF-25
        if not user or not user.check_password(password):
            return {"error": "Credenciales inválidas"}, 401
        
        # 3. Generar token
        access_token = create_access_token(identity=str(user.id))
        
        return {
            "access_token": access_token, 
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role.value
            }
        }, 200