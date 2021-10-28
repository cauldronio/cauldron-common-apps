import re
import argparse
import requests
import logging


GITHUB_REPO_REGEX = '^(?:git\+)?(?:https?:\/\/)?github\.com\/([a-zA-Z0-9](?:[a-zA-Z0-9]|-[a-zA-Z0-9]){1,38})\/([a-zA-Z0-9\.\-\_]{1,100})(?:.+)?'
GITLAB_REPO_REGEX = '^(?:git\+)?(?:https?:\/\/)?gitlab.com\/([a-zA-Z0-9_\.][a-zA-Z0-9_\-\.]{1,200}[a-zA-Z0-9_\-]|[a-zA-Z0-9_])\/((?:[a-zA-Z0-9_\.][a-zA-Z0-9_\-\.]*(?:\/)?)+)(?:.+)?'
PYPI_PACKAGE_REGEX = '^(?:https?:\/\/)?pypi.org\/project\/([a-zA-Z0-9\.\-\_]+)(?:.+)?'
NPM_PACKAGE_REGEX = '^(?:https?:\/\/)?npmjs.com\/package\/([a-zA-Z0-9\.\-\_]+)(?:.+)?'

logger = logging.getLogger(__name__)


def fetch(url):
    res = requests.get(url)
    res.raise_for_status()
    return res.json()


def guess_datasource(repository):
    """
    Check first if repository is a pip or npm package,
    then if it is a GitHub or GitLab repository
    """
    logger.info(f'Guessing {repository} datasource...')
    pypi_regex = re.match(PYPI_PACKAGE_REGEX, repository)
    if pypi_regex:
        logger.info(f"Pypi({pypi_regex.groups()[0]})")
        data = fetch(f"https://pypi.org/pypi/{pypi_regex.groups()[0]}/json")
        try:
            repository = data['info']['project_urls']['Source Code']
            logger.info(repository)
        except KeyError:
            logger.error('No repository found for pip package')
            return None

    npm_regex = re.match(NPM_PACKAGE_REGEX, repository)
    if npm_regex:
        logger.info(f"npm({npm_regex.groups()[0]})")
        data = fetch(f"https://api.npms.io/v2/package/{npm_regex.groups()[0]}")
        try:
            repository = data['metadata']['repository']['url']
            logger.info(repository)
        except KeyError:
            logger.error('No repository found for npm package')
            return None

    github_regex = re.match(GITHUB_REPO_REGEX, repository)
    if github_regex:
        logger.info(f"GitHub({github_regex.groups()[0]}/{github_regex.groups()[1]})")
        return {'datasource': 'github',
                'repository': f'https://github.com/{github_regex.groups()[0]}/{github_regex.groups()[1]}'
                }

    gitlab_regex = re.match(GITLAB_REPO_REGEX, repository)
    if gitlab_regex:
        logger.info(f"GitLab({gitlab_regex.groups()[0]}/{gitlab_regex.groups()[1]})")
        return {'datasource': 'gitlab',
                'repository': f'https://gitlab.com/{gitlab_regex.groups()[0]}/{gitlab_regex.groups()[1]}'
                }


def split_value(line):
    split = line.split(':', 1)
    if len(split) != 2:
        raise Exception('Empty value: %s' % line)
    return split[1].strip()


def packages_download_location(filename):
    with open(filename, 'r') as f:
        data = f.read()

    package = None
    for line in data.splitlines():
        if line.startswith('PackageName'):
            if package:
                yield package
            package = {
                'PackageName': split_value(line),
                'PackageHomePage': '',
                'PackageDownloadLocation': ''
            }
        if line.startswith('PackageHomePage'):
            if not package:
                raise Exception('No PackageName')
            package['PackageHomePage'] = split_value(line)
        if line.startswith('PackageDownloadLocation'):
            if not package:
                raise Exception('No PackageName')
            package['PackageDownloadLocation'] = split_value(line)
    if package:
        yield package


def source_repositories(filename):
    urls = []
    for location in packages_download_location(filename):
        datasource = guess_datasource(location['PackageDownloadLocation'])
        if not datasource:
            # Some packages include the repository in PackageHomePage
            datasource = guess_datasource(location['PackageHomePage'])
        if datasource:
            location['datasource'] = datasource['datasource']
            location['repository'] = datasource['repository']
        else:
            location['datasource'] = None
            location['repository'] = None
        urls.append(location)
    return urls


def setup_cmd_parser():
    """Parse input data"""

    parser = argparse.ArgumentParser(description='Get the dependencies in a SPDX.')
    parser.add_argument('filename',
                        help='SPDX file to parse')
    return parser


if __name__ == '__main__':
    parser = setup_cmd_parser()
    args = parser.parse_args()
    urls = source_repositories(args.filename)
    for url in urls:
        print(url)
