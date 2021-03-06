from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import psycopg2
import requests
import datetime
import scraper_script as Scrapers

from api_url import API

app = Flask(__name__)
CORS(app)
DATABASE_URL = "postgres://rdrhinxhcqfrkm:989d6c91e8eb163284de44343083d0c4928b4d539e493bb8dffbe16ce29e994d@ec2-52-203-98-126.compute-1.amazonaws.com:5432/d8u52i7luh8cuv?sslmode=require"

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Did not provide valid POST body"}), 400

@app.route('/')
def hello():
    return "Hello World!"

@app.route('/articles')
def fetch_articles():
    """
    GET request
    Returns all articles in our database, sorted from most recent publish date
    to least recent
    """
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    cur.execute("select * from articles order by publish_date desc;")
    articles = cur.fetchall()
    col_names = []
    for col in cur.description:
        col_names.append(col[0])
    
    json_articles = []

    for article in articles:
        json_article = dict()
        for i in range(len(col_names)):
            json_article[col_names[i]] = article[i]
        json_articles.append(json_article)
    
    cur.close()
    conn.close()

    return jsonify({"articles": json_articles}), 200

@app.route('/unused_articles/<int:blog_id>', methods=['GET'])
def fetch_unused_articles(blog_id):
    """
    GET request
    gets all unused article id's in a blog
    URL query parameters:
        blog_id (int): blog id of shopify blog
    
    Returns JSON in this format:
    {
        "articles": list of article objects ([{}]),
        "blog_name": name of blog (str)
    }
    """


    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    query = "select * from blogs where id = %s;"
    values = (blog_id,)
    cur.execute(query, values)
    blogs = cur.fetchall()
    # if blog_id not in blog table, return 404
    
    if blogs == []:
        return jsonify({"errors": "Blog with id {} does not exist".format(blog_id)}, 404)


    query = ("(SELECT id FROM articles "
                "ORDER BY publish_date DESC "
                "LIMIT 80)"
                "EXCEPT "
                "(SELECT article_id FROM articles_in_blog "
                "WHERE blog_id = (%s)) "
                )
    values = (blog_id,)
    cur.execute(query, values)
    data = cur.fetchall()

    json = dict()
    query = "select name from blogs where id = %s;"
    values = (blog_id,)
    cur.execute(query, values)
    blog_name = cur.fetchall()
    # updating our return JSON to have blog_name
    json['blog_name'] = blog_name[0][0]

    cur.execute("select * from articles order by publish_date desc;")
    articles = cur.fetchall()
    col_names = []
    for col in cur.description:
        col_names.append(col[0])

    # Fetching the article data in the articles_id list
    article_ids = [id for sublist in data for id in sublist]
    articles = []
    for article_id in article_ids:
        query = "SELECT * from articles where id = %s"
        values = (article_id,)
        cur.execute(query, values)
        data = cur.fetchall()
        article = dict()
        for i in range(len(col_names)):
            article[col_names[i]] = data[0][i]
        articles.append(article)

    # adding the articles list to our returned JSON
    json['articles'] = articles

    cur.close()
    conn.close()

    return jsonify(json), 200


@app.route('/blogs', methods=['GET'])
def get_blogs():
    """
    GET request
    gets all blogs from shopify, inserts them into our table, and returns parsed json
    return json format --> {id:"blog_name"}
    """
    # fetch Shopify blogs
    blogs_r = requests.get(API.BLOG_URL)
    if blogs_r.status_code != 200:
        return blogs_r.json(), blogs_r.status_code

    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()

    blogs_json = blogs_r.json()
    json = dict()    
    for blog in blogs_json["blogs"]:
        json[blog["id"]] = blog["title"]
        # inserts the blogs into our table, and updates the names in case they are changed
        query = "INSERT INTO blogs (id, name) VALUES(%s, %s) ON CONFLICT (id) DO UPDATE SET name = excluded.name;"
        values = (blog["id"], blog["title"])
        cur.execute(query, values)
        conn.commit()

    cur.close()
    conn.close()

    return jsonify(json), 200


@app.route('/add_article', methods=['POST'])
def add_article():
    """
    POST request
    Adds a single article to our database
    POST body params:
        url - link to the article (str)
        title - title of the article (str)
        author - name of the author (str)
        image_url - (str)
        date - date that the article was published (str in MM/DD/YYYY format)
    times_used will be filled on this server's end (initial value: 0)
    """
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    data = request.get_json()
    print(data)
    if data is None:
        return jsonify({"error": "Did not provide POST body"}), 400
    query = "INSERT INTO articles (url, title, author, image_url, publish_date) VALUES(%s, %s, %s, %s, %s)"
    values = (data["url"], data["title"], data["author"], data["image_url"], data["publish_date"])
    cur.execute(query, values)
    conn.commit()

    cur.close()
    conn.close()
    return jsonify({"inserted": "success"}), 200

@app.route("/shopify/articles", methods=['POST'])
def post_articles():
    """
    POST request
    Posts a single article to Shopify blog, and inserts the article
    into the articles_in_blogs table
    POST body params:
        json - contains all data
            article_id - id of article in database (int)
            blog_id - id of blog to post to (int)
            
    """
    blog_id = str(request.json['blog_id'])
    article_id = request.json['article_id']

    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    get_stmt = ("SELECT url, title, site_title, image_url FROM articles "
                "WHERE id = (%s)")
    values = (article_id,)
    cur.execute(get_stmt, values)
    data = cur.fetchall()

    if not data: # if id not found
        abort(404)
    
    # if not data[0][4]:
    #     content = '\n\nURL: '+ data[0][0]
    # else:
    #     content = data[0][4] + '\n\nURL: '+ data[0][0]
    content = f"Read more here: {data[0][0]}"
    json = {'title':data[0][1],
            'body_html':content,
            'author':data[0][2],
            'image':{'src':data[0][3]}}
    r = requests.post(API.ARTICLE_URL(API.ADMIN_URL,blog_id),json={'article':json})

    query = "INSERT INTO articles_in_blog (article_id, blog_id) VALUES(%s, %s)"
    values = (article_id, blog_id)
    cur.execute(query, values)
    conn.commit()

    cur.close()
    conn.close()

    if r.status_code == 201:
        return r.json(), r.status_code
    else:
        return jsonify({"Message":r.text}), r.status_code

@app.route("/scrape_articles", methods=['GET'])
def scrape_articles():
    """
    GET request
    Endpoint to call scraper code (frontend will refresh page after the call is complete)
    """
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    recent_articles = dict()
    for site in Scrapers.all_sites:
        site_query = '%'+site+'%'
        query = ("SELECT * "
                    "FROM articles "
                    "WHERE url LIKE %s "
                    "ORDER by publish_date DESC "
                    "LIMIT 1 ")
        values = (site_query,)

        cur.execute(query, values)
        data = cur.fetchall()

        col_names = []
        for col in cur.description:
            col_names.append(col[0])

        json_article = dict()
        if len(data) > 0:
            for i in range(len(col_names)):
                json_article[col_names[i]] = data[0][i]
        else: # if table is empty
            json_article = {
                'url': "",
                'title':"",
                'author':"",
                'image_url':"",
                'publish_date' : datetime.datetime(1,1,1),
                'site_title': "",
            }
        recent_articles[site] = json_article
            
    articles = Scrapers.run_scrapers(recent_articles)
    print ("Number of new articles: ", len(articles))

    if len(articles) == 0 :
        return jsonify({"error": "Did not provide POST body"}), 400
    for item in articles:
        query = "INSERT INTO articles (url, title, author, image_url, publish_date, site_title) VALUES(%s, %s, %s, %s, %s,%s) ON CONFLICT (url) DO NOTHING"
        values = (item["url"], item["title"], item["author"], item["image_url"], item["publish_date"], item["site_title"])
        cur.execute(query, values)
        conn.commit()

    cur.close()
    conn.close()
    return "200 OK"

@app.route('/recent_article/<string:site>', methods=['GET'])
def recent_article(site):
    """
    GET request
    gets the most recent article for a specific site
    URL query parameters:
        site (string): main website domain
    """
    if site is None:
        return jsonify({"error": "Did not provide main site domain"}), 400
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    site = '%'+site+'%'
    query = ("SELECT * "
                "FROM articles "
                "WHERE url LIKE %s "
                "ORDER by publish_date DESC "
                "LIMIT 1 ")
    values = (site,)

    cur.execute(query, values)
    data = cur.fetchall()

    col_names = []
    for col in cur.description:
        col_names.append(col[0])

    json_article = dict()
    for i in range(len(col_names)):
        json_article[col_names[i]] = data[0][i]
    
    cur.close()
    conn.close()
    return jsonify(json_article), 200


if __name__ == '__main__':
    app.run()



