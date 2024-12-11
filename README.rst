Base Skeleton to start your application using Flask-AppBuilder
--------------------------------------------------------------

- Install it::

	pip install flask-appbuilder
	git clone https://github.com/dpgaspar/Flask-AppBuilder-Skeleton.git

- Run it::

    $ export FLASK_APP=app
    # Create an admin user
    $ flask fab create-admin
    # Run dev server
    $ flask run


That's it!!
---
```bash
docker exec -it mwm-db psql -U postgres
```
```bash
CREATE DATABASE prefect;
GRANT ALL PRIVILEGES ON DATABASE prefect TO tiffanie;
ALTER DATABASE prefect OWNER TO tiffanie;
```

