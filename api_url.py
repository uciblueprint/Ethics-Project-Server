# from keys import Keys
import os

class API:

    # API_KEY = Keys.API_KEY
    # PASSWORD = Keys.PASSWORD
    # STORE_NAME = "ethic-bp"
    API_KEY = os.getenv('API_KEY')
    PASSWORD = os.getenv('API_PASSWORD')
    STORE_NAME = os.getenv('STORE_NAME')
    API_VERSION = "2020-01"

    ADMIN_URL = f"https://{API_KEY}:{PASSWORD}@{STORE_NAME}.myshopify.com/admin/api/{API_VERSION}"

    BLOG_URL = f"{ADMIN_URL}/blogs.json"

    ARTICLE_URL = lambda ADMIN_URL, blog_id: f"{ADMIN_URL}/blogs/{blog_id}/articles.json"
    ARTICLE_URL_count = lambda blog_id: f"{ADMIN_URL}/blogs/{blog_id}/articles/count.json"
    ARTICLE_URL_get_single = lambda blog_id, article_id: f"{ADMIN_URL}/blogs/{blog_id}/articles/{article_id}.json"

if __name__ == "__main__":
    print(API.BLOG_URL)
