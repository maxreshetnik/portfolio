=============
Portfolio
=============

maxreshetnik.tk_ source code
------------------------------
including `online store`_ demo website

This backend web application is developed in Python using the Django framework,
and Bootstrap tools are used to visually demonstrate how the backend works.

The main application allows an administrator to create portfolio with a set of
projects and other information in each, then choose the most suitable
portfolio to display on the domain home page.

The content of the main page is cached using memcache,
the page has a form for feedback with sending a message to e-mail.

| Another purpose of this project is to showcase how my django applications work.
| One of such app integrated into this project is the `shop`_.

Here are the shop features:
    * Visitors browse products which are grouped in categories
    * Product cards list page and details page with add to cart form
    * Full-text product search
    * Shopping cart & checkout process
    * Confirmation and cancellation of orders by users
    * Ratings and reviews for products
    * User account with personal info and orders.
    * Admin site for content management
    * Control of the available product quantity
    * Breadcrumb navigation & Responsive design

.. _maxreshetnik.tk: https://maxreshetnik.tk/
.. _online store: https://maxreshetnik.tk/shop/
.. _shop: `online store`_

To run locally, do the usual
""""""""""""""""""""""""""""""

1.  Requires python, postgresql, libpq-dev and memcached packages to be installed.

2.  Create a python virtual environment and install dependencies::

        pip install -r requirements.txt

3.  Add ``export DJANGO_SETTINGS_MODULE=portfolio.settings.dev`` to your
    activate venv script and restart venv to load the changes.
    If the variable is not specified production settings are used.

4.  Make a directory if you want to store project data in other place
    (MEDIA_ROOT, STATIC_ROOT, etc.), then you need to add the path to
    environment variable::

        export PROJECT_DATA_DIR=/path/to/your_data_dir

    *by default, media and static data is stored in the project directory.*

    Create a 'secrets.json' file in a directory named 'conf' in that directory
    or specify path to your json file in environment variable PROJECT_SECRETS_FILE,
    in the project conf directory you can find an example, 
    the file contains something like::

        {
            "secret_key": "abc",
            "allowed_hosts": [
                "127.0.0.1",
                "example.com",
            ],
            "db_name": "portfolio",
            "db_user": "portfolio",
            "db_password": "secret",
            "db_host": "localhost",
            "db_port": 5432,
            "cache_location": "localhost:11211",
            "email_host": "smtp.example.com",
            "email_port": 587,
            "email_host_password": "secret",
            "email_host_user": "username"
        }

5.  Check if postgresql is installed and login to psql console to create a
    database and configure a user::

        psql
        CREATE DATABASE portfolio;
        CREATE USER portfolio WITH PASSWORD 'secret';
        ALTER ROLE portfolio SET client_encoding TO 'utf8';
        ALTER ROLE portfolio SET default_transaction_isolation TO 'read committed';
        ALTER ROLE portfolio SET timezone TO 'UTC';
        GRANT ALL PRIVILEGES ON DATABASE portfolio TO portfolio;

    (Use the same password as the one you've used in your secrets.json file)

6.  Create database tables::

        ./manage.py makemigrations && ./manage.py migrate

7.  Create a superuser::

        ./manage.py createsuperuser

8.  Load sample data and start dev server::

        ./manage.py loaddata example_shop_data.json && ./manage.py runserver

    Visit http://127.0.0.1:8000/admin/ to create portfolio or fill up the shop 
    with products, then open http://127.0.0.1:8000/shop/  
