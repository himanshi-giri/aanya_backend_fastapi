from flask_jwt_extended import create_access_token
from flask_bcrypt import check_password_hash
from models import find_user

def authenticate_user(email, password):
    """Verify user credentials and return a JWT token if valid."""
    user = find_user(email)
    if user and check_password_hash(user["password"], password):
        return create_access_token(identity=email)
    return None
