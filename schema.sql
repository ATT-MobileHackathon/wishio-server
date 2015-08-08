/* users w/ photo */
CREATE TABLE Users (
    idusers INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    photo_url TEXT NOT NULL
);

/* product that is in someone's wishlist, so we save it to db */
CREATE TABLE Products (
    idproducts INTEGER PRIMARY KEY,
    macy_id TEXT NOT NULL,
    name TEXT NOT NULL,
    photo_url TEXT NOT NULL,
    price INTEGER NOT NULL
);

/* represents the overall funding of a user's product item */
CREATE TABLE Fund (
    idfund INTEGER PRIMARY KEY, 
    fundee_id INTEGER NOT NULL, 
    product_id INTEGER NOT NULL,
    FOREIGN KEY(fundee_id) REFERENCES Users(idusers),
    FOREIGN KEY(product_id) REFERENCES Products(idproducts)
);

/* individual funding transaction i.e. person a funds $5 to person b */
CREATE TABLE Transaction_Fund (
    idtransaction INTEGER PRIMARY KEY,
    fund_id INTEGER NOT NULL,
    funder_id INTEGER NOT NULL, 
    contribution INTEGER NOT NULL, -- amount in cents contributed by funder
    FOREIGN KEY(fund_id) REFERENCES Fund(idfund),
    FOREIGN KEY(funder_id) REFERENCES Users(idusers)
);

INSERT INTO Users (idusers, name, photo_url)
VALUES (1, 'Test User', 'https://www.gravatar.com/avatar/55502f40dc8b7c769880b10874abc9d0.jpg');

INSERT INTO Products (idproducts, macy_id, name, photo_url, price)
VALUES (1,
        '649718',
        'A|X Armani Exchange Watch, Men''s Black Ion Plated Stainless Steel Bracelet 46mm AX2104',
        'http://slimages.macys.com/is/image/MCY/products/8/optimized/1106168_fpx.tif?bgc=255,255,255&wid=100&qlt=90&layer=comp&op_sharpen=0&resMode=bicub&op_usm=0.7,1.0,0.5,0&fmt=jpeg',
        18000);

INSERT INTO Fund (idfund, fundee_id, product_id)
VALUES (1, 1, 1);

INSERT INTO Transaction_Fund (idtransaction, fund_id, funder_id, contribution)
VALUES (1, 1, 1, 10000);
