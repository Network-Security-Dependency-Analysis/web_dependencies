#!/usr/bin/env python3
'''
REFERENCES:
    https://stackoverflow.com/questions/31666584/beutifulsoup-to-extract-all-external-resources-from-html
'''
from concurrent import futures
from http.client import InvalidURL
from urllib.error import HTTPError

from bs4 import BeautifulSoup
import urllib.request
from urllib.parse import urlparse
import json
import os
import hashlib
import ssl
from concurrent.futures import ThreadPoolExecutor

TOP_URLS = {}


# ==================================================================================================
# Takes in an input file path, where the input file is a list of newline separated top level URLs
# to crawl. Starts filling out the TOP_URLS global dictionary.

def parse_input(input_file):
    with open(input_file, 'r') as f:
        top_urls = f.readlines()

    top_urls = [x.strip() for x in top_urls]
    for url in top_urls:
        if url:
            top_url_dict = {"top_url": url, "external_urls": {}, "internal_urls": set(),
                            "error_urls": set()}

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
# Takes in a URL string and outputs a Beautiful Soup object for further parsing

def get_webpage_source(url):
    try:
        # WARNING THIS MIGHT BE SOME KIND OF HORRIBLE SECURITY FLAW
        ctx_no_secure = ssl.create_default_context()
        ctx_no_secure.set_ciphers('HIGH:!DH:!aNULL')
        ctx_no_secure.check_hostname = False
        ctx_no_secure.verify_mode = ssl.CERT_NONE

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
    last_chunk = url_chunks[-1]
    chunks_len = len(url_chunks)

    if not url.endswith('/'):
        if ("." not in last_chunk or chunks_len == 3) and len(last_chunk) > 1:
            url = url + '/'

    return url


# ==================================================================================================
# Returns true if the resource URL is a relative URL, false if its an absolute URL

def is_valid_relative_resource(resource_url):
    if "http" in resource_url or ".." in resource_url or "mailto" in resource_url:
        return False

    if len(resource_url) < 2:
        return False

    return not bool(urlparse(resource_url).netloc)


# ==================================================================================================
def is_valid_internal_resource(url, resource_url):
    if "http" not in resource_url:
        return False

    # Get base URL of top level URL
    top_url_base = remove_www(urlparse(url).netloc)

    # Get base URL of resource URL
    resource_url_base = remove_www(urlparse(resource_url).netloc)

    # Check if base URLs match
    if top_url_base == resource_url_base:
        return True
    else:
        return False


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
    resource_dict = top_dict["external_urls"].get(resource_url, None)

    # case where we've seen this resource before
    if resource_dict is not None:
        top_dict["external_urls"][resource_url]["count"] = top_dict["external_urls"][resource_url][
                                                               "count"] + 1

    # case where we have not seen this resource before
    else:
        resource_dict = {"count": 1, "type": resource_type}
        top_dict["external_urls"][resource_url] = resource_dict


# ==================================================================================================
# Finds all URLs of a certain "tag" type in the HTML document. Determines whether resource is
# internal or external and commences further processing accordingly

def parse_resources(tag, attr, soup, top_dict, current_url):
    for t in soup.findAll(tag):
        try:
            resource_url = t[attr]
            resource_url = add_trailing_slash(resource_url)
            resource_url = remove_www(resource_url)
            # --------------------------------------------------------------------------------------
            # Internal, Relative Link
            # TODO handle relative URLs better because I think the way I append the relative url to
            #  the top level URL right now will break in some cases
            if tag == "a" and current_url[-1] == "/" and is_valid_relative_resource(resource_url):
                if resource_url[0] == '/':
                    resource_url = resource_url[1:]
                    resource_url = top_dict["top_url"] + resource_url
                else:
                    resource_url = current_url + resource_url

                analyze_url(resource_url, top_dict)
            # --------------------------------------------------------------------------------------
            # Internal, Absolute Link
            elif tag == "a" and is_valid_internal_resource(top_dict["top_url"], resource_url):
                analyze_url(resource_url, top_dict)
            # --------------------------------------------------------------------------------------
            # External Resource
            elif is_valid_external_resource(top_dict["top_url"], resource_url):
                append_external_resource(top_dict, resource_url, tag)
            # --------------------------------------------------------------------------------------
        except KeyError:
            pass


# ==================================================================================================
def get_links(soup, top_dict, current_url):
    parse_resources('script', "src", soup, top_dict, current_url)
    parse_resources("iframe", "src", soup, top_dict, current_url)
    parse_resources("video", "src", soup, top_dict, current_url)
    parse_resources("audio", "src", soup, top_dict, current_url)
    parse_resources('img', "src", soup, top_dict, current_url)
    parse_resources("a", "href", soup, top_dict, current_url)


'''
    embed_src = find_external_resources("embed", "src", soup)
    object_data = find_external_resources("object", "data", soup)
    soruce_src = find_external_resources("source", "src", soup)
    css_link = find_external_resources("link", "href", soup)
'''


# ==================================================================================================
def is_new_valid_internal_url(url, top_dict):
    # don't parse things we've already seen before
    if url not in top_dict["internal_urls"] and url not in top_dict["error_urls"]:
        # don't parse huge documents that aren't even webpages
        ignore_extensions = (".pdf", ".pptx")
        if not url.endswith(ignore_extensions):
            return True

    else:
        return False


# ==================================================================================================
def analyze_url(url, top_dict):
    url = add_trailing_slash(url)

    if is_new_valid_internal_url(url, top_dict):
        actual_url, page_source = get_webpage_source(url)

        if actual_url and page_source:
            # Handle rare case where URL re-directed
            if url != actual_url:
                if not is_new_valid_internal_url(actual_url, top_dict) or \
                        is_valid_external_resource(actual_url, top_dict["top_url"]):
                    return

                url = actual_url

            top_dict["internal_urls"].add(url)
            soup = BeautifulSoup(page_source, "lxml")
            print("New Valid Internal URL: " + url)
            get_links(soup, top_dict, url)
        else:
            top_dict["error_urls"].add(url)

    return url + " THREAD DONE"


# ==================================================================================================
if __name__ == "__main__":
    # TODO add in argparse to take in the input file and output directory from the command line ...
    #  make them optional, with default values of some kind

    input_path = "input.txt"
    output_dir = "/root/Documents/Network_Security/web_dependencies/data"

    parse_input(input_path)

    threads = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for top_url in TOP_URLS.keys():
            print("ANALYZING WEBPAGE: " + top_url)
            threads.append(executor.submit(analyze_url, top_url, TOP_URLS[top_url]))

    # wait for threads to finish before outputting all JSON files / ending the program
    for f in futures.as_completed(threads):
        print(f.result())

    # TODO have this function create one website's JSON file and thread this as well
    output_to_json(output_dir)
