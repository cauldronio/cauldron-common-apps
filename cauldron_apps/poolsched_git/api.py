from .models import GitRepo, IGitRaw, IGitEnrich


def analyze_git_repo(user, url):
    """owner, repo, instance"""
    git_repo, _ = GitRepo.objects.get_or_create(url=url)
    raw, _ = IGitRaw.objects.get_or_create(user=user, repo=git_repo)
    enrich, _ = IGitEnrich.objects.get_or_create(user=user, repo=git_repo)
    enrich.previous.add(raw)
    return git_repo


def analyze_git_repo_obj(user, git_repo):
    """owner, repo, instance"""
    raw, _ = IGitRaw.objects.get_or_create(user=user, repo=git_repo)
    enrich, _ = IGitEnrich.objects.get_or_create(user=user, repo=git_repo)
    enrich.previous.add(raw)
    return True
