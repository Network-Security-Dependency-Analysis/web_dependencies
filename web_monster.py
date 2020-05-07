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
import random
import globals
import web_monster_support as wms
import web_monster_ip as wmi

# URL / HTML Parsing Imports
from urllib.error import HTTPError
import urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from http.client import InvalidURL

# Threading / Concurrency Imports
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor

globals.init()


# ==================================================================================================
# Takes in an input file path, where the input file is a list of newline separated top level URLs
# to crawl. Starts filling out the TOP_URLS global dictionary.

def parse_input(input_file):
    with open(input_file, 'r') as f:
        top_urls = f.readlines()

    # get rid of newlines, etc
    top_urls = [x.strip() for x in top_urls]

    wms.initialize_dicts(top_urls)


# ==================================================================================================
# Outputs a JSON file for each website crawled

def output_to_json(output_directory, url):
    # make filename hash of the top url because linux doesn't like :./ in the file name
    hash_object = hashlib.sha1(str.encode(globals.TOP_URLS[url]["top_url"]))
    hex_dig = hash_object.hexdigest()

    json_file = os.path.join(output_directory, str(hex_dig) + ".json")

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    with open(json_file, 'w') as fp:
        json.dump(globals.TOP_URLS[url], fp)


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
        user_agent = random.choice(globals.USR_AGNTS)
        headers = {'User-Agent': user_agent}

        request = urllib.request.Request(url, headers={'User-Agent': user_agent})
        page_source = urllib.request.urlopen(request, context=ctx_no_secure)
        actual_url = page_source.geturl()

    except (HTTPError, InvalidURL) as e:
        print("ERROR (URL): " + str(e))
        print("URL: " + url)
        return None, None

    return actual_url, page_source


# ==================================================================================================
# Returns true if the resource comes from an external location, false otherwise

def is_valid_external_resource(url, resource_url):
    # avoid wacky URLs that start with things like mailto: or /media/
    if not resource_url.startswith("http"):
        return False

    # Get base URL of top level URL
    top_url_base = wms.remove_www(urlparse(url).netloc)

    # Get base URL of resource URL
    resource_url_base = wms.remove_www(urlparse(resource_url).netloc)

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
        top_dict["external_resources"][resource_url]["count"] += 1

    # case where we have not seen this resource before
    else:
        resource_dict = {"count": 1, "type": resource_type}
        top_dict["external_resources"][resource_url] = resource_dict


# ==================================================================================================
def append_external_domain(top_dict, resource_url, resource_type):
    domain = wms.url_to_domain(resource_url)

    domain_dict = top_dict["external_domains"].get(domain, None)

    # case where we've seen this domain before
    if domain_dict is not None:
        top_dict["external_domains"][domain]["resources"]["total"] += 1
        top_dict["external_domains"][domain]["resources"][resource_type] += 1

    # case where we've never seen this domain
    else:
        top_dict["external_domains"][domain] = {}
        # ------------------------------------------------------------------------------------------
        # Create the resources count dict

        resources_count_dict = {"total": 1}
        for tagType in wms.HTML_ELEMENTS.keys():
            resources_count_dict[tagType] = 0

        resources_count_dict[resource_type] = 1

        top_dict["external_domains"][domain]["resources"] = resources_count_dict
        # ------------------------------------------------------------------------------------------
        # Set the authoritative NS info
        ns_dict = wmi.set_auth_ns_info(domain, top_dict, None)

        # Set the IPv4 address info
        wmi.set_ip4_info(domain, top_dict, ns_dict)


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
            resource_url = wms.cleanup_url(t[attr])

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
                if wms.is_valid_relative_resource(resource_url):
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
def is_new_valid_internal_url(url, top_dict):
    # don't parse things we've already seen before
    if url not in globals.TOP_LOGS[top_dict["top_url"]]["internal_urls"] and url not in \
            globals.TOP_LOGS[top_dict["top_url"]]["error_urls"]:

        if not wms.valid_ending(url) or wms.contains_invalid_substring(url):
            globals.TOP_LOGS[top_dict["top_url"]]["error_urls"].add(url)
            return False
        else:
            return True

    else:
        return False


# ==================================================================================================
def get_links(soup, top_dict, current_url):
    for tagType in wms.HTML_ELEMENTS.keys():
        urlFields = wms.HTML_ELEMENTS[tagType]

        for urlField in urlFields:
            parse_resources(tagType, urlField, soup, top_dict, current_url)


# ==================================================================================================
def analyze_url(url, top_dict):
    if len(globals.TOP_LOGS[top_dict["top_url"]]["internal_urls"]) >= 175:
        return

    url = wms.cleanup_url(url)

    if is_new_valid_internal_url(url, top_dict):
        actual_url, page_source = get_webpage_source(url)

        if actual_url and page_source:
            # --------------------------------------------------------------------------------------
            actual_url = wms.cleanup_url(actual_url)
            # Handle rare case where URL re-directed
            # TODO probably split this out into handle_redirect function and add link to external
            #  dict if it is actually external
            if url != actual_url:
                if not is_new_valid_internal_url(actual_url, top_dict) or \
                        is_valid_external_resource(actual_url, top_dict["top_url"]):
                    globals.TOP_LOGS[top_dict["top_url"]]["error_urls"].add(url)
                    return

                url = actual_url
            # --------------------------------------------------------------------------------------
            print("\tNew Internal URL: " + url)
            globals.TOP_LOGS[top_dict["top_url"]]["internal_urls"].add(url)
            soup = BeautifulSoup(page_source, "lxml")
            get_links(soup, top_dict, url)
        else:
            globals.TOP_LOGS[top_dict["top_url"]]["error_urls"].add(url)

    return url


# ==================================================================================================
def thread_start(url, top_dict, output_dir):

    # Get IPv4 addresses
    ip_4_addresses = wmi.get_ip4_addrs(url, None)

    # Initialize ip_addresses
    top_dict["ip_addresses"] = {}
    for ip_address in ip_4_addresses:
        # Get latitude and longitude by IP address
        lat, long = wmi.get_ip_geo(ip_address)
        top_dict["ip_addresses"][ip_address] = {
            "lat": lat,
            "long": long,
        }

    u = analyze_url(url, top_dict)
    output_to_json(output_dir, u)

    wms.free_up_memory(top_dict)
    print("WEBSITE " + u + " THREAD DONE")


# ==================================================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl webpages for 3rd party links.")
    parser.add_argument("-i", dest="input_file", type=str, help="File containing list of top-level domains to scan", default="./cmu_input.txt")
    parser.add_argument("-o", dest="output_dir", type=str, help="Directory to output JSON results", default="./data/")
    args = parser.parse_args()

    parse_input(args.input_file)

    threads = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for top_url in globals.TOP_URLS.keys():
            print("ANALYZING WEBSITE: " + top_url)
            threads.append(executor.submit(thread_start, top_url, globals.TOP_URLS[top_url],
                                           args.output_dir))

    # wait for threads to finish
    for f in futures.as_completed(threads):
        pass

    '''
    # FOR TESTING PURPOSES ONLY
    for top_url in globals.TOP_URLS.keys():
        print("ANALYZING WEBSITE: " + top_url)
        thread_start(top_url, globals.TOP_URLS[top_url], args.output_dir)
    '''
    print("CRAWL COMPLETE!")
