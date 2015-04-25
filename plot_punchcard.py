#!/usr/bin/env python
# Note:
# Originally written by guanqun (https://github.com/guanqun/) Sep 29, 2011
# Edited by Intrepid (https://github.com/intrepid/) Apr 12, 2012

import math
import cairo
import sys
import subprocess

# defaults
author = ''
width = 1100
output_file = 'output.png'

# if len(sys.argv) > 1:
#     if sys.argv[1] == "--help" or sys.argv[1] == "-h":
#         print("SYNTAX:    git punchchard")
#         print("EXAMPLE:   git punchchard file=outputfile.png width=4000")
#         print("This creates 'outputfile.png', a 4000px wide png image")
#         print()
#         sys.exit(0)

options =dict()

# if len(sys.argv) > 1:
#     options = dict(arg.split('=') for arg in sys.argv[1:])
# if options.has_key('width'):
#     width = int(options['width'])
# if options.has_key('author'):
#     author = options['author']
# if options.has_key('file'):
#     output_file = options["file"]

height = int(round(width/2.75, 0))

# Calculate the relative distance
distance = int(math.sqrt((width*height)/270.5))

# Round the distance to a number divisible by 2
if distance % 2 == 1:
    distance -= 1

max_range = (distance/2) ** 2

# Good values for the relative position
left = width/18 + 10  # The '+ 10' is to prevent text from overlapping 
top = height/20 + 10
indicator_length = height/20

days = ['Sat', 'Fri', 'Thu', 'Wed', 'Tue', 'Mon', 'Sun']
hours = ['12am'] + [str(x) for x in xrange(1, 12)] + ['12pm'] + [str(x) for x in xrange(1, 12)]
def get_x_y_from_date(day, hour):
    y = top + (days.index(day) + 1) * distance
    x = left + (int(hour) + 1) * distance
    return x, y

stats = {}
for d in days:
    stats[d] = {}
    for h in xrange(0, 24):
        stats[d][str(h)] = 0

total = 0
for x,y in all_tuples_dict:
    z = all_tuples_dict[(x,y)]
    total += z
    stats[str(x)][str(y)] = z

def get_length(nr):
    if nr == 0:
        return 0
    for i in xrange(1, distance/2):
        if i*i <= nr and nr < (i+1)*(i+1):
            return i
    if nr == max_range:
        return distance/2-1

# normalize
all_values = []
for d, hour_pair in stats.items():
    for h, value in hour_pair.items():
        all_values.append(value)

max_value = max(all_values)
final_data = []
for d, hour_pair in stats.items():
    for h, value in hour_pair.items():
        final_data.append( [ get_length(int( float(stats[d][h]) / max_value * max_range )), get_x_y_from_date(d, h) ] )

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
cr = cairo.Context(surface)

cr.set_line_width (1)

# draw background to white
cr.set_source_rgb(1, 1, 1)
cr.rectangle(0, 0, width, height)
cr.fill()

# set black
cr.set_source_rgb(0, 0, 0)

# draw x-axis and y-axis
cr.move_to(left, top)
cr.rel_line_to(0, 8 * distance)
cr.rel_line_to(25 * distance, 0)
cr.stroke()

# draw indicators on x-axis and y-axis
x, y = left, top
for i in xrange(8):
    cr.move_to(x, y)
    cr.rel_line_to(-indicator_length, 0)
    cr.stroke()
    y += distance

x += distance
for i in xrange(25):
    cr.move_to(x, y)
    cr.rel_line_to(0, indicator_length)
    cr.stroke()
    x += distance

# select font
cr.select_font_face ('sans-serif', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

# and set a appropriate font size
cr.set_font_size(math.sqrt((width*height)/3055.6))

# draw Mon, Sat, ... Sun on y-axis
x, y = (left - 5), (top + distance)
for i in xrange(7):
    x_bearing, y_bearing, width, height, x_advance, y_advance = cr.text_extents(days[i])
    cr.move_to(x - indicator_length - width, y + height/2)
    cr.show_text(days[i])
    y += distance

# draw 12am, 1, ... 11 on x-axis
x, y = (left + distance), (top + (7 + 1) * distance + 5)
for i in xrange(24):
    x_bearing, y_bearing, width, height, x_advance, y_advance = cr.text_extents(hours[i])
    cr.move_to(x - width/2 - x_bearing, y + indicator_length + height)
    cr.show_text(hours[i])
    x += distance

# draw circles according to their frequency
def draw_circle(pos, length):
    # find the position
    # max of length is half of the distance
    x, y = pos
    clr = (1 - float(length * length) / max_range )
    cr.set_source_rgba (clr, clr, clr)
    cr.move_to(x, y)
    cr.arc(x, y, length, 0, 2 * math.pi)
    cr.fill()

for each in final_data:
    draw_circle(each[1], each[0])



# write to output
surface.write_to_png (output_file)

