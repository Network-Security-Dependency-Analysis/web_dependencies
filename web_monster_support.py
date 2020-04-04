import dns.resolver
import whois
import geoip2.database
from urllib.parse import urlparse

GEO_CLIENT = geoip2.database.Reader('geoip2_database/GeoLite2-City.mmdb')

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
# Get domain name from url

def get_domain_name(url):
    parsed_url = cleanup_url(url)

    if parsed_url.startswith("http"):
        parsed_url = urlparse(parsed_url).netloc

    return parsed_url


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
# WWW screws up our parser, so get rid of it if a URL contains it

def remove_www(url):
    return url.replace("www.", "")


# ==================================================================================================
# Required for URL matching and being able to append relative URLs

def add_trailing_slash(url):
    if "/" in url:
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
# Get latitude and longitude of a given IP address

def get_lat_long_of_ip(ip_address):
    geo_ip_data = GEO_CLIENT.city(ip_address)

    if geo_ip_data:
        try:
            lat = geo_ip_data.location.latitude
            long = geo_ip_data.location.latitude
            return lat, long
        except Exception as e:
            print("ERROR (GEOIP): " + str(e))

    return None, None


# ==================================================================================================
# Get the registrar for the given domain

def get_domain_registrar(url):
    domain = get_domain_name(url)

    # Get domain information with whois
    if domain:
        try:
            domain_info = whois.query(domain)
            if domain_info:
                if domain_info.registrar:
                    return domain_info.registrar
            return None
        except Exception as e:
            print("ERROR (WHOIS): Could not get registrar for " + domain)
            return None
    else:
        return None


# ==================================================================================================
# Get IPv4 addresses from url

def get_ip_4_addresses(url):
    ip_addresses = []
    domain_name = get_domain_name(url)

    if domain_name:
        try:
            for answer in dns.resolver.query(domain_name, 'A'):
                ip_addresses.append(str(answer))
        except Exception as e:
            print("ERROR (DNS): " + str(e))

    return ip_addresses
