import dns.resolver
import whois
from geoip import geolite2
from urllib.parse import urlparse

# TODO verify that we have all the external source types we care about
HTML_ELEMENTS = {
    "a": "href",
    "script": "src",
    "link": "href",
    "iframe": "src",
    "video": "src",
    "audio": "src",
    "img": "src",
    "embed": "src",
    "object": "data"
}

# ==================================================================================================
# WWW screws up our parser, so get rid of it if a URL contains it

def remove_www(url):
    return url.replace("www.", "")


# ==================================================================================================
def url_to_domain(url):
    domain = urlparse(url).netloc
    remove_substrings = ["https://", "http://"]

    for sub in remove_substrings:
        domain = domain.replace(sub, "")

    return domain


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
# Required for URL matching and being able to append relative URLs

def add_trailing_slash(url):
    url_chunks = url.split('/')
    url_chunks = [i for i in url_chunks if i]
    if len(url_chunks) == 0:
        return url

    last_chunk = url_chunks[-1]
    chunks_len = len(url_chunks)

    if not url.endswith('/'):
        if ("." not in last_chunk) or (url.startswith("http") and chunks_len == 2):
            if (len(last_chunk) > 1) and ("#" not in last_chunk):
                url = url + '/'

    return url


# ==================================================================================================
# Wrapper function to remove WWW and add trailing slash, for URL uniformity

def cleanup_url(url):
    url = remove_www(url)
    return add_trailing_slash(url)


# ==================================================================================================
def get_links(soup, top_dict, current_url):
    for tagType in HTML_ELEMENTS.keys():
        parse_resources(tagType, HTML_ELEMENTS[tagType], soup, top_dict, current_url)


# ==================================================================================================
# Get latitude and longitude of a given IP address

def get_lat_long_of_ip(ip_address):
    geo_ip_data = geolite2.lookup(ip_address)

    if geo_ip_data:
        try:
            location = geo_ip_data.location
        except:
            location = (None, None)
    
    return location[0], location[1]


# ==================================================================================================
# Get domain name from url

def get_domain_name(url):
    url = cleanup_url(url)
    if url.startswith("http"):
        parsed_url = urlparse(url).netloc

    return parsed_url

# ==================================================================================================
# Get the provider name of the given url

def get_domain_provider(url):
    domain = get_domain_name(url)
    # Get domain information with whois
    domain_info = whois.query(domain)
    if domain_info:
        if domain.registrar:
            return domain_info.registrar
    return None


# ==================================================================================================
# Get IPv4 addresses from url

def get_ip_4_addresses(url):
    ip_addresses = []
    domain_name = get_domain_name(url)
    for answer in dns.resolver.query(domain_name, 'A'):
        ip_addresses.append(str(answer))
    return ip_addresses