'''
This is a test module that scrapes links from websites
and compares their netloc to the netloc of the given
URL. It will print links that point to different netlocs.

Resources:
https://docs.python-guide.org/scenarios/scrape/
https://lxml.de/2.2/lxmlhtml.html
https://docs.python.org/3/library/urllib.parse.html
'''

import requests
import pprint
import sys
from urllib.parse import urlparse
from lxml import html


if len(sys.argv) != 2:
	print("Usage: link_extractor [url]")
	exit()

try:
	url = sys.argv[1]
	page = requests.get(url)
	if page.ok != True:
		print("Error reading page: ")
		print(page)
		exit()
except:
	print("Error sending request")
	exit()

html_tree = html.fromstring(page.content)
base_url = urlparse(url)

for link in html_tree.iterlinks():
	# TODO: if the given URL is 'google.com', this will print URLs
	# 	like 'maps.google.com'. This might not be our desired behavior.
	l = urlparse(link[2])
	if l.netloc != '' and l.netloc != base_url.netloc:
		pprint.pprint(l)

