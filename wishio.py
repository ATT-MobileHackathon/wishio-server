import os, requests, json, urllib.parse, re, time, feedparser
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, jsonify, current_app
from pyquery import PyQuery as pq

app = Flask(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2476.0 Safari/537.36'
}

@app.route('/')
def index():
    print(get_macys_info(77589)) #testing
    return "Hello world"

@app.route('/funds/retrieve', methods=['GET'])
def get_all_funds():
    cur = get_db().execute('SELECT Fund.*, Products.*, '
                           'Users.name AS `user.name`, '
                           'Users.photo_url AS `user.photo_url`, '
                           'SUM(Transaction_Fund.contribution) AS `currently_funded`, '
                           'COUNT(Transaction_Fund.contribution) AS `total_funders` '
                           'FROM Fund '
                           'INNER JOIN Users ON Users.idusers = Fund.fundee_id '
                           'INNER JOIN Products ON Products.idproducts = Fund.product_id '
                           'LEFT JOIN Transaction_Fund ON Fund.idfund = Transaction_Fund.fund_id '
                           'GROUP BY Fund.idfund')
    result = [{'user': {'name': row['user.name'], 'image': row['user.photo_url']},
               'item': {'name': row['macy_id'], 'price': row['price'], 'image': row['photo_url']},
               'currently_funded': row['currently_funded'],
               'total_funders': row['total_funders']} for row in cur.fetchall()]
    return jsonify(funds=result)


@app.route('/funds/add', methods=['POST'])
def add_new_fund():
    get_db().execute('INSERT INTO Fund (fundee_id, product_id, total_funders, currently_funded) '
                     'VALUES (?, ?, 0, 0)',
                     (request.form['user_id'], request.form['product_id']))
    get_db().commit()
    return ''


@app.route('/funds/<id>/contribute', methods=['POST'])
def contribute_to_fund(id):
    get_db().execute('INSERT INTO Transaction_Fund (fund_id, funder_id, contribution) '
                     'VALUES (?, ?, ?)',
                     (id, request.form['user_id'], request.form['contribution']))
    get_db().commit()
    return ''

with app.app_context():
    current_app.last_search_by_image_time = 0
    current_app.last_get_pin_images_time = 0


@app.route('/search', methods=['GET'])
def search_by_image():
    time.sleep(max(0, current_app.last_search_by_image_time + 1 - time.time()))
    current_app.last_search_by_image_time = time.time()

    image_url = request.args.get('image_url')

    url_1 = 'http://images.google.com/searchbyimage?image_url=' + urllib.parse.quote(image_url)
    url_2 = requests.get(url_1, allow_redirects=False, headers=HEADERS).headers['location']
    url_3 = url_2 + '&q=site:macys.com'

    text = requests.get(url_3, headers=HEADERS).text
    d = pq(text)
    products = []
    for data in d.find('.rg_meta'):
        macys_image_url = json.loads(data.text)['ou']

        p = re.compile('/(\d+)[^/]+$')
        m = p.search(macys_image_url)
        if m:
            products.append({'macys_id': m.group(1), 'image': macys_image_url})

    return jsonify(products=products)


@app.route('/pins', methods=['GET'])
def get_pin_images():
    time.sleep(max(0, current_app.last_get_pin_images_time + 1 - time.time()))
    current_app.last_get_pin_images_time = time.time()

    user = request.args.get('user')
    d = feedparser.parse('https://www.pinterest.com/' + user+ '/feed.rss')
    r = re.compile('http[^"]+\.jpg')
    results = [{'title': entry['title'], 'image': r.search(entry['summary']).group(0)} for entry in d['entries']]

    return jsonify(results=results)


######################## MACY'S API FUNCTIONS ########################

def get_macys_info(id): 
    """ 
    Given the product id (according to Macy's catalog), add that item to db 
    Makes a request to the Macy's API to get product specs, and returns object 
    with information necessary to populate db columns
    """
    try: 
        headers = {'Accept':'application/json', 'X-Macys-Webservice-Client-Id':'atthack2015'}
        payload = {'imagequality':'90'}
        url = 'https://api.macys.com/v3/catalog/product/' + str(id)
        r = requests.get(url, params=payload, headers=headers)
        j = r.json()
        print('Making GET request... /'+r.url)
        
        name = j['product'][0]['summary']['name']
        customerrating = j['product'][0]['summary']['customerrating']
        photo_url = j['product'][0]['image'][0]['imageurl']
        onsale = j['product'][0]['price']['onsale']
        if onsale == True: 
            price = j['product'][0]['price']['sale']['value']
        else: 
            price = j['product'][0]['price']['regular']['value']
            
        # conver to cents
        price *= 100
        price = int(price)

        result = {
            'name' : name, 
            'customerrating' : customerrating, 
            'photo_url' : photo_url,
            'onsale' : onsale,
            'price' : price
        }
        return result

    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)     
    

######################## DB SETUP & FUNCTIONS ########################
DATABASE = 'database.db' #path to db

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'wishio.db'),
    DEBUG=True,
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = dict_factory
    return rv


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

# creates db tables based on schema.sql
def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

"""
Function: call from command terminal to initialize database
"""
@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')

if __name__ == '__main__':
    app.run(debug=True)