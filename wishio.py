import os
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, jsonify
app = Flask(__name__)

DATABASE = 'database.db' #path to db

@app.route('/')
def index():
    return "Hello world"


@app.route('/funds')
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

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')

if __name__ == '__main__':
    app.run(debug=True)