#!/usr/bin/env python3
'''
REFERENCES:
    https://stackoverflow.com/questions/31666584/beutifulsoup-to-extract-all-external-resources-from-html
'''

from bs4 import BeautifulSoup
import urllib.request
from urllib.parse import urlparse
from urllib.parse import urljoin
import json
import os
import hashlib

TOP_URLS = {}


# ==================================================================================================
def parse_input(input_file):
    with open(input_file, 'r') as f:
        top_urls = f.readlines()

    top_urls = [x.strip() for x in top_urls]
    for url in top_urls:
        if url:
            top_url_dict = {"top_url": url, "external_urls": {}, "internal_urls": set()}
            TOP_URLS[url] = top_url_dict


# ==================================================================================================
# Outputs a JSON file for each website crawled

def output_to_json(output_directory):
    for url in TOP_URLS.keys():
        # make filename hash of the top url because linux doesn't like :./ in the file name
        hash_object = hashlib.sha1(str.encode(TOP_URLS[url]["top_url"]))
        hex_dig = hash_object.hexdigest()

        json_file = os.path.join(output_directory, str(hex_dig) + ".json")

        # don't actually want to output the internal URLs, and JSON doesn't like sets
        del TOP_URLS[url]["internal_urls"]

        with open(json_file, 'w+') as fp:
            json.dump(TOP_URLS[url], fp)


# ==================================================================================================
# Takes in a URL string and outputs a Beautiful Soup object for further parsing

def url_to_soup(url):
    page_source = urllib.request.urlopen(url)
    return BeautifulSoup(page_source, "lxml")


# ==================================================================================================
# WWW screws up our parser, so get rid of it if a URL contains it

def remove_www(base_url):
    if base_url.startswith("www."):
        base_url = base_url[4:]

    return base_url


# ==================================================================================================
# Returns true if the resource URL is a relative URL, false if its an absolute URL

def is_relative_resource(resource_url):
    return not bool(urlparse(resource_url).netloc)


# ==================================================================================================
# Returns true if the resource comes from an external location, false otherwise

def is_exernal_resource(url, resource_url):
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
        top_dict["external_urls"][resource_url]["count"] = top_dict["external_urls"][resource_url]["count"] + 1

    # case where we have not seen this resource before
    else:
        resource_dict = {"count": 1, "type": resource_type}
        top_dict["external_urls"][resource_url] = resource_dict


# ==================================================================================================
# Finds all URLs of a certain "tag" type in the HTML document. Determines if each URL is internal or
# external. Determines whether resource is internal or external and commences further processing
# accordingly

def parse_resources(tag, attr, soup, top_dict):
    for t in soup.findAll(tag):
        try:
            resource_url = t[attr]
            # --------------------------------------------------------------------------------------
            # Internal, Relative Link
            # TODO handle relative URLs better because I think the way I append the relative url to
            #  the top level URL right now will break in some cases
            if is_relative_resource(resource_url):
                if tag == "a":
                    if resource_url[0] == '/':
                        resource_url = resource_url[1:]

                    resource_url = top_dict["top_url"] + resource_url
                    print(resource_url)
            # --------------------------------------------------------------------------------------
            # TODO Internal, Absolute Link
            # --------------------------------------------------------------------------------------
            # External Resource
            elif is_exernal_resource(top_dict["top_url"], resource_url):
                append_external_resource(top_dict, resource_url, tag)
            # --------------------------------------------------------------------------------------
        except KeyError:
            pass


# ==================================================================================================
def get_links(soup, top_dict):
    parse_resources('script', "src", soup, top_dict)
    parse_resources("iframe", "src", soup, top_dict)
    parse_resources("video", "src", soup, top_dict)
    parse_resources("audio", "src", soup, top_dict)
    parse_resources('img', "src", soup, top_dict)
    parse_resources("a", "href", soup, top_dict)

'''
    embed_src = find_external_resources("embed", "src", soup)
    object_data = find_external_resources("object", "data", soup)
    soruce_src = find_external_resources("source", "src", soup)
    css_link = find_external_resources("link", "href", soup)
'''


# ==================================================================================================
if __name__ == "__main__":
    # TODO add in argparse to take in the input file and output directory from the command line ...
    #  make them optional, with default values of some kind

    input_path = "input.txt"
    output_dir = "/root/Documents/Network_Security/web_dependencies/data"

    parse_input(input_path)

    for top_url in TOP_URLS.keys():
        print("Analyzing webpage: " + top_url)
        soup = url_to_soup(top_url)
        get_links(soup, TOP_URLS[top_url])

    output_to_json(output_dir)
