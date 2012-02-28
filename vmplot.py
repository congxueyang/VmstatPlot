#!/usr/bin/python
# vmplot.py

#  Generate gnuplot(1) graphs from vmstat(1) output.
#  Copyright (C) 2008  KELEMEN Peter
#  Copyright (C) 2012  Bjarni R. Einarsson
#  
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import optparse
import fileinput
import tempfile
import time

iocols = ['bi', 'bo']   # this might be Linux-specific...
index = {}      # index of columns corresponding to header fields
sums = {}       # sum of columns corresponding to header fields in iocols
pcnts = {}      # count of positive values corresponding to header fields in iocols
avgs = {}       # average of columns corresponding to header fields in iocols
lc = 0          # line count

def build_column_index(x):
    for i in xrange(len(x)):
        index[x[i]] = i
        sums[x[i]] = 0
        pcnts[x[i]] = 0
    for i in iocols:
        if i not in x:
            print 'What you gave me does not seem to be vmstat(1) output, exiting.'
            sys.exit(10)
    print "column index built at line", lc

parser = optparse.OptionParser()
parser.add_option("-t", "--title", default=os.path.basename(os.getcwd()), help="graph title")
parser.add_option("-e", "--email", default=None, help="graph author email address")
parser.add_option("-k", "--kilobytes", default=0, help="throughput axis scale")
parser.add_option("-m", "--ram", default=4096, help="megabytes of RAM available")
parser.add_option("-s", "--size", default=7200, help="number of data points")
parser.add_option("-p", "--postscript", action="store_true", default=False, help="additional PostScript graph output")
parser.add_option("-r", "--retain", action="store_true", default=False, help="retain temporary files")
parser.add_option("-4", "--slc4", action="store_true", default=False, help="SLC4 (gnuplot 4.0) compatibility")
(options, args) = parser.parse_args()

print "option: title =", options.title
print "option: email =", options.email

try:
    options.size = int(options.size)
except:
    print "E: Invalid number. (%s)" % options.size
    sys.exit(1)
print "option: size =", options.size

try:
    options.ram = int(options.ram)
except:
    print "E: Invalid number. (%s)" % options.ram
    sys.exit(1)
print "option: ram =", options.ram

try:
    options.kilobytes = int(options.kilobytes)
except:
    print "E: Invalid number. (%s)" % options.kilobytes
    sys.exit(1)
print "option: kilobytes =", options.kilobytes

print "option: postscript =", options.postscript

vmstat = tempfile.mkstemp('.tmp', 'vmplot-vmstat-')
if options.retain:
    print "sanitized vmstat file:", vmstat[1]

for line in fileinput.input(args):
    if 'procs' in line:
        continue
    cols = line.split()
    if not index and 'free' in cols:
        build_column_index(cols)
        continue
    if cols[1].isdigit():
        skip = False
        for i in iocols:
            if cols[index[i]].isdigit():
                x = int(cols[index[i]])
                if x == 0:
                    continue
                if x < 10**9:   # skip vmstat(1) overflow errors
                    sums[i] = sums[i] + x
                    pcnts[i] = pcnts[i] + 1
                else:
                    print x, "too large, skipping"
                    skip = True
            else:
                print '%s:%u: column %u is garbled: "%s", skipping' % (
                fileinput.filename(),
                fileinput.filelineno(),
                index[i],
                cols[index[i]])
                skip = True
        if not skip:
            if len(cols) > 18 and (lc % int(options.size/5)) != 0:
              line = line.replace(cols[18], '').replace(cols[17], '')
            os.write(vmstat[0], line)
            lc += 1

os.close(vmstat[0])

for i in iocols:
    avgs[i] = sums[i] / pcnts[i]
    print "%s: SUM=%d AVG=%d CNT=%d" % (i, sums[i], avgs[i], pcnts[i])

options.label = time.strftime("%F %T", time.localtime())
if options.email:
    options.label = options.email + ' ' + options.label

plot = []
if options.slc4:
    plot.append('set terminal png small;')
    plot.append('set size 1.6,1.0;')
else:
    plot.append('set terminal png small size 1024,480 ;')
    plot.append('set label "%s" front offset -11,-2.5 ;' % (options.label))
plot.append('set output "%s.png";' % options.title)
plot.append('set title "%s";' % options.title)
plot.append('set key below;')
plot.append('set xlabel "Time";')
plot.append('set y2label "I/O (KB/s)";')
plot.append('set y2tics nomirror;')
if options.kilobytes: plot.append('set y2range [0:%d];' % options.kilobytes)
plot.append('set yrange [0:103];')
plot.append('set ylabel "Memory/CPU utilization (%)";')
plot.append('set ytics 20;')
plot.append('set grid linetype 0;')
plot.append('plot ')
plot.append('"%s" using 19:xtic(19) axis x1y2 title "t",' % vmstat[1])
plot.append('"%s" using 0:10 title "io:in" axis x1y2 smooth bezier lt 1 lw 2,' % vmstat[1])
plot.append('"%s" using 0:9 title "io:out" axis x1y2 smooth bezier lt 5 lw 2,' % vmstat[1])
plot.append('"%s" using 0:13 title "cpu:user" smooth bezier lt 3 lw 1,' % vmstat[1])
plot.append('"%s" using 0:14 title "cpu:sys" smooth bezier lt 4 lw 1,' % vmstat[1])
plot.append('"%s" using 0:15 title "cpu:idle" smooth bezier lt 2 lw 2,' % vmstat[1])
plot.append('"%s" using 0:($4/%d) title "mem:free" smooth bezier lt 6 lw 2,' % (vmstat[1], 10*options.ram))
plot.append('"%s" using 0:($5/%d) title "mem:buff" smooth bezier lt 7 lw 1,' % (vmstat[1], 10*options.ram))
plot.append('"%s" using 0:($6/%d) title "mem:cache" smooth bezier lt 8 lw 1,' % (vmstat[1], 10*options.ram))
plot.append('"%s" using 0:($3/%d) title "mem:swapped" smooth bezier lt 9 lw 2' % (vmstat[1], 10*options.ram))
if options.postscript:
    plot.append('set terminal postscript color landscape small;')
    plot.append('set size 1.0,1.0;')
    plot.append('set output "%s.ps";' % options.title)
    plot.append('replot;')

gnuplot = tempfile.mkstemp('.tmp', 'vmplot-gnuplot-')
if options.retain:
    print "gnuplot command file:", gnuplot[1]
os.write(gnuplot[0], '\\\n'.join(plot))
os.close(gnuplot[0])

os.system('gnuplot %s' % gnuplot[1])

if not options.retain:
    os.remove(vmstat[1])
    os.remove(gnuplot[1])

# End of file.