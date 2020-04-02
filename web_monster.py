#!/usr/bin/env python3
'''
REFERENCES:
    https://stackoverflow.com/questions/31666584/beutifulsoup-to-extract-all-external-resources-from-html
'''

import json
import os
import hashlib
import ssl
import argparse

# URL / HTML Parsing Imports
from urllib.error import HTTPError
import urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from http.client import InvalidURL

# Threading / Concurrency Imports
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor

TOP_URLS = {}

# TODO verify that we have all the external source types we care about
HTML_ELEMENTS = {
    "a": "href",
    "script": "src",
    "iframe": "src",
    "video": "src",
    "audio": "src",
    "img": "src",
    "embed": "src",
    "object": "data"
}


# ==================================================================================================
# Takes in an input file path, where the input file is a list of newline separated top level URLs
# to crawl. Starts filling out the TOP_URLS global dictionary.

def parse_input(input_file):
    with open(input_file, 'r') as f:
        top_urls = f.readlines()

    # get rid of newlines, etc
    top_urls = [x.strip() for x in top_urls]
    for url in top_urls:
        # check that URL is not an empty string
        if url:
            top_url_dict = {"top_url": url, "external_resources": {}, "external_domains": {},
                            "internal_urls": set(), "error_urls": set()}

            TOP_URLS[url] = top_url_dict


# ==================================================================================================
# Outputs a JSON file for each website crawled

def output_to_json(output_directory):
    for url in TOP_URLS.keys():
        # make filename hash of the top url because linux doesn't like :./ in the file name
        hash_object = hashlib.sha1(str.encode(TOP_URLS[url]["top_url"]))
        hex_dig = hash_object.hexdigest()

        json_file = os.path.join(output_directory, str(hex_dig) + ".json")

        # don't output the internal URLs and error URLs as they no longer serve a purpose, plus JSON
        # doesn't like Python sets (it yells)
        del TOP_URLS[url]["internal_urls"]
        del TOP_URLS[url]["error_urls"]

        with open(json_file, 'w+') as fp:
            json.dump(TOP_URLS[url], fp)


# ==================================================================================================
# Takes in a URL string and returns the actual URL the page was located at (to handle re-directs)
# and the page source itself

def get_webpage_source(url):
    try:
        # ------------------------------------------------------------------------------------------
        # WARNING THIS MIGHT BE SOME KIND OF HORRIBLE SECURITY FLAW (gets rid of SSL error though)

        ctx_no_secure = ssl.create_default_context()
        ctx_no_secure.set_ciphers('HIGH:!DH:!aNULL')
        ctx_no_secure.check_hostname = False
        ctx_no_secure.verify_mode = ssl.CERT_NONE
        # ------------------------------------------------------------------------------------------

        page_source = urllib.request.urlopen(url, context=ctx_no_secure)
        actual_url = page_source.geturl()

    except (HTTPError, InvalidURL) as e:
        print("ERROR: " + str(e))
        print("URL: " + url)
        return None, None

    return actual_url, page_source


# ==================================================================================================
# WWW screws up our parser, so get rid of it if a URL contains it

def remove_www(url):
    return url.replace("www.", "")


# ==================================================================================================
# Required for URL matching and being able to append relative URLs

def add_trailing_slash(url):
    url_chunks = url.split('/')
    url_chunks = [i for i in url_chunks if i]
    if len(url_chunks) == 0:
        return url

    last_chunk = url_chunks[-1]
    chunks_len = len(url_chunks)

    if not url.endswith('/'):
        if ("." not in last_chunk or (url.startswith("http") and chunks_len == 2)) and len(last_chunk) > 1:
            url = url + '/'

    return url


# ==================================================================================================
# Wrapper function to remove WWW and add trailing slash, for URL uniformity

def cleanup_url(url):
    url = remove_www(url)
    return add_trailing_slash(url)


# ==================================================================================================
# Returns true if the resource URL is a valid relative URL, false otherwise

def is_valid_relative_resource(resource_url):
    # avoid traversing backwards (inefficient) or trying to parse email links (breaks stuff)
    if ".." in resource_url or "mailto" in resource_url:
        return False

    # avoid weird symbols like # that just go back to the site's homepage
    if len(resource_url) < 2:
        return False

    return not bool(urlparse(resource_url).netloc)


# ==================================================================================================
# Returns true if the resource comes from an external location, false otherwise

def is_valid_external_resource(url, resource_url):
    if "http" not in resource_url:
        return False

    # Get base URL of top level URL
    top_url_base = remove_www(urlparse(url).netloc)

    # Get base URL of resource URL
    resource_url_base = remove_www(urlparse(resource_url).netloc)

    # Check if base URLs match
    if top_url_base == resource_url_base:
        return False
    else:
        return True


# ==================================================================================================
# Appends a new external resource to the dictionary, or increases the count by one if the resource
# has been seen before

def append_external_resource(top_dict, resource_url, resource_type):
    resource_dict = top_dict["external_resources"].get(resource_url, None)

    # case where we've seen this resource before
    if resource_dict is not None:
        top_dict["external_resources"][resource_url]["count"] = top_dict["external_resources"][
                                                                    resource_url]["count"] + 1

    # case where we have not seen this resource before
    else:
        resource_dict = {"count": 1, "type": resource_type}
        top_dict["external_resources"][resource_url] = resource_dict


# ==================================================================================================
def append_external_domain(top_dict, resource_url, resource_type):
    domain = urlparse(resource_url).netloc
    remove_substrings = ["https://", "http://"]

    for sub in remove_substrings:
        domain = domain.replace(sub, "")

    domain_dict = top_dict["external_domains"].get(domain, None)

    # case where we've seen this domain before
    if domain_dict is not None:
        top_dict["external_domains"][domain]["total"] += 1
        top_dict["external_domains"][domain][resource_type] += 1

    else:
        domain_count_dict = {"total": 1}
        for tagType in HTML_ELEMENTS.keys():
            domain_count_dict[tagType] = 0

        domain_count_dict[resource_type] = 1
        top_dict["external_domains"][domain] = domain_count_dict


# ==================================================================================================
def dont_traverse_higher_urls(resource_url, top_dict):
    top_url = top_dict["top_url"]

    # ignore difference between http and https
    base_urls = set()
    base_urls.add(top_url)
    if top_url.startswith("https:"):
        base_urls.add(top_url.replace("https:", "http:"))
    elif top_url.startswith("http:"):
        base_urls.add(top_url.replace("http:", "https:"))

    if resource_url.startswith(tuple(base_urls)):
        analyze_url(resource_url, top_dict)


# ==================================================================================================
# Finds all URLs of a certain "tag" type in the HTML document. Determines whether resource is
# internal or external and commences further processing accordingly

def parse_resources(tag, attr, soup, top_dict, current_url):
    for t in soup.findAll(tag):
        try:
            resource_url = cleanup_url(t[attr])
            # --------------------------------------------------------------------------------------
            # External Resource (add to dictionary of external URLs)

            if is_valid_external_resource(top_dict["top_url"], resource_url):
                append_external_resource(top_dict, resource_url, tag)
                append_external_domain(top_dict, resource_url, tag)
            # --------------------------------------------------------------------------------------
            # Internal Link (parse down this page)

            elif tag == "a":
                # Full URL
                if "http" in resource_url:
                    dont_traverse_higher_urls(resource_url, top_dict)

                # Partial URL
                if is_valid_relative_resource(resource_url):
                    # handle absolute path by combining with top_url
                    if resource_url[0] == '/':
                        resource_url = top_dict["top_url"] + resource_url[1:]
                        analyze_url(resource_url, top_dict)

                    # handle relative path by combining with valid current_url
                    elif current_url.endswith("/"):
                        analyze_url(current_url + resource_url, top_dict)

            # --------------------------------------------------------------------------------------
        except KeyError:
            pass


# ==================================================================================================
def get_links(soup, top_dict, current_url):
    for tagType in HTML_ELEMENTS.keys():
        parse_resources(tagType, HTML_ELEMENTS[tagType], soup, top_dict, current_url)


# ==================================================================================================
def is_new_valid_internal_url(url, top_dict):
    # don't parse things we've already seen before
    if url not in top_dict["internal_urls"] and url not in top_dict["error_urls"]:
        # don't parse huge documents that aren't even webpages
        # TODO may have to add more extensions to this pending testing
        ignore_extensions = (".pdf", ".pptx", ".xlsx", ".ics")
        if not url.endswith(ignore_extensions):
            return True

    else:
        return False


# ==================================================================================================
def analyze_url(url, top_dict):
    url = cleanup_url(url)

    if is_new_valid_internal_url(url, top_dict):
        actual_url, page_source = get_webpage_source(url)

        if actual_url and page_source:
            # --------------------------------------------------------------------------------------
            actual_url = cleanup_url(actual_url)
            # Handle rare case where URL re-directed
            # TODO probably split this out into handle_redirect function and add link to external
            #  dict if it is actually external
            if url != actual_url:
                if not is_new_valid_internal_url(actual_url, top_dict) or \
                        is_valid_external_resource(actual_url, top_dict["top_url"]):
                    return

                url = actual_url
            # --------------------------------------------------------------------------------------
            print("New Internal URL: " + url)
            top_dict["internal_urls"].add(url)
            soup = BeautifulSoup(page_source, "lxml")
            get_links(soup, top_dict, url)
        else:
            top_dict["error_urls"].add(url)

    return "WEBSITE " + url + " THREAD DONE"


# ==================================================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl webpages for 3rd party links.")
    parser.add_argument("-i", dest="input_file", type=str, help="File containing list of top-level domains to scan", default="./input.txt")
    parser.add_argument("-o", dest="output_dir", type=str, help="Directory to output JSON results", default="./data/")
    args = parser.parse_args()

    parse_input(args.input_file)

    threads = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for top_url in TOP_URLS.keys():
            print("ANALYZING WEBSITE: " + top_url)
            threads.append(executor.submit(analyze_url, top_url, TOP_URLS[top_url]))

    # wait for threads to finish before outputting all JSON files / ending the program
    for f in futures.as_completed(threads):
        print(f.result())

    # TODO have this function create one website's JSON file and thread this as well
    output_to_json(args.output_dir)
