import os, requests, json, urllib.parse, re, time, feedparser, random
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, jsonify, current_app
from pyquery import PyQuery as pq
from more_itertools import unique_everseen

app = Flask(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2476.0 Safari/537.36'
}

@app.route('/')
def index():
    print(get_macys_info(77589)) #testing
    return "Hello world"

######################## ONBOARDING FUNCTIONS ########################


@app.route('/register', methods=['POST'])
def register_user():
    name = request.form['name']
    pinterest_login = request.form['pinterest']

    user_id = add_user_to_db(name)

    relevant_pins = filter_pin_results(get_pin_images(pinterest_login))
    product_id_arrays = [[result['macys_id'] for result in search_by_image(pin['image'])] for pin in relevant_pins]
    filtered_product_ids = [products[:5] for products in product_id_arrays]
    product_arrays = sort_arrays_by_macys_review(filtered_product_ids)
    filtered_products = [products[:3] for products in product_arrays]
    products_flat_list = [product for product_array in filtered_products for product in product_array]

    for product in products_flat_list:
        product_id = add_product_to_db(product)
        add_fund_to_db(product_id, user_id)

    return jsonify(user_id=user_id)

    
def get_pin_images(user):
    print("get_pin_images: " + user)
    time.sleep(max(0, current_app.last_get_pin_images_time + 1 - time.time()))
    current_app.last_get_pin_images_time = time.time()

    d = feedparser.parse('https://www.pinterest.com/' + user+ '/feed.rss')
    r = re.compile('http[^"]+\.jpg')
    results = [{'title': entry['title'], 'image': r.search(entry['summary']).group(0)} for entry in d['entries']]

    return results

def filter_pin_results(arr): 
    random.shuffle(arr)
    return arr[:3]

def search_by_image(image_url):
    print("search_by_image: " + image_url)
    time.sleep(max(0, current_app.last_search_by_image_time + 1 - time.time()))
    current_app.last_search_by_image_time = time.time()

    url_1 = 'http://images.google.com/searchbyimage?image_url=' + urllib.parse.quote(image_url)
    url_2 = requests.get(url_1, allow_redirects=False, headers=HEADERS).headers['location']
    url_3 = url_2 + '&q=site:macys.com/shop/product/'

    text = requests.get(url_3, headers=HEADERS).text
    d = pq(text)
    products = []
    for data in d.find('.rg_meta'):
        macys_image_url = json.loads(data.text)['ou']
        macys_product_url = json.loads(data.text)['ru']

        p = re.compile('[&?]ID=(\d+)')
        m = p.search(macys_product_url)
        if m:
            products.append({'macys_id': m.group(1), 'image': macys_image_url})

    return products

######################## BUSINESS LOGIC FUNCTIONS ########################

@app.route('/funds/retrieve', methods=['GET'])
def get_all_funds():
    if 'user_id' in request.args:
        user_id = request.args['user_id']
    else:
        user_id = 9999999
    cur = get_db().execute('SELECT Fund.*, Products.*, '
                           'Users.name AS `user.name`, '
                           'Users.idusers AS `user.id`, '
                           'Users.photo_url AS `user.photo_url`, '
                           'SUM(Transaction_Fund.contribution) AS `currently_funded`, '
                           'COUNT(Transaction_Fund.contribution) AS `total_funders` '
                           'FROM Fund '
                           'INNER JOIN Users ON Users.idusers = Fund.fundee_id '
                           'INNER JOIN Products ON Products.idproducts = Fund.product_id '
                           'LEFT JOIN Transaction_Fund ON Fund.idfund = Transaction_Fund.fund_id '
                           'WHERE Fund.fundee_id != ? GROUP BY Fund.idfund', (user_id,))
    result = [{'user': {'user_id': row['user.id'], 'name': row['user.name'], 'image': row['user.photo_url']},
               'item': {'name': row['name'], 'price': row['price'], 'image': row['photo_url']},
               'currently_funded': row['currently_funded'] if row['currently_funded'] is not None else 0,
               'total_funders': row['total_funders'],
               'fund_id': row['idfund']} for row in cur.fetchall()]
    result = sorted(result, key=lambda x: x['currently_funded'] / x['item']['price'], reverse=True)
    return jsonify(funds=result)


@app.route('/funds/contribute', methods=['POST'])
def contribute_to_fund():
    get_db().execute('INSERT INTO Transaction_Fund (fund_id, funder_id, contribution) '
                     'VALUES (?, ?, ?)',
                     (request.form['fund_id'], request.form['user_id'], request.form['contribution']))
    get_db().commit()
    return ''

with app.app_context():
    current_app.last_search_by_image_time = 0
    current_app.last_get_pin_images_time = 0

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
        
        return convert_product_to_db(j['product'][0])

    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)     


def convert_product_to_db(product_json):
    macy_id = product_json['id']
    name = product_json['summary']['name']
    if 'customerrating' in product_json['summary']:
        customerrating = product_json['summary']['customerrating']
    else:
        customerrating = 0
    photo_url = product_json['image'][0]['imageurl']
    try:
        onsale = product_json['price']['onsale']
        if onsale and 'sale' in product_json['price']:
            price = product_json['price']['sale']['value']
        else:
            price = 100.5
            for priceitemkey in product_json['price']:
                priceitem = product_json['price'][priceitemkey]
                if isinstance(priceitem, dict) and 'value' in priceitem:
                    price = priceitem['value']
                    break
    except:
        onsale = False
        price = 101.5

    # conver to cents
    price *= 100
    price = int(price)
    if price < 100:
        price = 100

    result = {
        'macy_id': macy_id,
        'name': name,
        'customerrating': customerrating,
        'photo_url': photo_url,
        'price': price,
        'onsale': False
    }
    return result


def sort_arrays_by_macys_review(id_arrays):
    print("sort_arrays_by_macys_review: " + str(id_arrays))
    all_ids = list(unique_everseen([str(id) for id_array in id_arrays for id in id_array]))
    headers = {'Accept':'application/json', 'X-Macys-Webservice-Client-Id':'atthack2015'}
    id_to_product = {}
    for id in all_ids:
        url = 'https://api.macys.com/v3/catalog/product/' + id
        j = requests.get(url, headers=headers).json()
        if 'product' in j:
            print("sort_arrays_by_macys_review: found: " + id)
            product = j['product'][0]
            id_to_product[id] = convert_product_to_db(product)
        else:
            print("sort_arrays_by_macys_review: not found: " + id)
    product_arrays = []
    for id_array in id_arrays:
        product_array = []
        for id in id_array:
            if id in id_to_product:
                product_array.append(id_to_product[id])
        product_arrays.append(product_array)
    sorted_product_arrays = [sorted(product_array, key=lambda x: x['customerrating'], reverse=True) for product_array in product_arrays]
    return sorted_product_arrays


######################## DB SAVING FUNCTIONS #########################


def add_user_to_db(name):
    cursor = get_db().cursor()
    cursor.execute('INSERT INTO Users (name, photo_url) '
                   'VALUES (?, ?)',
                   (name, 'https://www.gravatar.com/avatar/55502f40dc8b7c769880b10874abc9d0.jpg'))
    get_db().commit()
    return cursor.lastrowid


def add_product_to_db(product):
    cursor = get_db().cursor()
    cursor.execute('INSERT INTO Products (macy_id, name, customerrating, photo_url, price, onsale) '
                   'VALUES (?, ?, ?, ?, ?, ?)',
                   (product['macy_id'], product['name'], product['customerrating'], product['photo_url'], product['price'], product['onsale']))
    get_db().commit()
    return cursor.lastrowid


def add_fund_to_db(product_id, user_id):
    cursor = get_db().cursor()
    cursor.execute('INSERT INTO Fund (fundee_id, product_id) '
                     'VALUES (?, ?)',
                     (user_id, product_id))
    get_db().commit()
    return cursor.lastrowid


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
    app.run(debug=False)