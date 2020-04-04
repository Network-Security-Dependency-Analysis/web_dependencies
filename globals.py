import geoip2.database

global TOP_URLS
global TOP_LOGS
global IP_LIB
global GEO_LIB
global ASN_LIB


def init():
    global TOP_LOGS, TOP_URLS, IP_LIB, GEO_LIB, ASN_LIB

    TOP_URLS = {}
    TOP_LOGS = {}
    GEO_LIB = geoip2.database.Reader('databases/geo_ip_database/GeoLite2-City.mmdb')
    ASN_LIB = geoip2.database.Reader('databases/asn_ip_database/GeoLite2-ASN.mmdb')



