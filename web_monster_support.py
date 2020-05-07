from urllib.parse import urlparse
import globals

# TODO verify that we have all the external source types we care about
HTML_ELEMENTS = {
    "a": ["href"],
    "script": ["src"],
    "link": ["href"],
    "iframe": ["src"],
    "video": ["src"],
    "audio": ["src"],
    "img": ["src", "data-src"],
    "embed": ["src"],
    "object": ["data"]
}


# ==================================================================================================
# Get domain name from url

def url_to_domain(url):
    parsed_url = cleanup_url(url)

    if parsed_url.startswith("http"):
        parsed_url = urlparse(parsed_url).netloc

    return parsed_url


# ==================================================================================================
# WWW screws up our parser, so get rid of it if a URL contains it

def remove_www(url):
    url = url.replace("www.", "")
    url = url.replace("www2.", "")
    return url

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
            if ("." not in last_chunk) or (url.startswith("http") and
                                                                 chunks_len == 2):
                if (len(last_chunk) > 1) and ("#" not in last_chunk) and ("page=" not in last_chunk):
                    url = url + '/'

    return url


# ==================================================================================================
# Wrapper function to remove WWW and add trailing slash, for URL uniformity

def cleanup_url(url):
    url = remove_www(url)
    return add_trailing_slash(url)


# ==================================================================================================
# Gets the global dictionaries ready for use

def initialize_dicts(top_urls):
    for url in top_urls:
        if url:
            url = cleanup_url(url)
            domain = url_to_domain(url)

            top_url_dict = {
                "top_url": url,
                "top_domain": domain,
                "external_domains": {},
                "external_resources": {}
            }

            top_log_dict = {
                "internal_urls": set(),
                "error_urls": set()
            }

            globals.TOP_URLS[url] = top_url_dict
            globals.TOP_LOGS[url] = top_log_dict


# ==================================================================================================
# Delete data to free up memory

def free_up_memory(top_dict):
    del top_dict["external_domains"]
    del top_dict["external_resources"]
    del globals.TOP_LOGS[top_dict["top_url"]]["internal_urls"]
    del globals.TOP_LOGS[top_dict["top_url"]]["error_urls"]


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
# Check for substrings... returns true if any ONE of them are in the string

def valid_ending(url):
    valid_extensions = (".htm", ".html", ".js", ".php")

    url_chunks = url.split("/")
    url_chunks = [i for i in url_chunks if i]
    last_chunk = url_chunks[-1].lower()

    if len(url_chunks) > 2 and "." in last_chunk:
        for ext in valid_extensions:
            if ext in last_chunk:
                return True
        else:
            print("IGNORE URL: " + url)
            return False
    else:
        return True


# ==================================================================================================
# Check for substrings... returns true if any ONE of them are in the string

def contains_invalid_substring(url):
    ignore_substrings = (".pdf", "tel:", "javascript:", "mailto:")

    for substring in ignore_substrings:
        if substring in url.lower():
            return True

    else:
        return False


# ==================================================================================================
