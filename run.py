from app import db, create_app
from app.models.domain import User
app = create_app()

if __name__ == '__main__':
    user_to_delete = User.query.filter_by(username='admin').first()
    if user_to_delete:
        db.session.delete(user_to_delete)
        db.session.commit()
        print("Usuario 'admin' manual eliminado de la base de datos.")
    app.run(debug=True, port=5000)