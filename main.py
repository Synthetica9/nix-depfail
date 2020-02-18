#! /usr/bin/env nix-shell
#! nix-shell -i "python -u" -p "with python3Packages; [python requests urllib3 chardet beautifulsoup4 brotlipy]"

# TODO: statusbar lib
# TODO: a lot of builds are timing out (https://hydra.nixos.org/build/74387262)

from collections import Counter
from pprint import pprint

import re
import sys

from bs4 import BeautifulSoup
import requests
from warnings import warn
import brotli

from tools import *

PARSER = 'html.parser'
# TODO: make this a proper argument
JOB = sys.argv[1] if len(sys.argv) == 2 else 'nixpkgs/gcc8'

DOMAIN = 'https://hydra.nixos.org'
NUM_SAMPLES = 1000


def strip_final_url(url):
    return re.search(r'([\w\d]{32}-.*)\.drv$', url)[1]


def build_log(buildid: int, s=requests, domain=DOMAIN):
    url = f'{DOMAIN}/build/{buildid}/nixlog/1/raw'
    return s.get(url)


def get_failed_deps(soup, s=requests, use_all=False):
    failed_deps = list(get_builds_by_status(soup, status='Dependency failed'))
    if not use_all:
        failed_deps = sample(failed_deps, NUM_SAMPLES)
    n = len(failed_deps)
    print(f'Sending out a ton ({n}) of http requests...')
    for (i, (buildid, pname)) in enumerate(failed_deps):
        print(f'{i + 1}/{n}:\t{pname} ({buildid})')
        r = build_log(buildid, s=s)
        yield strip_final_url(r.url)


def get_werrors(log_text):
    return {m[0] for m in re.finditer(r"\[-Werror=([\w-]+)\]", log_text)}


def get_failed_builds(soup, s=requests):
    print("|   | Package | WError | Log link |")
    print("| - | ------- | ------ | -------- |")
    failed_builds = get_builds_by_status(soup, status='Failed')
    c = Counter()
    for (buildid, pname) in failed_builds:
        r = build_log(buildid, s=s)
        if r.headers.get('Content-Encoding') == 'br':
            raw = brotli.decompress(r.content)
            text = str(raw, 'utf-8')
        else:
            text = r.text
        werrors = get_werrors(text)
        if werrors:
            print(f'| [ ] |  {pname} | {werrors} | [log]({r.url})')

        c[bool(werrors)] += 1
    pprint(c)


def get_build_status(buildid, s=requests):
    url = f'{DOMAIN}/build/{buildid}'
    r = s.get(url)
    soup = BeautifulSoup(r.text, PARSER)
    status = soup.find(text='Status:')
    row = status.parent.parent
    status = row.td.text.strip()
    print(row)
    return status


def get_status_stats(soup):
    return Counter(x['alt'] for x in soup.find_all(class_='build-status'))


def get_builds_by_status(soup, status):
    # TODO: use enum for status, something about typos
    xs = soup.find_all(class_='build-status', alt=status)
    has_results = False

    for x in xs:
        has_results = True
        row = x.parent.parent
        a1, a2 = row.find_all('a')
        buildid = int(a1.text)
        pname = a2.text
        yield (buildid, pname)

    if not has_results:
        warn(f'No results for {repr(status)}, is that a valid status?')


def get_latest_eval(job, full=False, s=requests):
    soup = BeautifulSoup(s.get(f'{DOMAIN}/jobset/{job}').text, PARSER)
    url = soup.find(class_='row-link')['href']
    if full:
        url += '?full=1'
    return url


def main():
    full = True
    s = requests.Session()
    with s.get(get_latest_eval(JOB, full, s=s)) as f:
        print('Parsing data, please stand by...')
        soup = BeautifulSoup(f.text, PARSER)
    for xs in takeEvery(inits(get_failed_deps(soup, s=s, use_all=not full)), 10):
        c = Counter(xs)
        pprint(c.most_common(10))
    c = Counter(xs)
    pprint(c.most_common(10))


if __name__ == '__main__':
    main()
    # print(get_build_status(74387262))
    print('Done!')
