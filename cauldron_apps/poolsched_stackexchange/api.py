from .models import IStackExchangeRaw, IStackExchangeEnrich


def analyze_stack_repo_obj(user, repo):
    if user.stackexchangetokens.count() < 1:
        return False
    raw, _ = IStackExchangeRaw.objects.get_or_create(user=user, question_tag=repo)
    enrich, _ = IStackExchangeEnrich.objects.get_or_create(user=user, question_tag=repo)
    enrich.previous.add(raw)
    return True
