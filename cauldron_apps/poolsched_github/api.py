from .models import GHInstance, GHRepo, IGHEnrich, IGHRaw


def analyze_gh_repo(user, owner, repo):
    """owner, repo"""
    # TODO: Define instance
    if user.ghtokens.count() < 1:
        return None
    instance = GHInstance.objects.get(name='GitHub')
    gh_repo, _ = GHRepo.objects.get_or_create(owner=owner, repo=repo, instance=instance)
    raw, _ = IGHRaw.objects.get_or_create(user=user, repo=gh_repo)
    enrich, _ = IGHEnrich.objects.get_or_create(user=user, repo=gh_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}


def analyze_gh_repo_obj(user, gh_repo):
    if user.ghtokens.count() < 1:
        return False
    raw, _ = IGHRaw.objects.get_or_create(user=user, repo=gh_repo)
    enrich, _ = IGHEnrich.objects.get_or_create(user=user, repo=gh_repo)
    enrich.previous.add(raw)
    return True
