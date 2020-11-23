import logging


class Config:
    def __init__(self, *args, **kwargs):
        logging.error('Fake Config created')

    def set_param(self, *args, **kwargs):
        logging.error('Fake Config.set_param() called')


class TaskProjects:
    def __init__(self, *args, **kwargs):
        logging.error('Fake TaskProjects created')

    def execute(self, *args, **kwargs):
        logging.error('Fake TaskProjects.execute() called')


class TaskRawDataCollection:
    def __init__(self, *args, **kwargs):
        logging.error('Fake TaskRawDataCollection created')

    def execute(self, *args, **kwargs):
        logging.error('Fake TaskRawDataCollection.execute() called')


class TaskEnrich:
    def __init__(self, *args, **kwargs):
        logging.error('Fake TaskEnrich created')

    def execute(self, *args, **kwargs):
        logging.error('Fake TaskEnrich.execute() called')
