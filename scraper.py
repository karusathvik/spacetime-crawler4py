import re
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin
from bs4 import BeautifulSoup
import shelve #for storing the data


#bottom two functions are basically PartA.py but modified 
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

#cwf = computer word frequencies
def cwf(text):
    stop_words = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as",
        "at","be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could",
        "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
        "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's",
        "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "s", "i", "d", "i'll", "i'm",
        "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most",
        "mustn't","my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
        "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't",
        "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
        "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
        "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
        "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why",
        "why's","with", "t", "would", "wouldn't", "you", "d", "ll", "re", "ve", "your", "yours", "yourself",
        "yourselves"
    }
    count = 0
    with shelve.open('f.shelve', writeback = True) as fq:
        for word in tokenize(text):
            if word not in stop_words:
                count += 1
                if word in fq:
                    fq[word] += 1
                else:
                    fq[word] = 1
    return count


def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
	new_urls = []
	valid_codes = [200, 404,301,302,307,308] #was only 200 and 404 but loosend up restriction to allow for more urls 

	#this creates and adds sites to its specific domain name to answer questions about count and total unique sites (1 and 4)
	with shelve.open('domains.shelve', writeback=True) as ds:
		key = urlparse(url).netloc
		if key in ds: 
			ds[key].append(url)
		else:
			ds[key] = [url]



	if resp.status in valid_codes: #others are usually forbideen
		soup = BeautifulSoup(resp.raw_response.content, 'lxml') #changed from html.parser for speed

		#checks the meta tag to check if scraping is allowed
		is_html_file = bool(soup.find("html") and soup.find("head") and soup.find("body")) #check we are dealing with a true html file
		alf = True #alf stands for alllowed link following (custom name)
		ai = True #aif stand for allowed indexing 
		robot_meta_tag = soup.find('meta', attrs={'name': 'robots'})
		if robot_meta_tag and 'content'  in robot_meta_tag:
			alf = not ('nofollow' in robot_meta_tag['content']) #False if non follow
			ai = not ('noindex' in robot_meta_tag['content']) # False if non indexable


		if ai and resp.status == 200 and is_html_file: #allowed indexing of the page 	
			page_text = ' '.join([element.get_text(strip=True) for element in soup.find_all(['h1','h2','h3','h4','h5','h6','p'])])

			if len(page_text) > 200: #low information page so not worth 
				total_count = cwf(page_text) #retuns total word count of that file
				with shelve.open('longest_page.shelve', writeback = True) as lp:
					max_count = max(lp.values(), default = 0)
					if total_count > max_count:
						lp.clear()
						lp[url] = total_count
					

		if alf and is_html_file: #allowed link following 
			#extract the links 
			for link in soup.find_all('a'):
				href = link.get('href')
				rel = link.get('rel')
				if href and (not rel or "nofollow" not in rel):
					full_link = urlunparse(urlparse(urljoin(url,href))._replace(fragment='')) #removes the fragment only 
					new_urls.append(full_link) 
						 

	return new_urls
		 
	


def is_valid(url):

	def validate_query_params(query_param):
		keys = ['sort', 'order', 'ref', 'share', 'scroll', 'position']
		for key in keys:
			if key in query_param and query_param[key][0].strip(): #make sure not empty
				return True
		return False


    valid_domains = {'ics.uci.edu', 'cs.uci.edu', 'informatics.uci.edu', 'stat.uci.edu'}
	
    # do a special case for the today uci.edu one
    try:
        parsed = urlparse(url)
        domain = parsed.netloc

        if not any((valid_domain == domain) or (domain.endswith(f".{valid_domain}")) for valid_domain in valid_domains):
            return False  # removes the invalid domains like physics.uci.edu

        if parsed.scheme not in set(["http", "https"]):
            return False
		
        return (
            not re.match(
                r".*\.(css|js|bmp|gif|jpeg|ico"
                + r"|png|tiff|mid|mp2|mp3|mp4"
                + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                + r"|epub|dll|cnf|tgz|sha1"
                + r"|thmx|mso|arff|rtf|jar|csv"
                + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()
            )
            and not re.match(r".*\b(auth|signup|admin|checkout|login|calendar)\b.*", parsed.path.lower())# to remove calendar tags and other private tags 
  			and not validate_query_params(parse_qs(parsed.query.lower()))
			and not re.search(r"filter", parsed.query.lower())
		)
    except TypeError:
        print("TypeError for ", parsed)
        raise
