#!/usr/bin/python

"""
Small web application to start investigating QTL hotspot form QTL
analysis made using MapQTL.

This web-app allows you to upload the output from your MapQTL analysis,
set a number of parameter and retrieve basic information regarding QTL
hotspots.
"""

from flask import (Flask, Response, render_template, request, redirect,
    url_for, flash, send_from_directory)
from flaskext.wtf import Form, FileField, RecaptchaField
from werkzeug import secure_filename
from flaskext.wtf import (Form, FileField, file_allowed, file_required,
    TextField)
#from flaskext.uploads import UploadSet, IMAGES

import ConfigParser
import datetime
import os
import random
import string


from lib.transform_mapfile_to_csv import main as transform_mapfile_to_csv
from lib.parse_mapqtl_file import main as parse_mapqtl_file
from lib.add_marker_to_qtls import main as add_marker_to_qtls
from lib.add_qtl_to_map import main as add_qtl_to_map


# folder where the files can be uploaded
UPLOAD_FOLDER = './uploads'
# Extension allowed for file to upload
ALLOWED_EXTENSIONS = set(['zip'])
# Mimetype allowed for file to upload
ALLOWED_MIMETYPES = set(['application/zip'])

# Turn on or off the debugging mode (turn on only for development).
DEBUG = True
# Create the application.
APP = Flask(__name__)
APP.secret_key = 'df;lkhad;fkl234jbcl90-=davjnk.djbgf-*iqgfb.vkjb34hrt' \
'q2lkhflkjdhflkdjhbfakljgipfurp923243nmrlenr;k3jbt;kt'
APP.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)


class UploadForm(Form):
    mapqtl_input = FileField("MapQTL file",
        validators=[file_required()])
    map_input = FileField("JoinMap file",
        validators=[file_required()])


class SessionForm(Form):
    session_id = TextField("Session identifier")


class InputForm(Form):
    lod_threshold = TextField("LOD Threshold")
    mapqtl_session = TextField("MapQTL session")


def allowed_file(input_file):
    """ Validate the uploaded file.
    Checks if its extension and mimetype are within the lists of
    mimetypes and extensions allowed.
    """
    filename = input_file.filename
    output = '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS \
        and input_file.mimetype in ALLOWED_MIMETYPES
    if not output:
        print "Wrong file: %s - %s" % (filename, input_file.mimetype)
    return output


def generate_session_id(size=15):
    """ Generate a session id using the time and a random string of
    characters.

    @param size, the size of the random string to add to the time stamp.
    """
    chars = string.ascii_uppercase + string.digits
    salt = ''.join(random.choice(chars) for x in range(size))
    output = "%s-%s" % (datetime.datetime.now(), salt)
    output = output.strip()
    for char in [' ', ':', '.', '-']:
        output = output.replace(char, '')
    return output.strip()


def generate_exp_id():
    """ Generate an experiment id using time.
    """
    output = "%s" % datetime.datetime.now()
    output = output.rsplit('.', 1)[0].strip()
    for char in [' ', ':', '.', '-']:
        output = output.replace(char, '')
    return output.strip()


def get_experiment_ids(session_id):
    """ Retrieve the experiment already run within this session.
    """
    folder = '%s/%s' % (UPLOAD_FOLDER, session_id)
    exp_ids = []
    for filename in os.listdir(folder):
        if os.path.isdir('%s/%s' % (folder, filename)) \
            and filename.startswith('20'):
            exp_ids.append(filename)
    return exp_ids


def retrieve_exp_info(session_id, exp_id):
    """ Retrieve the parameters used in the specified experiment.
    """
    folder = '%s/%s/%s' % (UPLOAD_FOLDER, session_id, exp_id)
    config = ConfigParser.RawConfigParser()
    config.read('%s/exp.cfg' % folder)
    lod_threshold = config.getfloat('Parameters', 'LOD_threshold')
    mapqtl_session = config.getint('Parameters', 'MapQTL_session')
    return {'lod_threshold': lod_threshold,
            'mapqtl_session': mapqtl_session}


def retrieve_qtl_number(session_id, exp_id):
    """ Retrieve the evolution of the number of QTLs per marker in
    the results of the experiment.
    """
    folder = '%s/%s/%s' % (UPLOAD_FOLDER, session_id, exp_id)
    stream = open('%s/map_with_qtl.csv' % folder, 'r')
    qtls_evo = []
    for row in stream.readlines():
        row = row.split(',')
        if row[3].startswith('#'):
            continue
        else:
            qtls_evo.append(row[3].strip())
    return qtls_evo


def run_mq2(session_id, lod_threshold, mapqtl_session):
    """ Run the scripts to extract the QTLs.
    """
    folder = '%s/%s' % (UPLOAD_FOLDER, session_id)
    exp_id = generate_exp_id()
    exp_folder = '%s/%s/' % (folder, exp_id)
    if not os.path.exists(exp_folder):
        os.mkdir(exp_folder)

    write_down_config('%s/%s' % (folder, exp_id),
        lod_threshold,
        mapqtl_session)

    transform_mapfile_to_csv(folder=folder,
        inputfile='map',
        outputfile='map.csv')

    parse_mapqtl_file(folder=folder,
        sessionid=mapqtl_session,
        zipfile='%s/input.zip'% (folder),
        lodthreshold=lod_threshold,
        outputfile='%s/qtls.csv' % (exp_id))

    add_marker_to_qtls(folder,
        qtlfile='%s/qtls.csv' % (exp_folder),
        mapfile='%s/map.csv' % (folder),
        outputfile='%s/qtl_with_mk.csv' % (exp_id))

    add_qtl_to_map(folder,
        qtlfile='%s/qtl_with_mk.csv' % (exp_folder),
        mapfile='%s/map.csv' % (folder),
        outputfile='%s/map_with_qtl.csv' % (exp_id))


def write_down_config(folder, lod_threshold, mapqtl_session):
    """ Write down the configuration used in an experiment.
    """
    config = ConfigParser.RawConfigParser()
    config.add_section('Parameters')
    config.set('Parameters', 'LOD_threshold', lod_threshold)
    config.set('Parameters', 'MapQTL_session', mapqtl_session)

    with open('%s/exp.cfg' % folder, 'wb') as configfile:
        config.write(configfile)

##  Web-app


@APP.route('/', methods=['GET', 'POST'])
def index():
    """ Shows the front page.
    All the content of this page is in the index.html file under the
    templates directory. The file is full html and with the form for the
    upload and the setting of the parameters.
    """
    print 'mq2 %s -- %s -- %s' % (datetime.datetime.now(),
        request.remote_addr, request.url)
    form = UploadForm(csrf_enabled=False)
    session_form = SessionForm(csrf_enabled=False)
    if session_form.validate_on_submit():
        session_id = session_form.session_id.data
        return redirect(url_for('session', session_id=session_id))
    if form.validate_on_submit():
        print "youhou!"
        upload_file = request.files['mapqtl_input']
        map_file = request.files['map_input']
        if upload_file and allowed_file(upload_file)\
            and map_file:
            filename = secure_filename(upload_file.filename)
            session_id = generate_session_id()
            upload_folder = '%s/%s' %(UPLOAD_FOLDER , session_id)
            os.mkdir(upload_folder)
            upload_file.save(os.path.join(upload_folder,
                'input.zip'))
            map_file.save(os.path.join(upload_folder,
                'map'))
            return redirect(url_for('session', session_id=session_id))
        else:
            flash('Wrong file type or name.')
    return render_template('index.html', form=form,
        session_form=session_form)


@APP.route('/session/<session_id>/', methods=['GET', 'POST'])
def session(session_id):
    print 'mq2 %s -- %s -- %s' % (datetime.datetime.now(),
        request.remote_addr, request.url)
    form = InputForm(csrf_enabled=False)
    if not session_id in os.listdir(UPLOAD_FOLDER):
        flash('This session does not exists')
        return redirect(url_for('index'))

    if form.validate_on_submit():
        lod_threshold = form.lod_threshold.data
        mapqtl_session = form.mapqtl_session.data
        run_mq2(session_id, lod_threshold, mapqtl_session)
    exp_ids = get_experiment_ids(session_id)
    return render_template('session.html', session_id=session_id,
        form=form, exp_ids=exp_ids)


@APP.route('/session/<session_id>/<exp_id>/')
def results(session_id, exp_id):
    print 'mq2 %s -- %s -- %s' % (datetime.datetime.now(),
        request.remote_addr, request.url)
    if not session_id in os.listdir(UPLOAD_FOLDER):
        flash('This session does not exists')
        return redirect(url_for('index'))
    folder = '%s/%s' % (UPLOAD_FOLDER, session_id)
    if not exp_id in os.listdir(folder):
        flash('This experiment does not exists')
        return redirect(url_for('session', session_id=session_id))
    infos = retrieve_exp_info(session_id, exp_id)
    qtls_evo = retrieve_qtl_number(session_id, exp_id)
    qtls_evo = [float(it) for it in qtls_evo]
    max_qtls = 0
    if qtls_evo:
        max_qtls = max(qtls_evo) + 2
    date = '%s-%s-%s at %s:%s:%s' %(exp_id[:4], exp_id[4:6], exp_id[6:8],
        exp_id[8:10], exp_id[10:12], exp_id[12:14])
    return render_template('results.html', session_id=session_id,
        exp_id=exp_id, infos=infos, date=date,
        qtls_evo=qtls_evo, max_qtls=max_qtls)


@APP.route('/retrieve/<session_id>/<exp_id>/<filename>')
def retrieve(session_id, exp_id, filename):
    print 'mq2 %s -- %s -- %s' % (datetime.datetime.now(),
        request.remote_addr, request.url)
    upload_folder = '%s/%s/%s/' % (UPLOAD_FOLDER, session_id, exp_id)
    return send_from_directory(upload_folder, filename)


if __name__ == '__main__':
    APP.debug = DEBUG
    APP.run()
