''' Determine all the resources that are requested using a headless browser

This is Thomas's rendition of Ian's code. The focus is to investigate all the
outbound network requests being made. Doing so allows us to identify which
third party services we are requesting from, and which third party services
will require further requests from other third party services.

References:
- https://github.com/pyzzled/selenium/blob/master/headless_browser/headless.py
- https://stackoverflow.com/questions/52633697/selenium-python-how-to-capture-network-traffics-response
'''

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from urllib.parse import urlparse
import json
import os

import web_monster_support as wms
import web_monster_ip as wmi

# Download from https://sites.google.com/a/chromium.org/chromedriver/downloads
CHROMEDRIVER = '/Users/thomasnguyen/Documents/Carnegie-Mellon/Class/Spring20/18-731/Project/Repos/web_dependencies/chromedriver'
WEBSITE = 'https://users.ece.cmu.edu/~vsekar/Teaching/Spring20/18731/lectures/'
# WEBSITE = 'https://news.google.com/'
# WEBSITE = 'https://visitpittsburgh.com/'
# WEBSITE = 'https://duquesnelight.com/'
# WEBSITE = 'https://www.cmu.edu/'
# WEBSITE = 'https://www.cmu.edu/ini/'
WEBSITE = 'https://zoom.us/'


# Headless browser preferences
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--window-size=1920x1080')
chrome_options.add_experimental_option('w3c', False)
caps = DesiredCapabilities.CHROME
caps['loggingPrefs'] = {
    'browser': 'ALL',
    'performance': 'ALL'
}

# Fetch the website
driver = webdriver.Chrome(desired_capabilities=caps, options=chrome_options, executable_path=CHROMEDRIVER)
driver.get(WEBSITE)

# Parse browser logs
browser_log = driver.get_log('performance')
events = [json.loads(entry['message'])['message'] for entry in browser_log]
responses = [event for event in events if 'Network.responseReceived' == event['method']]
requests = [event for event in events if 'Network.requestWillBeSent' == event['method']]

# Dump browser logs
with open('requests_raw.json', 'w') as results:
    for request in requests:
        results.write(json.dumps(request))
        results.write('\n\n')

# with open('responses_raw.json', 'w') as results:
#     for response in responses:
#         results.write(json.dumps(response))
#         results.write('\n\n')

# Identify all dependencies that exist
for request in requests:
    req_hdr = request['params']['request']

    src = req_hdr['headers']['Referer'] if 'Referer' in req_hdr['headers'] else '//ROOT'
    dst = req_hdr['url']

    if '//' in src and '//' in dst:
        src = src.split('//')[1].split('/')[0]
        dst = dst.split('//')[1].split('/')[0]
    else:
        continue

    print(src + ' --> ' + dst)
