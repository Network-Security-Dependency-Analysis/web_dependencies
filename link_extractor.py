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
import argparse
from anytree import Node, RenderTree

def main(args):
	# Dictionary of levels of recursion mapped to URLs for that level
	# currentRecurse = 0
	baseURL = urlparse(args.url).netloc
	root = Node(baseURL)

	addChildren(root)

	for pre, fill, node in RenderTree(root):
		print("%s%s" % (pre, node.name))


def addChildren(node):
	page = getPage(node.name)

	for link in page.iterlinks():
		# Get URL of the HTML link element
		l = urlparse(link[2])

		# Add the URL to the dict iff it is not empty or part of the base URL
		if l.netloc != '' and l.netloc != node.name:
			Node(l.netloc, parent=node)


def getPage(url):
	try:
		page = requests.get(args.url)
		if page.ok != True:
			print("Error reading page: ", file=sys.stderr)
			print(page, file=sys.stderr)
			return None
	except:
		print("Error sending request", file=sys.stderr)
		return None

	html_tree = html.fromstring(page.content)
	return html_tree


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Crawl webpages for 3rd party links.")
	# parser.add_argument("-r", dest="recurse")
	parser.add_argument("url", type=str, help="The URL to scan")
	args = parser.parse_args()
	main(args)