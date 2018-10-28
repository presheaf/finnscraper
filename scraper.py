import pandas as pd
import requests
import googlemaps
from bs4 import BeautifulSoup

import time
import datetime
import re
import glob
import random

import secrets                  # secrets.py should be a separate file with DIRECTIONS_API_KEY


UA_STRING = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/65.0.3325.181 Chrome/65.0.3325.181 Safari/537.36"
request_headers = {"User-Agent": UA_STRING}

def text_to_num(s):
    """Removes all nonnumeric characters from string, then converts it to
    int. Will flip sign of negative numbers. Also kind of dangerous
    that '2 million' -> 2.

    """
    # try:
    #     return int(s)
    # except ValueError:
    return int("".join(list(filter(lambda s: s.isnumeric(), s))))

def match_url_to_data(url):
    """Given the URL of a FINN match, return a dict of Useful Data"""
    page = requests.get(url, headers=request_headers)

    soup = BeautifulSoup(page.text, "html.parser")
    table = soup.find_all("dl") # table right under title with all the info

    try:
        address_string = soup.find("div", {"class": "bd word-break"}).find("h1").next.next.next.text
    except:
        address_string = "N/A"

    try:
        total_price = text_to_num(table[1].find(text="Totalpris").next.next.text)
    except:
        try:
            total_price = text_to_num(table[0].find(text=re.compile("Prisantydning")).next.next.text)
        except:
            total_price = -1

    try:
        size_string = table[2].find(text="Primærrom").next.next.text
        size = text_to_num(size_string.split()[0]) # split needed to remove ^2
    except:
        size = -1

    try:
        num_soverom = text_to_num(table[2].find(text="Soverom").next.next.text)
    except:
        num_soverom = -1

    try:
        visnings = soup.find(text="Visning").parent.parent.findAll("time")
        visnings = [v.text.strip() for v in visnings]
    except:
        visnings = None
        
    return {
        "address": address_string,
        "price": total_price,
        "size_m2": size,
        "soverom": num_soverom,
        "visnings": visnings,
        "url": url
    }



def travel_time(from_addr, to_addr):
    """Given two address strings, use Google Maps to compute morning commute time between them."""
    gmaps = googlemaps.Client(key=secrets.DIRECTIONS_API)
    arrival_time = datetime.datetime(2018, 5, 20, 8, 0, 0) # 8:00 on 20/5/2018
    directions_result = gmaps.directions(from_addr, to_addr,
                                         mode="transit", arrival_time=arrival_time)
    try:
        return directions_result[0]["legs"][0]["duration"]["value"] #
    except:
        return -1

def create_all_data(urls, delay=(6, 3)):
    """Given a list of urls, open each of them (with a random delay) and """

    data = []
    destination1 = "Bjørnegård school, Nedre Åsvei, Slependen"
    destination2 = "Bjørnegård school, Nedre Åsvei, Slependen"
    
    random.shuffle(urls)    # not sure whether this makes us more or less human
    for i, url in enumerate(urls):
        wait_time = random.normalvariate(delay[0], delay[1])
        start_time = time.time()
        print("At URL {:> 10d} of {}".format(i+1, len(urls)))
        try:
            result = match_url_to_data(url)
            try:
                result["commute_time1_sec"] = travel_time(result["address"], destination1)
                result["commute_time2_sec"] = travel_time(result["address"], destination2)
            except:
                pass
            print(result)
            data.append(result)
        except:
            print("Oops, something went wrong here.\n")
            pass
        elapsed_time = time.time() - start_time
        time.sleep(max(0, wait_time - elapsed_time))
    
    return data

def search_pages_to_urls():
    """Assuming user has saved all the search pages they want to get
    matches from under search_htmls/, grabs all match URLs from those.
    
    NOTE: I think you actually could get most of the data you can find on 
    the actual match page directly from the search page. In particular,
    address, price, etc are at least often visible, soo maybe opening
    the URLs returned by this can be avoided."""
    urls = []
    for fn in glob.glob("search_htmls/*.html"):
        with open(fn) as f:
            s = "".join(f.readlines())
            filesoup = BeautifulSoup(s, "html.parser")
        relative_urls = [
            list(t.children)[1]["href"] for t in filesoup.find_all(
                "div", {"class": "unit flex align-items-stretch result-item"}
            )
        ]
        urls += ["https://www.finn.no" + maybe_suffix
                 if not maybe_suffix.startswith("http") else maybe_suffix
                 for maybe_suffix in relative_urls

        ]
    return list(set(urls))



    


# sandbox

def get_sample_soup(url=None):
    """For testing"""
    if url is None:
        url = "https://www.finn.no/realestate/homes/ad.html?finnkode=119915640"
    soup = BeautifulSoup(requests.get(url, headers=request_headers).text, "html.parser")
    return soup
    
def search_page_to_match_urls(search_url, sleep_time=0):
    """Given the URL of a FINN search, return generator yielding the URLs of all the matches.
    Use sleep_time to set a delay """

    # FINN doesn't seem to want me to do this
    raise NotImplemented

def run_test():
    all_urls = search_pages_to_urls()
    # all_urls = all_urls[:10]
    data = create_all_data(all_urls)
    try:
        import json
        with open("data.json", "w") as f:
            json.dump(data, f)
    except:
        pass
    return data



def estimate_dependence(df):
    """Given a df with columns price, size_m2, commute_time1_sec, predict price as a function of
    the other 2 using linear regression, and return an array """
    import sklearn
    import numpy as np
    X = df[["size_m2", "commute_time1_sec"]].values
    y = df["price"].values
    res = LinearRegression().fit(X, y) 
    pred = np.dot(X, res.coef_.T) + res.intercept_

    return (pred - y)/y

def augment(df):
    sdf = df
    sdf["extra"] = estimate_dependence(df)
    return sdf.sort_values(by="extra", ascending=False)

if __name__ == "__main__":
    data = run_test()


sdf = augment(df)
sdf.to_excel("data.xls")
