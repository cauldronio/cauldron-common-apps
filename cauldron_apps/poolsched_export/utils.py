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


def get_available_dashboards(project, kbn_url):
    output = []
    token = get_jwt_key('Dashboards', project.projectrole.backend_role)
    import requests
    with requests.Session() as client:
        client.get(f"{kbn_url}/", params={'jwtToken': token})
        res = client.get(f"{kbn_url}/api/saved_objects/_find", params={'default_search_operator': 'AND',
                                                                       'page': 1,
                                                                       'per_page': 1000,
                                                                       'type': 'dashboard'})
        if res.ok:
            data = res.json()
            for dashboard in data['saved_objects']:
                output.append({
                    'name': dashboard['attributes']['title'],
                    'id': dashboard['id']
                })

    return output
