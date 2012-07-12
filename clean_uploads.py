#!/usr/bin/python
#-*- coding: UTF-8 -*-

"""
 (c) 2011, 2012 - Copyright Pierre-Yves Chibon

 Distributed under License GPLv3 or later
 You can find a copy of this license on the website
 http://www.gnu.org/licenses/gpl.html

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 MA 02110-1301, USA.

Script to clean the upload folder from the session folders.
"""


import ConfigParser
import datetime
import logging
import os
import shutil
import time

from optparse import OptionParser


LIMIT = 7
logging.basicConfig()
LOG = logging.getLogger('clean_uploads')


## {{{ http://code.activestate.com/recipes/577135/ (r2)
def _datetime_from_str(time_str):
    """Return (<scope>, <datetime.datetime() instance>) for the given
    datetime string.
    
    >>> _datetime_from_str("2009")
    ('year', datetime.datetime(2009, 1, 1, 0, 0))
    >>> _datetime_from_str("2009-12")
    ('month', datetime.datetime(2009, 12, 1, 0, 0))
    >>> _datetime_from_str("2009-12-25")
    ('day', datetime.datetime(2009, 12, 25, 0, 0))
    >>> _datetime_from_str("2009-12-25 13")
    ('hour', datetime.datetime(2009, 12, 25, 13, 0))
    >>> _datetime_from_str("2009-12-25 13:05")
    ('minute', datetime.datetime(2009, 12, 25, 13, 5))
    >>> _datetime_from_str("2009-12-25 13:05:14")
    ('second', datetime.datetime(2009, 12, 25, 13, 5, 14))
    >>> _datetime_from_str("2009-12-25 13:05:14.453728")
    ('microsecond', datetime.datetime(2009, 12, 25, 13, 5, 14, 453728))
    """
    formats = [
        # <scope>, <format>
        ("year", "%Y"),
        ("month", "%Y-%m"),
        ("day", "%Y-%m-%d"),
        ("hour", "%Y-%m-%d %H"),
        ("minute", "%Y-%m-%d %H:%M"),
        ("second", "%Y-%m-%d %H:%M:%S"),
        # ".<microsecond>" at end is manually handled below
        ("microsecond", "%Y-%m-%d %H:%M:%S"),
    ]
    for scope, form in formats:
        if scope == "microsecond":
            # Special handling for microsecond part. AFAIK there isn't a
            # strftime code for this.
            if time_str.count('.') != 1:
                continue
            time_str, microseconds_str = time_str.split('.')
            try:
                microsecond = int((microseconds_str + '000000')[:6])
            except ValueError:
                continue
        try:
            # This comment here is the modern way. The subsequent two
            # lines are for Python 2.4 support.
            #t = datetime.datetime.strptime(time_str, form)
            t_tuple = time.strptime(time_str, form)
            date_obj = datetime.datetime(*t_tuple[:6])
        except ValueError:
            pass
        else:
            if scope == "microsecond":
                date_obj = date_obj.replace(microsecond=microsecond)
            return scope, date_obj
    else:
        raise ValueError("could not determine date from %r: does not "
            "match any of the accepted patterns ('%s')"
            % (time_str, "', '".join(s for s, p, f in formats)))
## end of http://code.activestate.com/recipes/577135/ }}}


def parse_arguments():
    """ Parse the command line arguments.
    """
    usage = "usage: %prog [options] path/to/config/file"
    parser = OptionParser(usage)
    parser.add_option("-v", '--verbose', 
                  action="store_true", dest="verbose", default=False,
                  help="Increase the verbosity of the output")
    parser.add_option("-t", '--test', 
                  action="store_true", dest="test", default=False,
                  help="Increase the verbosity and just perform a test "\
                  "run without touching any files.")
    return parser.parse_args()


def main():
    """ Main function.
    Browse the given folder, determine based on the name how old the
    last analysis is and whether the folder is older than X days or not.
    """
    options = parse_arguments()[0]

    # Do all the checks regarding the input provided
    if options.verbose:
        LOG.setLevel(logging.DEBUG)
    config_file = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'mq2.cfg')
    if not os.path.exists(config_file):
        print 'The provided config file does not exist: %s' % config_file
        return

    config = ConfigParser.ConfigParser()
    config.readfp(open(config_file))
    folder = config.get('mq2', 'upload_folder')

    LOG.info('Folder: %s' % folder)
    today = datetime.datetime.today()
    to_clean = []
    for filename in os.listdir(folder):
        # This is the folder with all the sessions
        if os.path.isdir(os.path.join(folder, filename)):
            string = '%s-%s-%s' % (filename[:4], filename[4:6],
                filename[6:8])
            session_date = _datetime_from_str(string)[1]
            delta = today - session_date
            if delta.days > LIMIT:
                LOG.info('Session %s is above limit' % filename)
                to_keep = False
                for sub_filename in os.listdir(os.path.join(folder,
                    filename)):
                    # This is the folder with all the experiment within
                    # a session
                    if os.path.isdir(os.path.join(folder, filename,
                        sub_filename)):
                        string = '%s-%s-%s' % (sub_filename[:4],
                            sub_filename[4:6], sub_filename[6:8])
                        exp_date = _datetime_from_str(string)[1]
                        delta = today - exp_date
                        if delta.days < LIMIT:
                            LOG.info('Experiment %s is to keep' % (
                                sub_filename))
                            to_keep = True
                            break
                if not to_keep:
                    LOG.info('Session %s is to be cleaned' % filename)
                    to_clean.append(os.path.join(folder, filename))

    sample_session = os.path.join(folder,
        config.get('mq2', 'sample_session'))
    if sample_session in to_clean:
        LOG.info('Save the sample session: %s' % sample_session)
        to_clean.remove(sample_session)

    if not to_clean:
        LOG.info('No old sessions, nothing to remove')

    for filename in to_clean:
        if not options.test:
            shutil.rmtree(filename)
        else:
            print 'To remove: %s' % filename


if __name__ == '__main__':
    main()
