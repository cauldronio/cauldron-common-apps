import csv
import logging
import os
import ssl
import gzip

from .. import utils

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.connection import create_ssl_context
    from elasticsearch.helpers import scan
except ImportError:
    # Only used when running the intention
    pass


logger = logging.getLogger(__name__)


class ExportOpenDistroBackend:
    """Abstract class for backends

    Base class to fetch data from Elasticsearch.

    You need to defined the fields you want to export
    for the backend.
    BASE_FIELDS are fields that can be obtained with
    and without SortingHat enabled.
    SORTINGHAT_FIELDS are fields that only can obtained
    with SortingHat enabled.
    ES_INDEX is the Elasticsearch index for the backend.
    """

    BASE_FIELDS = []
    SORTINGHAT_FIELDS = []
    ES_INDEX = None

    def __init__(self, project_role, es_host, es_port, es_scheme):
        self.project_role = project_role
        self.es_host = es_host
        self.es_port = es_port
        self.es_scheme = es_scheme

    def _init_elastic(self):
        """Get a Elasticsearch client instance initialized and authenticated"""
        jwt_key = utils.get_jwt_key(f"Project CSV", self.project_role)
        context = create_ssl_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        elastic = Elasticsearch(hosts=[self.es_host], scheme='https', port=self.es_port,
                                headers={"Authorization": f"Bearer {jwt_key}"}, ssl_context=context, timeout=5)
        return elastic

    def fetch_items(self, index=None):
        """Fetch items from Elasticsearch

        This method returns a generator of items
        from a ElasticSearch index
        """
        index = index or self.ES_INDEX
        if not index:
            raise Exception("ElasticSearch index to retrieve data not defined.")

        logger.info('Initializing OpenDistro client')
        elastic = self._init_elastic()
        es_iterator = scan(elastic,
                           query={"query": {"match_all": {}}},
                           index=index)
        for item in es_iterator:
            yield item

    def store_csv(self, file_path, compress=False, sortinghat=False):
        """Store data fetched from Elasticsearch to the file defined
        Optionally it can compress the file stored
        SortingHat fields are optional to be included in the CSV
        """
        logger.info('Create a new CSV file')
        fields = self.BASE_FIELDS
        if sortinghat:
            fields += self.SORTINGHAT_FIELDS

        opener = gzip.open if compress else open

        with opener(file_path, 'wt') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            for item in self.fetch_items():
                try:
                    writer.writerow(item['_source'])
                except Exception as e:
                    logger.error(f"Error writing row: {e}")
        logger.info('CSV file created successfully')
