import dns.resolver
import web_monster_support as wms
import globals


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
    try:
        geo_ip_data = globals.GEO_LIB.city(ip_address)
        if geo_ip_data:
            lat = geo_ip_data.location.latitude
            long = geo_ip_data.location.longitude
            return lat, long

    except Exception as e:
        print("ERROR (GEOIP): " + str(e))

    return None, None


# ==================================================================================================
# Get the Autonomous System information for the IP address

def get_ip_asn(ip_address):
    try:
        asn_ip_data = globals.ASN_LIB.asn(ip_address)
        if asn_ip_data:
            asn = asn_ip_data.autonomous_system_number
            as_org = asn_ip_data.autonomous_system_organization
            return asn, as_org
    except Exception as e:
        print("ERROR (ASNIP): " + str(e))

    return None, None


# ==================================================================================================
# Set the location info and IP address info for a given IP in the dictionary

def set_ip4_info(domain, top_dict):
    ip_4_addresses = get_ip4_addrs(domain)

    top_dict["external_domains"][domain]["ip_addresses"] = {}
    for ip_address in ip_4_addresses:

        # Get latitude and longitude by IP address
        lat, long = get_ip_geo(ip_address)

        # Get ASN info by IP address
        asn, as_org = get_ip_asn(ip_address)

        top_dict["external_domains"][domain]["ip_addresses"][ip_address] = {
            "lat": lat,
            "long": long,
            "asn": asn,
            "as_org": as_org
        }


# ==================================================================================================
