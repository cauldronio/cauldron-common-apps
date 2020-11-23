from .models import IMeetupRaw, IMeetupEnrich


def analyze_meetup_repo_obj(user, meetup_repo):
    if user.meetuptokens.count() < 1:
        return None
    raw, _ = IMeetupRaw.objects.get_or_create(user=user, repo=meetup_repo)
    enrich, _ = IMeetupEnrich.objects.get_or_create(user=user, repo=meetup_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}
