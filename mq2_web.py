#!/usr/bin/python

"""
Small web application to start investigating QTL hotspot form QTL
analysis made using MapQTL.

This web-app allows you to upload the output from your MapQTL analysis,
set a number of parameter and retrieve basic information regarding QTL
hotspots.
"""

from flask import (Flask, render_template, request, redirect, url_for,
    flash, send_from_directory)
from flaskext.wtf import (Form, FileField, file_required, TextField,
    Required)
from wtforms.validators import StopValidation

import ConfigParser
import datetime
import os
import random
import shutil
import string
import tempfile
import zipfile
from ConfigParser import NoSectionError, NoOptionError

try:
    import zlib
    ZCOMPRESSION = zipfile.ZIP_DEFLATED
except:
    ZCOMPRESSION = zipfile.ZIP_STORED

from pymq2 import (set_tmp_folder, extract_zip, MQ2Exception,
    MQ2NoMatrixException, MQ2NoSuchSessionException)
from pymq2.generate_map_from_mapqtl import generate_map_from_mapqtl
from pymq2.parse_mapqtl_file import parse_mapqtl_file
from pymq2.add_marker_to_qtls import add_marker_to_qtls
from pymq2.add_qtl_to_map import add_qtl_to_map


CONFIG = ConfigParser.ConfigParser()
CONFIG.readfp(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
    'mq2.cfg')))
# folder where the files can be uploaded
UPLOAD_FOLDER = CONFIG.get('mq2', 'upload_folder')
# Extension allowed for file to upload
ALLOWED_EXTENSIONS = set(item.strip() for item in CONFIG.get('mq2',
    'allowed_extensions').split(','))
# Mimetype allowed for file to upload
ALLOWED_MIMETYPES = set(item.strip() for item in CONFIG.get('mq2',
    'allows_mimetypes').split(','))

# Create the application.
APP = Flask(__name__)
APP.secret_key = CONFIG.get('mq2', 'secret_key')

if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)


## I wonder if these two class could be removed by using the NumberRange
## object from wtforms. But it seems to not validate correctly.
class ValidateFloat(object):
    """
    Validates that the field contains a float. This validator will stop the
    validation chain on error.

    @param message Error message to raise in case of a validation error.
    """
    field_flags = ('required', )

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        try:
            float(field.data)
        except ValueError:
            if self.message is None:
                self.message = field.gettext(
                    u'This field should contain a float.')

            field.errors[:] = []
            raise StopValidation(self.message)


class ValidateInt(object):
    """
    Validates that the field contains a integer. This validator will
    stop the validation chain on error.

    @param message Error message to raise in case of a validation error.
    """
    field_flags = ('required', )

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        try:
            float(field.data)
        except ValueError:
            if self.message is None:
                self.message = field.gettext(
                    u'This field should contain an integer.')

            field.errors[:] = []
            raise StopValidation(self.message)


class UploadForm(Form):
    """ Form used to upload the MapQTL output file and the JoinMap map
    file.
    """
    mapqtl_input = FileField("MapQTL zip file",
        validators=[file_required()])


class SessionForm(Form):
    """ Form used to specify a session identifier to be able to go back
    to this specific session.
    """
    session_id = TextField("Session identifier",
        validators=[Required()])


class InputForm(Form):
    """ Form used to specify the arguments needed when extracting the
    QTLs information from the MapQTL output.
    """
    lod_threshold = TextField("LOD Threshold",
        validators=[Required(), ValidateFloat()])
    mapqtl_session = TextField("MapQTL session",
        validators=[Required(), ValidateInt()])


## Functions


def allowed_file(input_file):
    """ Validate the uploaded file.
    Checks if its extension and mimetype are within the lists of
    mimetypes and extensions allowed.

    @param input_file a File object uploaded and for which we want to
    check that its extension and it mimetype is allowed.
    """
    filename = input_file.filename
    output = '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS \
        and input_file.mimetype in ALLOWED_MIMETYPES
    if not output:
        print "Wrong file: %s - %s" % (filename, input_file.mimetype)
    return output


def experiment_done(session_id, lod_threshold, mapqtl_session):
    """ Check within a session if there is not already an existing
    experiment which used the same parameters.

    @param session_id the session identifier uniquely identifying the
    MapQTL zip file and the JoinMap map file. The session identifier
    also uniquely identifies the folder in which are the files uploaded.
    @param lod_threshold the LOD threshold to use to consider a value
    significant for a QTL.
    @param mapqtl_session the MapQTL session/run from which to retrieve
    the QTLs.
    """
    for exp in get_experiment_ids(session_id):
        infos = retrieve_exp_info(session_id, exp)
        if infos['mapqtl_session'] == int(mapqtl_session) and \
            infos['lod_threshold'] == float(lod_threshold):
            return exp
    return False


def generate_exp_id():
    """ Generate an experiment id using time.
    """
    output = "%s" % datetime.datetime.now()
    output = output.rsplit('.', 1)[0].strip()
    for char in [' ', ':', '.', '-']:
        output = output.replace(char, '')
    return output.strip()


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


def get_experiment_ids(session_id):
    """ Retrieve the experiment already run within this session.
    @param session_id the session identifier uniquely identifying the
    MapQTL zip file and the JoinMap map file. This is also the name of
    the folder in which are the different experiment
    """
    folder = os.path.join(UPLOAD_FOLDER, session_id)
    exp_ids = []
    for filename in os.listdir(folder):
        if os.path.isdir(os.path.join(folder, filename)) \
            and filename.startswith('20'):
            exp_ids.append(filename)
    return exp_ids


def retrieve_exp_info(session_id, exp_id):
    """ Retrieve the parameters used in the specified experiment.
    @param session_id the session identifier uniquely identifying the
    MapQTL zip file and the JoinMap map file. This is also the name of
    the folder in which are the different experiment
    @param exp_id the experiment identifier used to uniquely identify a
    run which may have specific parameters.
    """
    folder = os.path.join(UPLOAD_FOLDER, session_id, exp_id)
    config = ConfigParser.RawConfigParser()
    config.read('%s/exp.cfg' % folder)
    try:
        lod_threshold = config.getfloat('Parameters', 'LOD_threshold')
    except ValueError:
        lod_threshold = None
    except NoSectionError:
        lod_threshold = None
    except NoOptionError:
        lod_threshold = None
    try:
        mapqtl_session = config.getint('Parameters', 'MapQTL_session')
    except ValueError:
        mapqtl_session = None
    except NoSectionError:
        mapqtl_session = None
    except NoOptionError:
        mapqtl_session = None
    try:
        exp_id = config.getint('Parameters', 'Experiment_ID')
    except ValueError:
        exp_id = None
    except NoSectionError:
        exp_id = None
    except NoOptionError:
        exp_id = None
    return {'lod_threshold': lod_threshold,
            'mapqtl_session': mapqtl_session,
            'experiment_id': exp_id}


def retrieve_qtl_infos(session_id, exp_id):
    """ Retrieve the evolution of the number of QTLs per marker in
    the results of the experiment.
    @param session_id the session identifier uniquely identifying the
    MapQTL zip file and the JoinMap map file. This is also the name of
    the folder in which are the different experiment
    @param exp_id the experiment identifier used to uniquely identify a
    run which may have specific parameters.
    @return a tuple containing three elements.
    The first element is the qtls_evo list, containing for each marker
    the number of QTLs found.
    The second element is the qtls_lg, a list of all the different
    linkage group available.
    The third element is the lg_index, a list of the position at which
    the linkage group change.
    """
    folder = os.path.join(UPLOAD_FOLDER, session_id, exp_id)
    qtls_evo = []
    qtls_lg = []
    lg_index = []
    try:
        stream = open('%s/map_with_qtl.csv' % folder, 'r')
        lg = None
        cnt = 0
        for row in stream.readlines():
            print row
            row = row.split(',')
            if not lg:
                lg = row[1]
            if row[3].startswith('#'):
                continue
            else:
                qtls_evo.append(row[3].strip())
                print row[3]
            if lg != row[1]:
                lg_index.append(cnt)
                lg = None
            if row[1] not in qtls_lg:
                qtls_lg.append(row[1])
            cnt = cnt + 1
    except IOError:
        print 'No output in folder %s' % folder
    return (qtls_evo, qtls_lg, lg_index)


def run_mq2(session_id, lod_threshold, mapqtl_session):
    """ Run the scripts to extract the QTLs.
    @param session_id the session identifier uniquely identifying the
    MapQTL zip file and the JoinMap map file. The session identifier
    also uniquely identifies the folder in which are the files uploaded.
    @param lod_threshold the LOD threshold to use to consider a value
    significant for a QTL.
    @param mapqtl_session the MapQTL session/run from which to retrieve
    the QTLs.
    """
    folder = os.path.join(UPLOAD_FOLDER, session_id)
    already_done = experiment_done(session_id, lod_threshold, mapqtl_session)
    if already_done is not False:
        return already_done
    exp_id = generate_exp_id()
    exp_folder = os.path.join(folder, exp_id)
    if not os.path.exists(exp_folder):
        os.mkdir(exp_folder)

    write_down_config(os.path.join(folder, exp_id),
        lod_threshold,
        mapqtl_session,
        exp_id)
    tmp_folder = None
    no_matrix = False
    try:
        tmp_folder = set_tmp_folder()
        extract_zip(os.path.join(folder, 'input.zip'), tmp_folder)

        generate_map_from_mapqtl(inputfolder=tmp_folder,
                sessionid=mapqtl_session,
                outputfile=os.path.join(exp_folder, 'map.csv'))

        try:
            parse_mapqtl_file(inputfolder=tmp_folder,
                sessionid=mapqtl_session,
                lodthreshold=lod_threshold,
                qtl_outputfile=os.path.join(exp_folder, 'qtls.csv'),
                qtl_matrixfile=os.path.join(exp_folder, 'qtls_matrix.csv'))
        except MQ2NoMatrixException, err:
            print 'MQ2NoMatrixException: %s' % err
            no_matrix = err

        add_marker_to_qtls(qtlfile=os.path.join(exp_folder, 'qtls.csv'),
            mapfile=os.path.join(exp_folder, 'map.csv'),
            outputfile=os.path.join(exp_folder, 'qtls_with_mk.csv'))

        add_qtl_to_map(qtlfile=os.path.join(exp_folder, 'qtls_with_mk.csv'),
            mapfile=os.path.join(exp_folder, 'map.csv'),
            outputfile=os.path.join(exp_folder, 'map_with_qtl.csv'))
    except MQ2NoSuchSessionException, err:
        shutil.rmtree(exp_folder)
        raise MQ2NoSuchSessionException(err)
    finally:
        if tmp_folder and os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)
    if no_matrix is not False:
        raise MQ2NoMatrixException(no_matrix)


def write_down_config(folder, lod_threshold, mapqtl_session, exp_id):
    """ Write down the configuration used in an experiment.
    @param folder the folder in which to write down this configuration.
    @param lod_threshold the LOD threshold to use to consider a value
    significant for a QTL.
    @param mapqtl_session the MapQTL session/run from which to retrieve
    the QTLs.
    """
    config = ConfigParser.RawConfigParser()
    config.add_section('Parameters')
    config.set('Parameters', 'LOD_threshold', lod_threshold)
    config.set('Parameters', 'MapQTL_session', mapqtl_session)
    config.set('Parameters', 'Experiment_ID', exp_id)

    with open(os.path.join(folder, 'exp.cfg'), 'wb') as configfile:
        config.write(configfile)


##  Web-app


@APP.route('/', methods=['GET', 'POST'])
def index():
    """ Shows the front page.
    Fill the index.html template with the correct form to allow the user
    to upload his file and find back his session.
    """
    print 'mq2 %s -- %s -- %s' % (datetime.datetime.now(),
        request.remote_addr, request.url)
    form = UploadForm(csrf_enabled=False)
    session_form = SessionForm(csrf_enabled=False)
    if session_form.validate_on_submit()and session_form.session_id.data:
        return redirect(url_for('session',
            session_id=session_form.session_id.data))
    if form.validate_on_submit():
        upload_file = request.files['mapqtl_input']
        if upload_file and allowed_file(upload_file):
            session_id = generate_session_id()
            upload_folder = os.path.join(UPLOAD_FOLDER, session_id)
            os.mkdir(upload_folder)
            upload_file.save(os.path.join(upload_folder,
                'input.zip'))
            return redirect(url_for('session', session_id=session_id))
        else:
            flash('Wrong file type or name.')
    return render_template('index.html', form=form,
        session_form=session_form)


@APP.route('/session/<session_id>/', methods=['GET', 'POST'])
def session(session_id):
    """ Shows the session page.
    This page shows the different experiments ran on this session.
    A session being a MapQTL output zip file and a JoinMap map file,
    experiments are defined by the parameters used to find the QTLs
    within this MapQTL output.

    @param session_id the session identifier uniquely identifying the
    MapQTL zip file and the JoinMap map file.
    """
    print 'mq2 %s -- %s -- %s' % (datetime.datetime.now(),
        request.remote_addr, request.url)
    form = InputForm(csrf_enabled=False)
    if not session_id in os.listdir(UPLOAD_FOLDER):
        flash('This session does not exists')
        return redirect(url_for('index'))

    if form.validate_on_submit():
        lod_threshold = form.lod_threshold.data
        mapqtl_session = form.mapqtl_session.data
        output = None
        try:
            output = run_mq2(session_id, lod_threshold, mapqtl_session)
        except MQ2Exception, err:
            form.errors['MQ2'] = err
        if output:
            flash("Experiment already run in experiment: %s" % output)
    exp_ids = get_experiment_ids(session_id)
    return render_template('session.html', session_id=session_id,
        form=form, exp_ids=exp_ids)


@APP.route('/session/<session_id>/<exp_id>/')
def results(session_id, exp_id):
    """ Show the result page of an experiment.
    This page gives a quick overview of the QTL density along the map as
    well as the information about the parameters used for this
    experiment and access to the output files generated by our tool.

    @param session_id the session identifier uniquely identifying the
    MapQTL zip file and the JoinMap map file.
    @param exp_id the experiment identifier used to uniquely identify a
    run which may have specific parameters.
    """
    print 'mq2 %s -- %s -- %s' % (datetime.datetime.now(),
        request.remote_addr, request.url)
    if not session_id in os.listdir(UPLOAD_FOLDER):
        flash('This session does not exists')
        return redirect(url_for('index'))
    folder = os.path.join(UPLOAD_FOLDER, session_id)
    if not exp_id in os.listdir(folder):
        flash('This experiment does not exists')
        return redirect(url_for('session', session_id=session_id))
    infos = retrieve_exp_info(session_id, exp_id)
    (qtls_evo, qtls_lg, lg_index) = retrieve_qtl_infos(session_id, exp_id)
    qtls_evo = [float(it) for it in qtls_evo]
    max_qtls = 0
    if qtls_evo:
        max_qtls = max(qtls_evo) + 2
    date = '%s-%s-%s at %s:%s:%s' % (exp_id[:4], exp_id[4:6], exp_id[6:8],
        exp_id[8:10], exp_id[10:12], exp_id[12:14])
    files = os.listdir(os.path.join(folder, exp_id))
    files.remove(u'exp.cfg')
    return render_template('results.html', session_id=session_id,
        exp_id=exp_id, infos=infos, date=date,
        qtls_evo=qtls_evo, max_qtls=max_qtls,
        qtls_lg=qtls_lg, lg_index=lg_index,
        files=files)


@APP.route('/retrieve/<session_id>/<exp_id>/<filename>')
def retrieve(session_id, exp_id, filename):
    """ Retrieve the output file of an experiment.
    This method just returns you the direct file generated by our tool
    for a given experiment in a given session.

    @param session_id the session identifier uniquely identifying the
    MapQTL zip file and the JoinMap map file.
    @param exp_id the experiment identifier used to uniquely identify a
    run which may have specific parameters.
    @param filename the name of the file to retrieve within this session.
    """
    print 'mq2 %s -- %s -- %s' % (datetime.datetime.now(),
        request.remote_addr, request.url)
    upload_folder = os.path.join(UPLOAD_FOLDER, session_id, exp_id)
    if filename != 'zip':
        return send_from_directory(upload_folder, filename)
    else:
        if os.path.exists(os.path.join(upload_folder, '%s.zip' % exp_id)):
            return send_from_directory(upload_folder, '%s.zip' % exp_id)
        zf = zipfile.ZipFile(os.path.join(upload_folder, '%s.zip' % exp_id),
            mode='w')
        try:
            for filename in os.listdir(upload_folder):
                if not filename.endswith('.zip'):
                    zf.write(os.path.join(upload_folder, filename),
                        arcname=os.path.join(exp_id, filename),
                        compress_type=ZCOMPRESSION)
        except IOError, err:
            print 'ERROR while generating the zip file: %s' % err
        finally:
            zf.close()
        return send_from_directory(upload_folder, '%s.zip' % exp_id)


if __name__ == '__main__':
    APP.debug = True
    APP.run()