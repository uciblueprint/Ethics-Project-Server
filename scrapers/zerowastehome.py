from bs4 import BeautifulSoup
import requests
from scrapers.utils import *

## for zerowastehome.com

def scrape_zerowastehome():
    '''
    Scrapes content from zerowastehome
    '''
    l = []
    
    base_url = 'https://zerowastehome.com/blog/' 
    print(base_url)

    # Request URL and Beautiful Parser
    r = requests.get(base_url)
    soup = BeautifulSoup(r.text, "html.parser")

    blogposts = soup.find_all('div', class_="post-content")

    for item in blogposts:
        d = { }

        ## url
        url = item.find("a", class_="entire-meta-link")
        d['url'] = url['href']

        ## title
        title = item.find("h3", class_="title").get_text()
        d['title'] = title.strip()

        ## author
        author = item.find("div", class_="text").find("a").get_text()
        d['author'] = author

        ## image_url
        image_url = item.find("span", class_='post-featured-img') 
        #image_url['style'] = ''background-image: url(https://s3-us-east-2.amazonaws.com/zerowaste-media/wp-content/uploads/20180803124650/2018-07-01-06.32.13-900x600.jpg);'
        d['image_url'] = image_url['style'].strip("background-image: url(").strip(");")

        ## publish_date
        publish_date = item.find("div", class_="text").find("span").get_text()
        d['publish_date'] = date_convert(publish_date)

        l.append(d)

    return l


if __name__ == "__main__":
    print(scrape_zerowastehome())
    