Offene-Entwicklungshilfe
========================

Offene Entwicklungshilfe – making German developing aid spending more transparent

Background
----------
**[Blog post about the project](http://www.crisscrossed.net/2013/02/12/german-open-aid-data-website/)**

App
----------

The app is implemented by using the Python microframework Flask. It is a lightweight app, in which all the action resides in one file: *openaid.py* Flask is only used for development and to render all of the website files (Frozen-Flask) completely, which can then be deployed to any web server. The interactive part then is done at the client side by Javascript thanks to the [openspending project](https://github.com/openspending). The data can be downloaded at the [OECD CRS website](http://stats.oecd.org/Index.aspx?datasetcode=CRS1) and needs to be then imported into a Sqlite data base. The complete raw data set is a bit hidden; click on the above link in the menu on export and then on "related files".

Installation
------------
For the installation you can use [pip](https://pypi.python.org/pypi/pip/) to install the dependencies.  

``pip install -r requirements.txt``

