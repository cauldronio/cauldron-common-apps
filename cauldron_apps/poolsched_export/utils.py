import jwt
from django.conf import settings


def get_jwt_key(user, backend_roles):
    """
    Return the JWT key for a specific user and role
    :param user:
    :param backend_roles: String or list of backend roles
    :return:
    """
    claims = {
        "user": user,
        "roles": backend_roles
    }
    return jwt.encode(claims, settings.JWT_KEY, algorithm='RS256').decode('utf-8')
