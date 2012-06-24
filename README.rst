MQ²
===

:Author: Pierre-Yves Chibon <pierre-yves.chibon@wur.nl>, <pingou@pingoured.fr>


A simple web application to quickly visualize output from MapQTL analysis.

Assuming one QTL per linkage group and using the LOD threshold set by the user.
This application extracts all the QTLs detected by MapQTL, using the JoinMap
map file, it finds the closest marker and finally put the number of QTLs found
for each marker on the map.

This approach quickly allows you to find and visualize potential QTL hotspot
in your dataset. This is particularly usefull for large QTL analysis on a
large number of traits.

Get this project:
-----------------
Source:  https://github.com/PBR/mq2


Dependencies:
-------------
.. _Flask: http://flask.pocoo.org/

This project is a `Flask`_ application, as such it depends on:
- python-flask
- python-flask-wtf
- python-wtforms


Deploying this project:
-----------------------

.. _Flask deployment documentation: http://flask.pocoo.org/docs/deploying/

Instruction to deploy this application is available on the
`Flask deployment documentation`_ page.

My approach:
 cd /srv/
 git clone <repo>
 sudo vim /etc/httd/conf.d/wsgi.conf
and put in this file:
 WSGIScriptAlias /mq2 /var/www/wsgi/mq2.wsgi
 <Directory /var/www/wsgi/>
     Order deny,allow
     Allow from all
 </Directory>
Then create the file /var/www/wsgi/mq2.wsgi with:
 import sys
 sys.path.insert(0, '/srv/mq2')
 
 import mq2
 application = mq2.APP
Then restart apache and you should be able to access the website on 
http://localhost/mq2


License:
--------

This project is licensed under the new BSD license.
