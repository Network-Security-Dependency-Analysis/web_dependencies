#https://github.com/pyzzled/selenium/blob/master/headless_browser/headless.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from urllib.parse import urlparse
import json
import os

import web_monster_support as wms
import web_monster_ip as wmi

def evaluate_responses(responses):

    result = {}

    for response in responses:

        if response['params']['response']:
            # Key is clean url
            key = wms.remove_www(urlparse(response['params']['response']['url']).netloc)

            if not key in result:
                result[key] = {}
                result[key]['IP'] = {}
                result[key]['cert_issuer'] = []
                result[key]['mimeType'] = {}

            # Add IP address
            if not response['params']['response'].get('remoteIPAddress') in result[key]['IP']:
                if response['params']['response'].get('remoteIPAddress'):
                    ip_address = response['params']['response']['remoteIPAddress']
                    result[key]['IP'][ip_address] = {}

                    if response['params']['response']['headers'].get('server'):
                        result[key]['IP'][ip_address]['server'] = response['params']['response']['headers']['server']
                    elif response['params']['response']['headers'].get('Server'):
                        result[key]['IP'][ip_address]['server'] = response['params']['response']['headers']['Server']
            
            # Add certificate information if available
            if response['params']['response'].get('securityDetails'):
                if not response['params']['response']['securityDetails'].get('issuer') in result[key]['cert_issuer']:
                    result[key]['cert_issuer'].append(response['params']['response']['securityDetails'].get('issuer'))
            
            # Add filetype
            mimetype = response['params']['response']['mimeType']
            if not mimetype in result[key]['mimeType']:
                result[key]['mimeType'][mimetype] = 1
            else:
                result[key]['mimeType'][mimetype] += 1
    
    with open("responses.json", "w") as results:
        results.write(json.dumps(result))

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

# download the chrome driver from https://sites.google.com/a/chromium.org/chromedriver/downloads
# Add chrome driver directory
chrome_driver = "/Users/ian/Documents/CMU/Spring2020/NetSec/Project/chromedriver"

driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options, executable_path=chrome_driver)

driver.get(" https://pittsburghpa.gov/")

# https://stackoverflow.com/questions/52633697/selenium-python-how-to-capture-network-traffics-response
def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response

browser_log = driver.get_log('performance')
events = [process_browser_log_entry(entry) for entry in browser_log]
responses = [event for event in events if 'Network.responseReceived' == event['method']]
requests = [event for event in events if 'Network.requestWillBeSent' == event['method']]

evaluate_responses(responses)

with open("requests_raw.json", "w") as results:
    for request in requests:
        results.write(json.dumps(request))
        results.write("\n\n")
    
with open("responses_raw.json", "w") as results:
    for response in responses:
        results.write(json.dumps(response))
        results.write("\n\n")