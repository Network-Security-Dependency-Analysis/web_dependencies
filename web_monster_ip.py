import dns.resolver
import web_monster_support as wms
import ipinfo

import globals


# ==================================================================================================
# Get the IP Info API ready to use

def setup_ipinfo():
    with open("ipinfo_access_token.txt", 'r') as f:
        access_token = f.readline()

    access_token = access_token.strip()
    globals.IP_LIB = ipinfo.getHandler(access_token)


# ==================================================================================================
# Get IPv4 addresses from url

def get_ip4_addrs(url):
    ip_addresses = []
    domain_name = wms.url_to_domain(url)

    if not domain_name.startswith("/"):
        try:
            for answer in dns.resolver.query(domain_name, 'A'):
                ip_addresses.append(str(answer))
        except Exception as e:
            print("ERROR (DNS): " + str(e))

    return ip_addresses


# ==================================================================================================
# Get the latitude and longitude of an IP address

def get_ip_geo(ip_address):
    geo_ip_data = globals.GEO_LIB.city(ip_address)

    if geo_ip_data:
        try:
            lat = geo_ip_data.location.latitude
            long = geo_ip_data.location.latitude
            return lat, long
        except Exception as e:
            print("ERROR (GEOIP): " + str(e))

    return None, None


# ==================================================================================================
def set_ip4_info(domain, top_dict):
    ip_4_addresses = get_ip4_addrs(domain)

    top_dict["external_domains"][domain]["ip_addresses"] = {}
    for ip_address in ip_4_addresses:
        # Get latitude and longitude by IP address
        lat, long = get_ip_geo(ip_address)

        top_dict["external_domains"][domain]["ip_addresses"][ip_address] = {
            "lat": lat,
            "long": long,
        }


# ==================================================================================================
