import os
import codecs
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
readme_md = os.path.join(here, 'README.md')
with codecs.open(readme_md, encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="cauldron_apps",
    version="0.2",
    description="Django apps used in Cauldron.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='GPLv3',
    author='cauldron.io',
    author_email='contact@cauldron.io',
    url='https://gitlab.com/cauldronio/cauldron-common-apps',
    packages=find_packages(exclude=('project', '*tests')),
    include_package_data=True,
    keywords="django apps cauldron",
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.0',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Database :: Database Engines/Servers',
    ],
    install_requires=[
        "django>=3.0",
        "mysqlclient",
        "sqlalchemy",
        "django-model-utils>=4.0",
        "PyGithub==1.54.1",
        "cryptography>=3.2",
        "pyjwt<2",
        "python-dateutil>=2.8.1,<3",
        "python-gitlab",
        "elasticsearch",
        "elasticsearch_dsl",
        "tweepy",
    ]
)
