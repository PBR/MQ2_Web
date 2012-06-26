#!/usr/bin/python
#-*- coding: UTF-8 -*-

"""
 (c) Copyright Pierre-Yves Chibon -- 2011

 Distributed under License GPLv3 or later
 You can find a copy of this license on the website
 http://www.gnu.org/licenses/gpl.html

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY o201206241222063305291BYN5DLPX80A6DBr FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 MA 02110-1301, USA.
"""

import datetime
import os
import shutil
import tarfile
import tempfile
import zipfile


def read_input_file(filename, sep='\t'):
    """Reads a given inputfile (tab delimited) and returns a matrix
    (list of list).
    arg: filename, the complete path to the inputfile to read
    """
    output = []
    stream = None
    try:
        stream = open(filename, 'r')
        for row in stream:
            output.append(row.strip().split(sep))
    except Exception, err:
        print "Something wrong happend while reading the file %s " % filename
        print "ERROR: %s" % err
    finally:
        if stream:
            stream.close()
    return output


def get_qtls_from_mapqtl_data(matrix, threshold, inputfile):
    """Extract the QTLs found by MapQTL reading its file.
    This assume that there is only one QTL per linkage group.
    :arg matrix, the MapQTL file read in memory
    :arg threshold, threshold used to determine if a given LOD value is
    reflective the presence of a QTL.
    :arg inputfile, name of the inputfile in which the QTLs have been
    found
    """
    trait_name = inputfile.split(')_', 1)[1].split('.mqo')[0]
    qtls = []
    
    qtl = None
    for entry in matrix[1:]:
        if qtl is None:
            qtl = entry
        if qtl[1] != entry[1]:
            if float(qtl[4]) > float(threshold):
                qtl.insert(0, trait_name)
                qtls.append(qtl)
            qtl = None
            continue
        if entry[4] == '':
            entry[4] = 0
        if qtl[4] == '':
            qtl[4] = 0
        if float(entry[4]) > float(qtl[4]):
            qtl = entry

    if float(qtl[4]) > float(threshold):
        qtl.insert(0, trait_name)
        if qtl not in qtls:
            qtls.append(qtl)

    return qtls


def get_files_to_read(folder, sessionid):
    """ Reads a given folder and return all the files from MapQTL which
    are from the specified session and are of interest for us.
    So it looks for "Session <sessionid> (IM)_<exp>_<metabolite>.mqo" in
    all the files of the folder.
    :arg folder, path to the folder containing the data
    :arg sessionid, session given in the file name and present in the file
    name
    """
    filelist = []
    for root, dirs, files in os.walk(folder):
        for filename in files:
            if filename.startswith('Session %s' % sessionid) \
                and filename.endswith('.mqo'):
                filename = os.path.join(root, filename)
                filelist.append(filename)
    return filelist


def write_down_qtl_found(outputfile, qtls):
    """ Write down all the QTLs found in the specified inputfile to the
    specified outputfile.
    The name of the trait is extracted from the name of the inputfile, it
    is found between the 'IM)_' and '.mqo' of the filename.
    :arg outputfile, name of the outputfile in which the QTLs found are
    written.
    :arg qtls, the list of QTLs identified in the input file.
    """

    try:
        stream = open(outputfile, 'w')
        for qtl in qtls:
            stream.write('\t'.join(qtl) + '\n')
    except Exception, err:
        print 'An error occured while writing the QTLs to the file %s' \
        % outputfile
        print 'ERROR: %s' % err
    finally:
        stream.close()
    print 'Wrote QTLs in file %s' % outputfile


def set_tmp_folder():
    """ Create a temporary folder using the current time in which
    the zip can be extracted and which should be destroyed afterward.
    """
    output = "%s" % datetime.datetime.now()
    output = output.rsplit('.', 1)[0].strip()
    for char in [' ', ':', '.', '-']:
        output = output.replace(char, '')
    output.strip()
    tempfile.tempdir = '%s/%s' % (tempfile.gettempdir(), output)



def extract_zip(filename):
    """ Extract the sources in a temporary folder.
    :arg filename, name of the zip file containing the data from MapQTL
    which will be extracted
    """
    extract_dir = tempfile.gettempdir()
    print "Extracting %s in %s " % (filename, extract_dir)
    if not os.path.exists(extract_dir):
        try:
            os.mkdir(extract_dir)
        except IOError, err:
            print "Could not generate the folder %s" % extract_dir

    if zipfile.is_zipfile(filename):
        try:
            zfile = zipfile.ZipFile(filename, "r")
            zfile.extractall(extract_dir)
            zfile.close()
        except Exception, err:
            print "Error: %s" % err
    else:
        try:
            tar = tarfile.open(filename)
            tar.extractall(extract_dir)
            tar.close()
        except tarfile.ReadError, err:
            print "Error: %s" % err

    return extract_dir


def main(folder, sessionid, zipfile = None, lodthreshold=3,
        outputfile='qtls.csv'):
    """Main function.
    This function finds all the file fitting the pattern in the given
    folder, then these files are read and for each a list of QTLs is
    retrieved if their LOD value is above the lod threshold provided.

    :arg folder, the path to the folder to look into for the data file.
    :arg sessionid, the session ID from MapQTL containing the data, this
    is used to identy which files should be read.
    :kwarg zipfile, name of the zip file containing the data from MapQTL
    :kwarg lodthreshold, the LOD threshold from which we decide if we
    have a QTL.
    :kwarg outputfile, the name of the file in which the QTLs found in
    the data will be printed.
    """
    set_tmp_folder()
    inputfolder = None
    if zipfile is not None and os.path.exists(zipfile):
        inputfolder = extract_zip(zipfile)

    if inputfolder is not None:
        filelist = get_files_to_read(inputfolder, sessionid)
    else:
        filelist = get_files_to_read(folder, sessionid)
    if not filelist:
        return
    qtls = []
    matrix = read_input_file(filelist[0])
    headers = matrix[0]
    headers.insert(0, 'Trait_name')
    qtls.append(headers)
    for filename in filelist:
        matrix = read_input_file(filename)
        qtls.extend(get_qtls_from_mapqtl_data(matrix, lodthreshold, filename))
    print '- %s QTLs found in %s' % (len(qtls), filename)
    write_down_qtl_found(os.path.join(folder, outputfile), qtls)
    shutil.rmtree(tempfile.gettempdir())


if __name__ == '__main__':
    FOLDER = '/home/pierrey/Desktop/Yuni/'
    ZIP = FOLDER + 'YuniF2.zip'
    OUTPUT = 'QTL.csv'
    SESSION = 3
    LODTHRES = 3
    main(FOLDER, SESSION, zipfile=ZIP, lodthreshold=LODTHRES, 
        outputfile=OUTPUT)
