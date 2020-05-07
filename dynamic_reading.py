#https://github.com/pyzzled/selenium/blob/master/headless_browser/headless.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from urllib.parse import urlparse
import argparse
import json
import hashlib
import os

import globals

import web_monster_support as wms
import web_monster_ip as wmi

# Threading / Concurrency Imports
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor

globals.init()

def parse_input(input_file):
    """ Takes in an input file path, where the input file is a list of 
        newline separated top level URLs to crawl. Starts filling out the 
        TOP_URLS global dictionary.
    """

    with open(input_file, 'r') as f:
        top_urls = f.readlines()

    # get rid of newlines, etc
    top_urls = [x.strip() for x in top_urls]

    wms.initialize_dicts(top_urls)

def setup_driver(CHROME_DRIVER_PATH):
    """ Setup driver with capabilities """ 

    # instantiate a chrome options object so you can set the size and headless preference
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_experimental_option('w3c', False)

    caps = DesiredCapabilities.CHROME
    caps['loggingPrefs'] = {
        'browser': 'ALL',
        'performance': 'ALL'
        }
    driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options, executable_path=CHROME_DRIVER_PATH)

    return driver

def evaluate_responses(responses, domain, top_dict):
    """ Retrieve dependency information from responses """

    for response in responses:
        
        # Remove extra data from structure
        response = response['params'].get('response')

        if response:
            # Key is clean url
            key = wms.remove_www(urlparse(response['url']).netloc)

            if not key == domain:
                # Check if key exists
                if not key in top_dict['external_domains']:
                    top_dict['external_domains'][key] = {}

                curr_dict = top_dict['external_domains'][key]
            else:
                curr_dict = top_dict

            # Add entries if they do not exist
            if not 'ip_addresses' in curr_dict:
                curr_dict['ip_addresses'] = {}
            if not 'cert_issuer' in curr_dict:
                curr_dict['cert_issuer'] = []
            if not 'mimeType' in curr_dict:
                curr_dict['mimeType'] = {}
            
            if response.get('remoteIPAddress'):
                ip_address = response['remoteIPAddress']

                # Add IP address
                if not ip_address in curr_dict['ip_addresses']:
                    curr_dict['ip_addresses'][ip_address] = {}
                # Add server information if available                
                if ip_address in curr_dict['ip_addresses']:
                    if response['headers'].get('server'):
                        curr_dict['ip_addresses'][ip_address]['server'] = response['headers']['server']
                    elif response['headers'].get('Server'):
                        curr_dict['ip_addresses'][ip_address]['server'] = response['headers']['Server']
            
            # Add certificate information if available
            if response.get('securityDetails'):
                if not response['securityDetails'].get('issuer') in curr_dict['cert_issuer']:
                    curr_dict['cert_issuer'].append(response['securityDetails'].get('issuer'))
            
            # Add filetype
            mimetype = response['mimeType']
            if not mimetype in curr_dict['mimeType']:
                curr_dict['mimeType'][mimetype] = 1
            else:
                curr_dict['mimeType'][mimetype] += 1
            
def evaluate_requests(requests, orig_url, top_dict):
    """ Retrieve dependency information from requests """

    # Identify all dependencies that exist
    for request in requests:
        req_hdr = request['params']['request']

        src = req_hdr['headers']['Referer'] if 'Referer' in req_hdr['headers'] else ''
        dst = req_hdr['url']

        if '//' in src and '//' in dst:
            src = src.split('//')[1].split('/')[0]
            # Skip if originating url is the root
            if orig_url in src:
                continue    
            dst = dst.split('//')[1].split('/')[0]

            # Add dependencies from third party dependencies
            if src in top_dict['external_domains']:

                if not 'dependencies' in top_dict['external_domains'][src]:
                    top_dict['external_domains'][src]['dependencies'] = []
                if not dst in top_dict['external_domains'][src]['dependencies']:
                    top_dict['external_domains'][src]['dependencies'].append(dst)
        else:
            continue

def output_to_json(output_directory, url):
    # make filename hash of the top url because linux doesn't like :./ in the file name
    hash_object = hashlib.sha1(str.encode(globals.TOP_URLS[url]["top_url"]))
    hex_dig = hash_object.hexdigest()

    json_file = os.path.join(output_directory, str(hex_dig) + ".json")

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    with open(json_file, 'w') as fp:
        json.dump(globals.TOP_URLS[url], fp, indent=4)

def thread_start(url, top_dict, output_dir):

    # Get IPv4 addresses
    ip_4_addresses = wmi.get_ip4_addrs(url)

    # Initialize ip_addresses
    top_dict["ip_addresses"] = {}
    for ip_address in ip_4_addresses:
        # Get latitude and longitude by IP address
        lat, long = wmi.get_ip_geo(ip_address)
        top_dict["ip_addresses"][ip_address] = {
            "lat": lat,
            "long": long,
        }

    # Get url with driver
    driver.get(url)
    
    def process_browser_log_entry(entry):
        """ Process browser logs 
            Ref: https://stackoverflow.com/questions/52633697/selenium-python-how-to-capture-network-traffics-response
        """

        response = json.loads(entry['message'])['message']
        return response

    # Get browser logs and events
    browser_log = driver.get_log('performance')
    events = [process_browser_log_entry(entry) for entry in browser_log]
    # Parse responses from events
    responses = [event for event in events if 'Network.responseReceived' == event['method']]
    # Parse requests from events
    requests = [event for event in events if 'Network.requestWillBeSent' == event['method']]

    # Get domain from url
    domain = wms.remove_www(urlparse(url).netloc)

    evaluate_responses(responses, domain, top_dict)
    evaluate_requests(requests, domain, top_dict)

    # Save results to output
    output_to_json(output_dir, url)

    wms.free_up_memory(top_dict)
    print("WEBSITE " + url + " THREAD DONE")

if __name__ == "__main__":
    
    # download the chrome driver from https://sites.google.com/a/chromium.org/chromedriver/downloads
    # Add chrome driver directory
    CHROME_DRIVER_PATH = "/Users/ian/Documents/CMU/Spring2020/NetSec/Project/chromedriver"

    driver = setup_driver(CHROME_DRIVER_PATH)

    parser = argparse.ArgumentParser(description="Crawl webpages for 3rd party links.")
    parser.add_argument("-i", dest="input_file", type=str, help="File containing list of top-level domains to scan", default="./input_files/pittsburgh_input.txt")
    parser.add_argument("-o", dest="output_dir", type=str, help="Directory to output JSON results", default="./data/dynamic-2/")
    args = parser.parse_args()

    parse_input(args.input_file)

    threads = []
    # with ThreadPoolExecutor(max_workers=5) as executor:
    #     for top_url in globals.TOP_URLS.keys():
    #         print("ANALYZING WEBSITE: " + top_url)
    #         threads.append(executor.submit(thread_start, top_url, globals.TOP_URLS[top_url],
    #                                        args.output_dir))

    # # wait for threads to finish
    # for f in futures.as_completed(threads):
    #     pass
    # '''
    # FOR TESTING PURPOSES ONLY
    for top_url in globals.TOP_URLS.keys():
        print("ANALYZING WEBSITE: " + top_url)
        thread_start(top_url, globals.TOP_URLS[top_url], args.output_dir)
    # '''
    print("CRAWL COMPLETE!")