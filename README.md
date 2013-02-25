Offene-Entwicklungshilfe
========================

Offene Entwicklungshilfe - a website to make German developing aid spending transparent

Background
----------
**[Blog post about the project](http://www.crisscrossed.net/2013/02/12/german-open-aid-data-website/)**

App
----------
The app is implemented using the Python microframework Flask. It is a lightweight app, where all the action resides in one file *openaid.py*. But Flask is only used for development and to render all files of the website completely, which can then be deployed to any web server. The interactive past then is done client side by Javascript thanks to the [openspending project](https://github.com/openspending). The data can be downloaded at the [OECD CRS website](http://stats.oecd.org/Index.aspx?datasetcode=CRS1) and needs then imported into a Sqlite data base. The complete raw data set is a bit hidden; click on the above link in the menu on export and then on "related files". 

Installation
------------
For the installation you can use [pip](https://pypi.python.org/pypi/pip/) to install the dependencies.  

``pip install -r requirements.txt``

