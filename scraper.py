import re
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin
from bs4 import BeautifulSoup
import shelve  # for storing the data
from nltk.corpus import stopwords
import nltk

stop_words = None

# bottom two functions are basically PartA.py but modified 
def tokenize(text):
    result = ''
    for val in text:
        if val.isalnum():
            result += val.lower()
        else:
            if result:
                yield result
                result = ''
    if result:
        yield result

def density_calculation(text):
    # should return a decimal between 0-1 with the lower end being unfavorable
    stop_word_count = 0
    normal_count = 1
    for word in tokenize(text):
        if word not in stop_words:
            normal_count += 1
        else:
            stop_word_count += 1
    return stop_word_count / (stop_word_count + normal_count)

# cwf = compute word frequencies
def cwf(text):
    global stop_words
    if not stop_words:
        nltk.download('stopwords')
        stop_words = set(stopwords.words('english'))

    density = density_calculation(text)
    count = 0
    if density < 0.55:
        with shelve.open('f.shelve', writeback=True) as fq:
            for word in tokenize(text):
                count += 1
                if word not in stop_words and len(word) > 3: #ensures the word is 4 or more characters because why would we want smaller characters
					if word in fq:
                        fq[word] += 1
                    else:
                        fq[word] = 1
    return count

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def check_calendar(raw_text, parsed):
    raw_text = raw_text.lower()
    # returns true if a calendar
    return (
        ((bool(re.search(r"\b\d{4}-\d{2}-\d{2}\b", parsed.query.lower()))
          or re.search(r"\b\d{4}-\d{2}-\d{2}\b", parsed.path.lower())
          or 'calendar' in parsed.path.lower()
          or bool(re.search(r"\b\d{4}-\d{2}\b", parsed.path.lower()))
          or bool(re.search(r"\b\d{4}-\d{2}\b", parsed.query.lower()))
          or bool(re.search(r"eventdisplay", parsed.query.lower()))))
    )


def extract_next_links(url, resp):
    new_urls = []

    soup = BeautifulSoup(resp.raw_response.content, 'lxml')
    # checks the meta tag to check if scraping is allowed
    is_html_file = bool(soup.find("html") and soup.find("head") and soup.find("body"))  # check we are dealing with a true html file

    if is_html_file and resp.status == 200:  # others are usually forbidden
        # only adds the valid domains that we decided to parse through
        with shelve.open('domains.shelve', writeback=True) as ds:
            key = urlparse(url).netloc
            if key in ds:
                ds[key].append(url)
            else:
                ds[key] = [url]

        alf = True  # alf stands for allowed link following (custom name)
        ai = True  # ai stands for allowed indexing
        robot_meta_tag = soup.find('meta', attrs={'name': 'robots'})
        if robot_meta_tag and 'content' in robot_meta_tag:
            alf = not ('nofollow' in robot_meta_tag['content'])  # False if non-follow
            ai = not ('noindex' in robot_meta_tag['content'])  # False if non-indexable

        calendar_check = check_calendar(soup.get_text(separator=' ', strip=True), urlparse(url))  # check if we are dealing with an empty calendar

        if alf and not calendar_check:  # allowed link following
            # extract the links
            for link in soup.find_all('a'):
                href = link.get('href')
                rel = link.get('rel')
                if href and (not rel or "nofollow" not in rel):
                    full_link = urljoin(resp.raw_response.url, href).split('#')[0]  # removes the fragment only
                    new_urls.append(full_link)

        if ai and not calendar_check:  # allowed indexing of the page
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()
            page_text = soup.get_text()
            if len(page_text) > 350:  # low information page so not worth
                total_count = cwf(page_text)  # returns total word count of that file
                with shelve.open('longest_page.shelve', writeback=True) as lp:
                    max_count = max(lp.values(), default=0)
                    if total_count > max_count:
                        lp.clear()
                        lp[url] = total_count
                        with open("long_file.txt", "w") as file:
                            file.write(page_text)

    return new_urls


def is_valid(url):
    def validate_query_params(query_param):
        keys = ['sort', 'ref', 'share', 'scroll', 'position', 'idx', 'C', 'O', 'upname']
        if (query_param.get('action') and 'login' in query_param['action'][0].strip()) or (query_param.get('do') and 'backlink' in query_param['do'][0].strip()):
            return True
        for key in keys:
            if key in query_param and query_param[key][0].strip():  # make sure the params don’t lead to empty values hence the strip
                return True
        return False

    valid_domains = {'ics.uci.edu', 'cs.uci.edu', 'informatics.uci.edu', 'stat.uci.edu'}

    try:
        parsed = urlparse(url)
        domain = parsed.netloc
		special_link = False
        if domain == 'today.uci.edu' and parsed.path.startswith('/department/information_computer_sciences'):
        	special_link = True

        # Check if domain is valid
        if not special_link and not any((valid_domain == domain) or (domain.endswith(f".{valid_domain}")) for valid_domain in valid_domains):
            return False  # Exclude invalid domains like physics.uci.edu
       

        # Check if scheme is valid
        if parsed.scheme not in {"http", "https"}:
            return False

        # Validate file types, paths, and query parameters
        return (
            not re.match(
                r".*\.(css|js|bmp|gif|jpeg|ico|jpg|cpp|h|wvx"
                r"|png|tiff|mid|mp2|mp3|mp4|apk"
                r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|lif"
                r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|war|bst|mpg|tgz|cc"
                r"|epub|dll|cnf|tgz|sha1|bib"
                r"|thmx|mso|arff|rtf|jar|csv|Z|ppsh|ppsx|img|sql|class"
                r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()
            )
            and not re.match(r".*\b(auth|signup|admin|checkout|login|calendar|pix)\b.*", parsed.path.lower())  # sensitive information as well as calendar
            and not validate_query_params(parse_qs(parsed.query.lower()))
            and not re.search(r"\bfilter\b", parsed.query.lower())  # just for filters
            and not (bool(re.search(r"\b\d{4}-\d{2}-\d{2}\b", parsed.query) or re.search(r"\b\d{4}-\d{2}-\d{2}\b", parsed.path)) and 'events' in parsed.path)  # another calendar check
            and not bool(re.search(r"^.*?(/.+?/).*?\1.*$|^.*?/(.+?/).*\2.*$", parsed.path.lower())))

    except TypeError:
        print("TypeError for", parsed)
        raise




