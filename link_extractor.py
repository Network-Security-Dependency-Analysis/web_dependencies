'''
Program to scrape websites for hrefs to other sites.

Resources:
https://docs.python-guide.org/scenarios/scrape/
https://lxml.de/2.2/lxmlhtml.html
https://docs.python.org/3/library/urllib.parse.html
https://anytree.readthedocs.io/en/latest/index.html
https://docs.python.org/3/howto/argparse.html 
'''

import requests
import pprint
import sys
from urllib.parse import urlparse
from lxml import html
import argparse
from anytree import Node, RenderTree, search, LevelOrderIter

def main(args):
	# The initial baseURL is created with urlparse, and needs to be prefixed with the scheme
	if not args.url.startswith("http"):
		args.url = "http://" + args.url
	baseURL = urlparse(args.url).netloc
	if baseURL.startswith("www."):
		# TODO: some sites use www. and some don't, leading to duplicates.
		#	I've removed www. for now to remove duplicates, but there is
		#	probably a better way to do this in the future
		baseURL = baseURL[4:]
	root = Node(baseURL)

	# Traverse tree level-by-level, at each step creating the next level
	#	of children until we reach the desired depth
	for n in LevelOrderIter(root, maxlevel=args.recurse):
		addChildren(n)

	# Print nicely to the console
	for pre, fill, node in RenderTree(root):
		print("%s%s" % (pre, node.name))


def addChildren(node):
	'''
	Given a node (where node.name is a base URL), scrape all 
	links from the page at that URL and add the unique links 
	as children.
	'''
	page = getPage(node.name)

	if page == None:
		# Can happen if we try to access a non-existent URL
		return

	for link in page.iterlinks():
		# Get URL of the HTML link element
		l = urlparse(link[2])
		if l.netloc.startswith("www."):
			# TODO: see note in main() about www.
			netloc = l.netloc[4:]
		else:
			netloc = l.netloc

		# If the link is not to the same base URL and not already in the 
		#	children of the tree, add it to the tree.
		# TODO: Maybe instead of skipping duplicates we can count the number 
		#	of times a link appears on a page, and weight certain nodes as 
		#	"more important" than others.
		if netloc != '' and netloc != node.name:
			find = search.findall(node, filter_=lambda n: n.name == netloc)
			if find == ():
				# Setting the parent here automatically updates the tree!
				Node(netloc, parent=node)


def getPage(url):
	'''
	Given a URL, use the requests library + lxml/html to 
	return an html_tree object.
	'''
	try:
		if not url.startswith("http"):
			# requests.get() needs the scheme--default to http
			url = "http://" + url
		page = requests.get(url)
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
	parser.add_argument("-r", type=int, dest="recurse", default=1, help="# of recursive scans to perform")
	parser.add_argument("url", type=str, help="The URL to scan")
	args = parser.parse_args()
	main(args)