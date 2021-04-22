from .base import ExportOpenDistroBackend


class ExportMeetup(ExportOpenDistroBackend):
    BASE_FIELDS = ['id', 'group_id', 'type', 'event_url', 'like_count', 'meetup_created', 'meetup_duration',
                   'meetup_status', 'meetup_time', 'meetup_updated', 'meetup_yes_rsvp_count', 'member_is_host',
                   'num_comments', 'num_rsvps', 'rsvps_limit', 'rsvps_response', 'time_date', 'venue_address_1',
                   'venue_city', 'venue_country', 'venue_name', 'group_members', 'group_name', 'group_topics',
                   'author_id', 'author_uuid']
    SORTINGHAT_FIELDS = ['author_user_name', 'member_id', 'member_name']
    ES_INDEX = 'meetup'
