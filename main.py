#! /usr/bin/env nix-shell
#! nix-shell -i "python -u" -p "with python3Packages; [python requests urllib3 chardet beautifulsoup4]"

from collections import Counter
from pprint import pprint

import re
import sys

from bs4 import BeautifulSoup
import requests

from tools import *

PARSER = 'html.parser'
# TODO: make this a proper argument
JOB = sys.argv[1] if len(sys.argv) == 2 else 'nixos/gcc-8'
DOMAIN = 'https://hydra.nixos.org'
NUM_SAMPLES = 400


def strip_final_url(url):
    return re.search(r'([\w\d]{32}-.*)\.drv$', url)[1]


def get_builds(soup, s=requests, use_all=False):
    failed_deps = list(soup.find_all(class_='build-status', alt='Dependency failed'))
    if not use_all:
        failed_deps = sample(failed_deps, NUM_SAMPLES)
    n = len(failed_deps)
    print(f'Sending out a ton ({n}) of http requests...')
    for (i, x) in enumerate(failed_deps):
        row = x.parent.parent
        a1, a2 = row.find_all('a')
        buildid = a1.text
        pname = a2.text
        print(f'{i + 1}/{n}: {pname} ({buildid})')
        url = f'{DOMAIN}/build/{buildid}/nixlog/1/raw'
        r = s.get(url)

        yield strip_final_url(r.url)


def get_latest_eval(job, full=False, s=requests):
    print('Getting latest eval')
    soup = BeautifulSoup(s.get(f'{DOMAIN}/jobset/{job}').text, PARSER)
    url = soup.find(class_='row-link')['href']
    if full:
        url += '?full=1'
    print(url)
    return url


def main():
    full = True
    s = requests.Session()
    with s.get(get_latest_eval(JOB, full, s=s)) as f:
        print('Parsing data, please stand by...')
        soup = BeautifulSoup(f.text, PARSER)
    for xs in takeEvery(inits(get_builds(soup, s=s, use_all=not full)), 10):
        c = Counter(xs)
        pprint(c.most_common(10))


if __name__ == '__main__':
    main()
    print('Done!')
