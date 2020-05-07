'''
REFERENCES:
    https://stackoverflow.com/questions/4066614/how-can-i-find-the-authoritative-dns-server-for-a-domain-using-dnspython
        -- get_auth_ns is largely based on the top answer to this stack overflow question
'''

import dns.resolver
import web_monster_support as wms
import globals
import os
import sys
import json
import random


# ==================================================================================================
def log_dns(logfile, logstring):
    if logfile:
        with open(logfile, "a+") as lf:
            lf.write(logstring)


# ==================================================================================================
# Wrapper function meant to be called from the main web monster file

def set_auth_ns_info(domain, top_dict, logfile):
    try:
        ns_dict = bolster_auth_ns_data(get_auth_ns(domain, logfile, 0))
    except Exception as e:
        print("ERROR (DNS-NS): " + str(e))
        ns_dict = None

    top_dict["external_domains"][domain]["authoritative_name_servers"] = ns_dict
    return ns_dict


# ==================================================================================================
# Recursively find the authoritative name servers for the specified domain. Debugging information is
# written to the file at the path specified by logfile if it is not None

def get_auth_ns(domain, logfile, level):
    if level >= 5:
        raise Exception("LEVEL FIVE HIT")

    try:
        dns_name = dns.name.from_text(domain)

        default = dns.resolver.get_default_resolver()
        default.timeout = 8
        default.lifetime = 8
        nameserver = default.nameservers[0]

        log_dns(logfile, "DNS Name From Text = " + str(dns_name) + "\n")
        log_dns(logfile, "Default Nameserver = " + nameserver + "\n")

        query = dns.message.make_query(dns_name, dns.rdatatype.NS)
        response = dns.query.udp(query, nameserver, timeout=8)
        rcode = response.rcode()

        if rcode == dns.rcode.NOERROR:
            if len(response.authority) > 0:
                rrset = response.authority[0]

                resp = rrset.to_text().split()
                new_domain = resp[0]
                log_dns(logfile, "Parent Domain = " + new_domain + "\n")
                return get_auth_ns(new_domain, logfile, level+1)

            else:
                rrset = response.answer[0]

                nameservers = {}
                for index, r in enumerate(rrset):
                    ns_ip = default.query(r.target).rrset[0].to_text()
                    nameservers[str(r.target)] = {"ip": ns_ip}

                # --------------------------------------------------------------------------------------
                # Log authoritative NS results for testing purposes
                log_dns(logfile, "Authoritative Nameservers: \n")
                for key, item in nameservers.items():
                    item_str = json.dumps(item)
                    log_dns(logfile, key + "\t" + item_str + "\n")
                # --------------------------------------------------------------------------------------

                return nameservers
        else:
            print(str(response.rcode()))
            return None

    except Exception as e:
        print("ERROR (DNS): " + str(e))
        return None


# ==================================================================================================
# The the authoritative name servers for the domain, and find their geolocation and ASN information

def bolster_auth_ns_data(nameservers):
    if nameservers:
        for key, item in nameservers.items():
            ip_addr = item.get("ip")

            lat, long = get_ip_geo(ip_addr)
            asn, asn_org = get_ip_asn(ip_addr)

            item["lat"] = lat
            item["long"] = long
            item["asn"] = asn
            item["asn_org"] = asn_org

            nameservers[key] = item

        return nameservers
    else:
        return None


# ==================================================================================================
# Get IPv4 addresses from url

def get_ip4_addrs(url, nameservers):
    ip_addresses = []
    domain_name = wms.url_to_domain(url)

    if not domain_name.startswith("/"):

        if nameservers:
            try:
                # try to query authoritative nameserver directly
                resolvr = dns.resolver.Resolver()
                resolvr.timeout = 8
                resolvr.lifetime = 8

                ns_key = random.choice(list(nameservers.keys()))
                resolvr.nameservers = [nameservers.get(ns_key).get("ip")]
                for answer in resolvr.query(domain_name, 'A'):
                    ip_addresses.append(str(answer))

                return ip_addresses
            except Exception as e:
                print("ERROR (DNS-NS): " + str(e))

        try:
            default = dns.resolver.get_default_resolver()
            default.timeout = 8
            default.lifetime = 8
            for answer in default.query(domain_name, 'A'):
                ip_addresses.append(str(answer))

            return ip_addresses
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

def set_ip4_info(domain, top_dict, nameservers):
    ip_4_addresses = get_ip4_addrs(domain, nameservers)

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
# FOR TESTING PURPOSES ONLY
if __name__ == "__main__":
    globals.init()

    logFile = os.path.join(os.getcwd(), "DNS_LOG.txt")

    if os.path.exists(logFile):
        os.remove(logFile)

    ns = get_auth_ns(sys.argv[1], logFile, 0)
    ns = bolster_auth_ns_data(ns)
    print(json.dumps(ns))
