MQ²_Web
=======

:Author: Pierre-Yves Chibon <pierre-yves.chibon@wur.nl>, <pingou@pingoured.fr>


A web application for MQ2 to quickly visualize output from MapQTL analysis

Assuming one QTL per linkage group and using the LOD threshold set by the user.
This application extracts all the QTLs detected by MapQTL, using the JoinMap
map file, it finds the closest marker and finally put the number of QTLs found
for each marker on the map.

This approach quickly allows you to find and visualize potential QTL hotspot
in your dataset. This is particularly usefull for large QTL analysis on a
large number of traits.


Get this project:
-----------------
Source:  https://github.com/PBR/MQ2_Web


Dependencies:
-------------
.. _Flask: http://flask.pocoo.org/

This project is a `Flask`_ application, as such it depends on:
- python-flask
- python-flask-wtf
- python-wtforms

.. _MQ2: https://github.com/PBR/MQ2

Since this project is a web-interface to MQ2, it requires `MQ2`_ installed.


Deploying this project:
-----------------------

.. _Flask deployment documentation: http://flask.pocoo.org/docs/deploying/

Instruction to deploy this application is available on the
`Flask deployment documentation`_ page.

 **My approach.**

Below is the approach I took to deploy the instance on a local machine.

Retrieve
the sources::

 cd /srv/
 git clone <repo>
 cd MQ2_Web

Copy the
configuration file::

 cp mq2.cfg.sample mq2.cfg

Adjust the configuration file (upload folder, secret key...)

Don't forget to create the folder and set its right it you use a specific one,
for example if you use ``/var/www/uploads`` as upload folder::

 sudo mkdir /var/www/uploads
 sudo chown apache:apache /var/www/uploads

Then configure apache::

 sudo vim /etc/httd/conf.d/wsgi.conf

and put in this file::

 WSGIScriptAlias /mq2 /var/www/wsgi/mq2.wsgi
 <Directory /var/www/wsgi/>
    Order deny,allow
    Allow from all
 </Directory>

Then create the file /var/www/wsgi/mq2.wsgi with::

 import sys
 sys.path.insert(0, '/srv/MQ2_Web')
 
 import mq2_web
 application = mq2_web.APP

Then restart apache and you should be able to access the website on
http://localhost/mq2


Testing:
--------

This project contains unit-tests allowing you to check if your server
has all the dependencies correctly set.

To run them::

 python tests.py

Note that the unit-tests will fail if the ``upload_folder`` defined in
``mq2.cfg`` is not writable for the user running the tests.


Cleaning the upload folder:
---------------------------

Within the sources of the project is a script called ``clean_uploads.py``
which can be called from within a cron job to clean the upload directory
and remove the session older than X days.

This ``X`` is set at the top of the script and can be adjusted as desired.

::

 python clean_uploads.py --help
 
provides more information about the
options available for this script.

Beware that this script requires the ``mq2.cfg`` file to be in the same
directory as it is.


License:
--------

This project is licensed GPLv3+.
