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
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
 MA 02110-1301, USA.
"""


def transform_loc_map(inputfile):
    """Transform the loc map into a CSV file.
    :arg inputfile, the name of the inputfile containing the map to
    transform.
    """
    genetic_map = []
    stream = None
    try:
        stream = open(inputfile, 'r')
        group = None
        for row in stream:
            if row.strip() and not row.startswith(';'):
                row = row.strip()
                content = row.split(' ')
                content = [ent for ent in content if ent]
                if row.startswith('group'):
                    group = content[1]
                else:
                    content.insert(1, group)
                    genetic_map.append(content)
    except Exception, err:
        print "Something wrong happend while reading the file %s " % inputfile
        print "ERROR: %s" % err
    finally:
        if stream:
            stream.close()
    return genetic_map


def write_down_map(outputfile, genetic_map):
    """Write down the genetic map as CSV format into the given outputfile.
    :arg outputfile, the name of the file in which the map will be written.
    :arg genetic_map, the CSV version of the genetic map read.
    """
    try:
        stream = open(outputfile, 'w')
    except Exception, err:
        print 'Could not open the file %s to write in' % outputfile
        print 'ERROR: %s' % err

    try:
        stream.write("Marker, Linkage group, Position\n")
        for entry in genetic_map:
            stream.write(','.join(entry) + "\n")
    except Exception, err:
        print 'An error occured while writing the map to the file %s' \
        % outputfile
        print 'ERROR: %s' % err
    finally:
        stream.close()
    print 'Wrote genetic map in file %s' % outputfile


def main(folder, inputfile, outputfile='map.csv'):
    """Main function.
    This function transform the map file into a csv file.

    :arg inpufile, the map file from MapQTL to be transformed to csv.
    :kwarg outputfile, the name of the output file in which the map will
    be written.
    """
    genetic_map = transform_loc_map('%s/%s' % (folder, inputfile))
    print '- %s markers found in %s' % (len(genetic_map), inputfile)
    write_down_map('%s/%s' % (folder, outputfile), genetic_map)


if __name__ == '__main__':
    FOLDER = '/home/pierrey/Desktop/Yuni/'
    INPUT = FOLDER + 'YuniF2.map'
    OUTPUT = 'YuniF2map.csv'
    main(FOLDER, inputfile=INPUT, outputfile=OUTPUT)
