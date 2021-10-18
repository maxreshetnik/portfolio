=============
Portfolio
=============

maxreshetnik.tk_ source code
------------------------------
including `Shop`_ website

This backend web application is developed in Python using the Django framework,
and Bootstrap tools are used to visually demonstrate how the backend works.

The main application allows an administrator to create multiple portfolios with
a set of projects and other information in each, then choose the most suitable
portfolio to display on the domain home page.

Another purpose of this project is to create connection point for my django apps
to demonstrate how they work. One of such app integrated into this project is
an online store, for more details see in `Shop app`_ repository.

.. _maxreshetnik.tk: https://maxreshetnik.tk/
.. _Shop: https://maxreshetnik.tk/shop/
.. _Shop app: https://github.com/maxreshetnik/shop

To run locally, do the usual
""""""""""""""""""""""""""""""

1.  Create a Python 3.9 virtual environment

2.  Install dependencies::

        pip install -r requirements.txt

3.  Add ``export DJANGO_SETTINGS_MODULE=portfolio.settings.dev`` to your
    activate venv script and restart venv to load the changes.
    If the variable is not specified production settings are used.

4.  Make a directory if you want to store the project's data in other place
    (MEDIA_ROOT, STATIC_ROOT, etc.) then you need to add the variable to
    your user's environment::

        export PORTFOLIO_DATA_DIR=~/your_data_dir

    *by default, the data is stored in the project directory if developer settings
    are set, and in the parent if production.*

    Create a 'secrets.json' file in a directory named 'conf' in that directory
    or in the project parent directory if that data dir is not specified,
    containing something like::

        {
            "secret_key": "abc",
            "allowed_hosts": [
                "127.0.0.1"
            ],
            "db_host": "localhost",
            "db_password": "secret",
            "db_port": "",
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

6.  Create tables::

        ./manage.py migrate

7.  Create a superuser::

        ./manage.py createsuperuser

8.  Start the development server::

        ./manage.py runserver

    Visit http://127.0.0.1:8000/admin/ to create portfolio or fill your online store
    with products, then open http://127.0.0.1:8000/ or http://127.0.0.1:8000/shop/
