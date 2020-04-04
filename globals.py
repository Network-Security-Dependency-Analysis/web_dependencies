import geoip2.database

global TOP_URLS
global TOP_LOGS
global IP_LIB
global GEO_LIB


def init():
    global TOP_LOGS, TOP_URLS, IP_LIB, GEO_LIB

    TOP_URLS = {}
    TOP_LOGS = {}
    IP_LIB = None
    GEO_LIB = geoip2.database.Reader('geoip2_database/GeoLite2-City.mmdb')
