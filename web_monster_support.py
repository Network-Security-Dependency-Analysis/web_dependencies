from geoip import geolite2

# ==================================================================================================
# WWW screws up our parser, so get rid of it if a URL contains it

def remove_www(url):
    return url.replace("www.", "")

# ==================================================================================================
# Wrapper function to remove WWW and add trailing slash, for URL uniformity

def cleanup_url(url):
    url = remove_www(url)
    return add_trailing_slash(url)

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
# Get IPv4 addresses from url

def get_ip_4_addresses(url):
    ip_addresses = []
    domain_name = get_domain_name(url)
    for answer in dns.resolver.query(domain_name, 'A'):
        ip_addresses.append(str(answer))
    return ip_addresses