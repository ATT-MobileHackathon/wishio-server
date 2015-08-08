/* users w/ photo */
CREATE TABLE Users (
    idusers INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    photo_url TEXT NOT NULL
);

/* product that is in someone's wishlist, so we save it to db */
CREATE TABLE Products (
    idproducts INTEGER PRIMARY KEY,
    macy_id INTEGER NOT NULL, -- might need this for macy's api references? 
    photo_url TEXT NOT NULL,
    price TEXT NOT NULL
);

/* represents the overall funding of a user's product item */
CREATE TABLE Fund (
    idfund INTEGER PRIMARY KEY, 
    fundee_id INTEGER NOT NULL, 
    product_id INTEGER NOT NULL,
    total_funders INTEGER NOT NULL, 
    currently_funded INTEGER NOT NULL, -- can be used to calculate progress
    FOREIGN KEY(fundee_id) REFERENCES Users(idusers),
    FOREIGN KEY(product_id) REFERENCES Products(idproducts)
);

/* individual funding transaction i.e. person a funds $5 to person b */
CREATE TABLE Transaction_Fund (
    idtransaction INTEGER PRIMARY KEY,
    fund_id INTEGER NOT NULL,
    funder_id INTEGER NOT NULL, 
    contribution INTEGER NOT NULL, -- dollar quantity contributed by funder
    FOREIGN KEY(fund_id) REFERENCES Fund(idfund),
    FOREIGN KEY(funder_id) REFERENCES Users(idusers)
);