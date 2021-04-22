from .base import ExportOpenDistroBackend


class ExportStackExchange(ExportOpenDistroBackend):
    BASE_FIELDS = ['origin', 'tag', 'type', 'item_id', 'creation_date', 'author', 'author_reputation', 'score',
                   'down_vote_count', 'up_vote_count', 'answer_count', 'comment_count', 'favorite_count',
                   'question_has_accepted_answer', 'question_tags', 'view_count', 'tag', 'answer_status',
                   'is_accepted', 'question_id', 'question_tags']
    SORTINGHAT_FIELDS = []
    ES_INDEX = 'stackexchange'
