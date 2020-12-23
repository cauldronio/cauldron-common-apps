from .models import GLInstance, GLRepo, IGLRaw, IGLEnrich


def analyze_gl_repo(user, owner, repo, instance):
    """owner, repo"""
    if user.gltokens.filter(instance=instance).count() < 1:
        return None
    gl_repo, _ = GLRepo.objects.get_or_create(owner=owner, repo=repo, instance=instance)
    raw, _ = IGLRaw.objects.get_or_create(user=user, repo=gl_repo)
    enrich, _ = IGLEnrich.objects.get_or_create(user=user, repo=gl_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}


def analyze_gl_repo_obj(user, gl_repo):
    if user.gltokens.filter(instance=gl_repo.instance).count() < 1:
        return False
    raw, _ = IGLRaw.objects.get_or_create(user=user, repo=gl_repo)
    enrich, _ = IGLEnrich.objects.get_or_create(user=user, repo=gl_repo)
    enrich.previous.add(raw)
    return True
