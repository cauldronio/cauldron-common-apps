from .models import GLInstance, GLRepo, IGLRaw, IGLEnrich


def analyze_gl_repo(user, owner, repo):
    """owner, repo"""
    # TODO: Define instance
    if user.gltokens.count() < 1:
        return None
    instance = GLInstance.objects.get(name='GitLab')
    gl_repo, _ = GLRepo.objects.get_or_create(owner=owner, repo=repo, instance=instance)
    raw, _ = IGLRaw.objects.get_or_create(user=user, repo=gl_repo)
    enrich, _ = IGLEnrich.objects.get_or_create(user=user, repo=gl_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}


def analyze_gl_repo_obj(user, gl_repo):
    if user.gltokens.count() < 1:
        return None
    raw, _ = IGLRaw.objects.get_or_create(user=user, repo=gl_repo)
    enrich, _ = IGLEnrich.objects.get_or_create(user=user, repo=gl_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}
