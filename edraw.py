#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
VERSION
-------
version 2 of edraw inkscape extension

AUTHOR
------
Lukas Geiling, 2020

LICENSE
-------
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

TODO
------
* testing
* program documentation
* interpolation of arc segments
* handling holes in paths, several 'm' or 'M' commands in path d attribute
* handling text
* flatten transformations
'''

import inkex
import datetime as dt
import re
import ntpath

try:
	import numpy as np
except:
	inkex.errormsg('Could not import the mighty numpy library. Please check if the right version of numpy is installed correctly.')
try:
	from lxml import etree
except:
	inkex.errormsg('Could not import the lxml library. Please check if the right version of lxml is installed correctly.')

ns = {
u'sodipodi' :u'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
u'cc'	    :u'http://creativecommons.org/ns#',
u'ccOLD'	:u'http://web.resource.org/cc/',
u'svg'	    :u'http://www.w3.org/2000/svg',
u'dc'	    :u'http://purl.org/dc/elements/1.1/',
u'rdf'	    :u'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
u'inkscape' :u'http://www.inkscape.org/namespaces/inkscape',
u'xlink'	:u'http://www.w3.org/1999/xlink',
u'xml'	    :u'http://www.w3.org/XML/1998/namespace'
}

def path_leaf(path):
	'''
	Function that will return full filename from a complete path (absolute or relative).
	
	Parameters
	----------
	path : str
		full path (absolute or relative) including the full filename (name.filesuffix)
    
    Returns
	-------
	str
		full filename including filesuffix
	'''
	head, tail = ntpath.split(path)
	return tail or ntpath.basename(head)


def get_opt_attrib(element, attrib, alt_attrib_val):
	'''
	Function that return the attribute of an xml element if this attribute exists, otherwise return a given value.
	
	Parameters
	----------
	element : xml element
		element for trying to get attribute
	attrib : str
		name of the attribute
	alt_attrib_val
		alternative value if attribute of elemet does not exist
    
    Returns
	-------
	attrib_val
		value of attribute or alternative value
	'''
	try:
		attrib_val = element.attrib[attrib]
	except:
		attrib_val = alt_attrib_val
	return(attrib_val)
	
def get_layer_attribs(svg_layer, color):
	'''
	Function that will determine the properties of a svg layer and return these properties as an array.
	
	Parameters
	----------
	svg_layer : xml element
		xml element of a svg layer (no group)
	color : str
		the color which should be assigned to the layer. Format is in hex #RRGGBBAA
    
    Returns
	-------
	array : str
		the layer properties as array
		array[0] : layer name
		array[1] : hiding state of layer
		array[2] : locking state of layer
		array[3] : color of layer in hex #RRGGBB
		array[4] : alpha of the layer in range [0.,1.]
	'''
	name = svg_layer.attrib['{{{inkscape}}}label'.format(**ns)]
	# get layer visibility
	hidden = get_opt_attrib(svg_layer, 'style', 'false')
	if hidden =='display:inline':
		hidden = 'true'
	else:
		hidden = 'false'
	# get layer lock state
	locked = get_opt_attrib(svg_layer, '{{{sodipodi}}}insensitive'.format(**ns), 'false')
	colorRGB = color[:7]
	alpha = int(color[-2:],16)/255.#int(color[-2:], 16)/1000.
	return([name, hidden, locked, colorRGB, alpha])

def color_string2color_list(color_string):
	'''
	Function that finds all hex color in a string and returns them as an array of hex format #RRGGBBAA colors. If color contains just RGB values an alpha value of FF will be appended to color string.
	
	Parameters
	----------
	color_string : str
		string containing alls colors
    
    Returns
	-------
	color_list : list
		list of all colors in hex #RRGGBBAA format
	'''
	color_list = re.findall(r'#[0-9A-Fa-f]{8}|#[0-9A-Fa-f]{6}', color_string.upper())
	for i, c in enumerate(color_list):
		if len(c)==7:
			color_list[i] = c + 'FF'
	return(color_list)
	
def rgba_conv(color):
	'''
	Function that will convert an color as array in rgba values to hex #RRGGBBAA format-
	
	Parameters
	----------
	color : list
		list of rgb values in range 0 to 255 and alpha value in range 0 to 1
    
    Returns
	-------
	rgba : str
		color in #RRGGBBAA format
	'''
	rgba = '#{:02x}{:02x}{:02x}'.format(color[0],color[1],color[2])
	if len(color)==3:
		rgba += 'FF'
	else:
		rgba += '{:02x}'.format(int(color[3]*100))
	return(rgba)
	
def get_outl(sty):
	'''
	Function that checks if the style string has an stroke or is filled.
	
	Parameters
	----------
	sty : str
		style string of an svg element
    
    Returns
	-------
	outl : str
		the element meant as outline or shape 'true' or 'false'
	'''
	sty_fill = re.search('fill:(.+?);', sty).group(1)
	if sty_fill != 'none':
	   outl = 'false'
	else:
	   outl = 'true'
	return(outl)
	
def gen_style(old_sty, layer_color, layer_alpha):
	'''
	Function that generates a style from svg element and determine if element is shape or outline.
	
	Parameters
	----------
	old_sty : str
		style string of an svg element
	layer_color : str
		color to be uses for new style
	layer_alpha : float
		alpha to be used for new style
	
    Returns
	-------
	new_sty : str
		new style string to apply on svg element
	outl : str
		is element shape or outline ('false' or 'true')
	'''
	sty_fill = re.search('fill:(.+?);', old_sty).group(1)
	#sty_stroke = re.search('stroke:(.+?);', old_sty).group(1)
	if sty_fill != 'none':
	   new_sty = 'fill:{};stroke:none;opacity:{}'.format(layer_color,layer_alpha)
	   outl = 'false'
	else:
	   new_sty = 'fill:none;stroke:{};stroke-width:1;opacity:{}'.format(layer_color,layer_alpha)
	   outl = 'true'
	return(new_sty, outl)
	
def area_fast_rect(x,y):
	'''
	Function for determing scanning direction
	
	Parameters
	----------
	x : str
		width
	y: str
		height
	
    Returns
	-------
	str
		return '0 deg' if x>=y , otherwise '90 deg'
	'''
	if float(x)>=float(y):
		return('0 deg')
	else:
		return('90 deg')
		
def area_fast_path(points):
	'''
	Function that calculates scanning direction from 2 points
	
	Parameters
	----------
	x : list
		array of N points [x_1,y_1,x_2,y_2,...,x_N,y_N]
	
    Returns
	-------
	str
		return scanning direction in degrees
	'''
	if len(points)<4:
		inkex.errormsg('Path consists of less than 2 points. The angle can not be calculated and is set to 0 deg.')
		return('0 deg')
	else:
		if (points[2]-points[0])!=0:
			tan = (points[3]-points[1])/(points[2]-points[0])
			return('{:.0f} deg'.format(np.rad2deg(np.arctan(tan))))
		else:
			return('90 deg')
		
def cubic_bezier(cubic_bezier, t):
	'''
	Function that evaluate a cubic bezier curve at t.
	
	Parameters
	----------
	cubic_bezier : svg.path.CubicBezier
		startpoint, controlpoint1, controlpoint2, endpoint of Cubic Bezier path
	t : float
		wherer to evaluate cubic bezier. For 0<=t<=1 the evaluation point will be on the path.
	
    Returns
	-------
	complex
		evaluated point of cubic bezier
	
	Note
	----
	see https://en.wikipedia.org/wiki/B%C3%A9zier_curve#Cubic_B%C3%A9zier_curves for formula
	'''
	b0 = cubic_bezier[1][0]
	b1 = cubic_bezier[1][1]
	b2 = cubic_bezier[1][2]
	b3 = cubic_bezier[1][3]
	return((-b0+3*b1-3*b2+b3)*t**3+(3*b0-6*b1+3*b2)*t**2 + (-3*b0+3*b1)*t + b0)
	
def quadratic_bezier(quadratic_bezier, t):
	'''
	Function that evaluate a quadratic bezier curve at t.
	
	Parameters
	----------
	quadratic_bezier : svg.path.QuadraticBezier
		startpoint, controlpoint, endpoint of quadratic Bezier path
	t : float
		wherer to evaluate quadratic bezier. For 0<=t<=1 the evaluation point will be on the path.
	
    Returns
	-------
	complex
		evaluated point of quadratic bezier
	
	Note
	----
	see https://en.wikipedia.org/wiki/B%C3%A9zier_curve#Quadratic_B%C3%A9zier_curves for formula
	'''
	b0 = quadratic_bezier[1][0]
	b1 = quadratic_bezier[1][1]
	b2 = quadratic_bezier[1][2]
	return((b0-2*b1+b2)*t**2 + (-2*b0+2*b1)*t + b0)
	
def interpolate_curved_path(path, n=3):
	'''
	Function that interpolate a cubic bezier or quadratic bezier curve at n sampling points
	
	Parameters
	----------
	pyth : svg.path type
		path which should be interpolated
	n : int, optional
		points at [0, 1/N, 2/N, ..., (N-1)/N]
	
    Returns
	-------
	points : list
		array of complex numbers representing x and y value respectivly
	'''
	samples = np.linspace(1/n,1,n,endpoint=True)
	points = []
	if path[0]=='C':
		func = cubic_bezier
	elif path[0]=='Q':
		func = quadratic_bezier
	for t in samples:
		point = func(path, t)
		points.append(point)
	return(points)
	
def create_ely_tree(filename, grid):
	'''
	Function for creating xml tree of the raw ely file structure
	
	Parameters
	----------
	filename : str
		filename of ely file without suffix
	grid : list
		list of grid parameters
		grid[0] : horizontal spacing
		grid[1] : vertical spacing
		grid[2] : visibility
		grid[3] : snapping
	
    Returns
	-------
	elayout : xml tree
		raw XML tree of ely file
	'''
	str_timestamp = dt.datetime.now().strftime('%d.%m.%Y %H:%M:%S')
	elayout = etree.Element('ELAYOUT', locked='false', name=filename, version='1.0')
	version = etree.SubElement(elayout, 'VERSION', created=str_timestamp, modified=str_timestamp, number='1.0')
	grid= etree.SubElement(elayout, 'GRID', horizontal=grid[0], show=grid[2], snap_to=grid[3], vertical=grid[1])
	layer_list = etree.SubElement(elayout, 'LAYER_LIST')
	structure_list = etree.SubElement(elayout, 'STRUCTURE_LIST')
	structure = etree.SubElement(structure_list, 'STRUCTURE', locked='false', name='Structure')
	version_lev4 = etree.SubElement(structure, 'VERSION', created=str_timestamp, modified=str_timestamp, number='1.0')
	instance_list = etree.SubElement(structure, 'INSTANCE_LIST')
	return(etree.ElementTree(elayout))
	


class edraw(inkex.EffectExtension):
	
	def add_arguments(self, pars):
		'''
		Parsing the arguments from inkscape extension
		'''
		pars.add_argument('--tab')
		pars.add_argument('--dir_file', type=str, default='~/drawing.ely', help='Complete path and file name for output file')
		
		pars.add_argument('--apply_on_svg', type=inkex.Boolean, default=False, help='Apply apeareance like in ely file to drawing')
		#pars.add_argument('--flat_trans', type=inkex.Boolean, default=False, help='Try to flatten transformations')
		pars.add_argument('--calc_rot', type=inkex.Boolean, default=False, help='Calculate scanning direction of polygons by first two points')
		pars.add_argument('--num_int_points', type=int, default=10, help='Number of points for interpolation of curved path segment')
		
		pars.add_argument('--color_cycle', type=str, default='default', help='which type of color cycle should be used')
		pars.add_argument('--color_string', type=str, default='#1F77B47F, #FF7F0E7F, #2CA02C7F, #D627287F, #9467BD7F, #8C564B7F, #E377C27F, #7F7F7F7F, #BCBD227F, #17BECF7F', help='text string for colors in #rgb or #rgba notation')
		
		pars.add_argument('-c1', '--col1', type=inkex.Color, default=inkex.Color('#1F77B4FF'), help='Color of Layer 1')
		pars.add_argument('-c2', '--col2', type=inkex.Color, default=inkex.Color('#1F77B4FF'), help='Color of Layer 2')
		pars.add_argument('-c3', '--col3', type=inkex.Color, default=inkex.Color('#1F77B4FF'), help='Color of Layer 3')
		pars.add_argument('-c4', '--col4', type=inkex.Color, default=inkex.Color('#1F77B4FF'), help='Color of Layer 4')
		pars.add_argument('-c5', '--col5', type=inkex.Color, default=inkex.Color('#1F77B4FF'), help='Color of Layer 5')
		

	
	def get_grid(self):
		'''
		Function for getting grid properties
		'''
		try:
			grid = self.svg.xpath('//inkscape:grid')[0]
		except:
			grid = None
		namedview = self.svg.xpath('//sodipodi:namedview')[0]
		g_xdist = get_opt_attrib(grid, 'spacingx', '1')
		g_ydist = get_opt_attrib(grid, 'spacingy', '1')
		g_vis = get_opt_attrib(grid, 'visible', 'true')
		g_snap = get_opt_attrib(namedview, '{{{inkscape}}}snap-grids'.format(**ns), 'true')
		return([g_xdist,g_ydist,g_vis,g_snap])
		
	def get_size(self):
		'''
		Function for size property of document
		'''
		return(max(self.svg.height,self.svg.width))
		
	def effect(self):
		'''
		--- the actual extension ---
		This method will iterate of all svg layers and their elements and parsing them to an .ely file. The apperance of inkscape document will be adapted respectively
		'''
		num_int_points = self.options.num_int_points
		apply_on_svg = self.options.apply_on_svg
		calc_rot = self.options.calc_rot
		
		ep_directory = self.options.dir_file
		
		filename = path_leaf(ep_directory)
		size = self.get_size()
		if apply_on_svg:
			unit = self.svg.attrib['height'][-2:]
			self.svg.attrib['height'] = '{}{}'.format(size,unit)
			self.svg.attrib['width'] = '{}{}'.format(size,unit)
		else:
			pass
		ely_xml = create_ely_tree(filename.split('.')[0],self.get_grid())
		ely_layer_list = ely_xml.xpath('//LAYER_LIST')[0]
		ely_structure = ely_xml.xpath('//STRUCTURE')[0]
		
		svg_layer_list = self.svg.xpath('//svg:g[@inkscape:label]')
		
		color_cycle_type = self.options.color_cycle
		if color_cycle_type == 'default':
			color_cycle = ['#1F77B47F', '#FF7F0E7F', '#2CA02C7F', '#D627287F', '#9467BD7F', '#8C564B7F', '#E377C27F', '#7F7F7F7F', '#BCBD227F', '#17BECF7F']
		elif color_cycle_type == 'string':
			color_cycle = color_string2color_list(self.options.color_string)
		elif color_cycle_type == 'custom':
			color_cycle = []
			for c in [self.options.col1[:], self.options.col2[:], self.options.col3[:], self.options.col4[:], self.options.col5[:]]:
				color_cycle.append(rgba_conv(c))
		
		for i, svg_layer in enumerate(svg_layer_list):
			layer_color = color_cycle[i % len(color_cycle)]
			svg_layer_attribs = get_layer_attribs(svg_layer, layer_color)
			ely_layer = etree.SubElement(ely_layer_list, 'LAYER', fill_color=svg_layer_attribs[3], fill_opacity=str(svg_layer_attribs[4]), hidden=svg_layer_attribs[1], locked=svg_layer_attribs[2], name=svg_layer_attribs[0])
			ely_layer_reference = etree.SubElement(ely_structure, 'LAYER_REFERENCE', frame_cx=str(size/2.), frame_cy=str(size/2.), frame_size=str(size), ref=svg_layer_attribs[0])
			
			svg_rects = svg_layer.findall('.//svg:rect')
			svg_ellipses = svg_layer.findall('.//svg:ellipse')
			svg_circles = svg_layer.findall('.//svg:circle')
			svg_paths = svg_layer.xpath('.//svg:path[@d]')
			for svg_rect in svg_rects:
				x, y, h, w, s = [svg_rect.attrib[atr] for atr in ['x','y','height','width','style']]
				ns, o = gen_style(s, svg_layer_attribs[3], svg_layer_attribs[4])
				a = area_fast_rect(w,h)
				etree.SubElement(ely_layer_reference, 'RECT', outline=o, area_fast=a, height=h, width=w, x=x, y=y)
				if apply_on_svg:
					svg_rect.attrib['style'] = ns
				
			for svg_ellipse in svg_ellipses:
				rx, ry, cx, cy, s = [svg_ellipse.attrib[atr] for atr in ['rx','ry','cx','cy','style']]
				ns, o = gen_style(s, svg_layer_attribs[3], svg_layer_attribs[4])
				a = area_fast_rect(rx,ry)
				etree.SubElement(ely_layer_reference, 'ELLIPSE', outline=o, area_fast=a, rx=rx, ry=ry, cx=cx, cy=cy)
				if apply_on_svg:
					svg_ellipse.attrib['style'] = ns
				
			for svg_circle in svg_circles:
				r, cx, cy, s = [svg_circle.attrib[atr] for atr in ['r','cx','cy','style']]
				ns, o = gen_style(s, svg_layer_attribs[3], svg_layer_attribs[4])
				a = '0 deg'
				etree.SubElement(ely_layer_reference, 'CIRCLE', outline=o, area_fast=a, cx=cx, cy=cy, r=r)
				if apply_on_svg:
					svg_circle.attrib['style'] = ns
				
			for svg_path in svg_paths:
				d, s = [svg_path.attrib[atr] for atr in ['d','style']]
				segs = svg_path.path.to_arrays()
							
				PP = 0j
				CC = 0j
				newp = ''
				points2 = ''
				
				for i in range(len(segs)):
					if segs[i][0] == 'M':
						PP = complex(segs[i][1][0],segs[i][1][1])
						newp += 'M {:f},{:f}'.format(PP.real,PP.imag)
						points2 += '({:.3f} {:.3f})'.format(PP.real,PP.imag)
					elif segs[i][0] == 'L':
						PP = complex(segs[i][1][0],segs[i][1][1])
						newp += ' L {:f},{:f}'.format(PP.real,PP.imag)
						points2 += ' ({:.3f} {:.3f})'.format(PP.real,PP.imag)
					elif segs[i][0] == 'H':
						PP = complex(segs[i][1][0],PP.imag)
						newp += ' L {:f},{:f}'.format(PP.real,PP.imag)
						points2 += ' ({:.3f} {:.3f})'.format(PP.real,PP.imag)
					elif segs[i][0] == 'V':
						PP = complex(PP.real,segs[i][1][0])
						newp += ' L {:f},{:f}'.format(PP.real,PP.imag)
						points2 += ' ({:.3f} {:.3f})'.format(PP.real,PP.imag)
					elif segs[i][0] == 'C':
						seg_s = PP
						seg_c1 = segs[i][1][0]+segs[i][1][1]*1j
						CC = complex(segs[i][1][2],segs[i][1][3])
						seg_c2 = CC
						PP = complex(segs[i][1][4],segs[i][1][5])
						seg_e = PP
						ipoints = interpolate_curved_path(['C',[seg_s,seg_c1,seg_c2,seg_e]], n=num_int_points)
						newp += ' L '+' L '.join(['{:f},{:f}'.format(x.real, x.imag) for x in ipoints])
						points2 += ' '+' '.join(['({:.3f} {:.3f})'.format(x.real, x.imag) for x in ipoints])
					elif segs[i][0] == 'S':
						seg_s = PP
						seg_c1 = 2*PP-CC
						CC = complex(segs[i][1][0],segs[i][1][1])
						seg_c2 = CC
						PP = complex(segs[i][1][2],segs[i][1][3])
						seg_e = PP
						ipoints = interpolate_curved_path(['C',[seg_s,seg_c1,seg_c2,seg_e]], n=num_int_points)
						newp += ' L '+' L '.join(['{:f},{:f}'.format(x.real, x.imag) for x in ipoints])
						points2 += ' '+' '.join(['({:.3f} {:.3f})'.format(x.real, x.imag) for x in ipoints])
					elif segs[i][0] == 'Q':
						seg_s = PP
						CC = complex(segs[i][1][0],segs[i][1][1])
						seg_c = CC
						PP = complex(segs[i][1][2],segs[i][1][3])
						seg_e = PP
						ipoints = interpolate_curved_path(['Q',[seg_s,seg_c,seg_e]], n=num_int_points)
						newp += ' L '+' L '.join(['{:f},{:f}'.format(x.real, x.imag) for x in ipoints])
						points2 += ' '+' '.join(['({:.3f} {:.3f})'.format(x.real, x.imag) for x in ipoints])
					elif segs[i][0] == 'T':
						seg_s = PP
						CC = 2*PP-CC
						seg_c = CC
						PP = complex(segs[i][1][0],segs[i][1][1])
						seg_e = PP
						ipoints = interpolate_curved_path(['Q',[seg_s,seg_c,seg_e]], n=num_int_points)
						newp += ' L '+' L '.join(['{:f},{:f}'.format(x.real, x.imag) for x in ipoints])
						points2 += ' '+' '.join(['({:.3f} {:.3f})'.format(x.real, x.imag) for x in ipoints])
					elif segs[i][0] == 'A':# not supported for interpolation yet
						PP = complex(segs[i][1][5],segs[i][1][6])
						newp += ' L {:f},{:f}'.format(PP.real,PP.imag)
						points2 += ' ({:.3f} {:.3f})'.format(PP.real,PP.imag)
					elif segs[i][0] == 'Z':
						newp += ' Z'
						closed = True
					else:
						pass
					
				angle_points = re.findall(r'[-+]?\d*\.\d+|\d+', newp)
				angle_points = np.array(angle_points,dtype=float)
				
				if calc_rot:
					a = area_fast_path(angle_points)
				else:
					a = '0 deg'
				if closed:
					ns, o = gen_style(s, svg_layer_attribs[3], svg_layer_attribs[4])
					etree.SubElement(ely_layer_reference, 'POLYGON', outline=o, area_fast=a, points=points2)
				else:
					ns = 'fill:none;stroke:{};stroke-width:1;opacity:{}'.format(svg_layer_attribs[3], svg_layer_attribs[4])
					etree.SubElement(ely_layer_reference, 'LINES', points=points2)
				if apply_on_svg:
					svg_path.attrib['style'] = ns
					svg_path.attrib['d'] = newp
				
		#inkex.errormsg(etree.tostring(ely_xml,pretty_print=True).decode())#control output
		ely_xml.write(ep_directory, pretty_print=True, xml_declaration=True, encoding="utf-8")
		
	
if __name__ == '__main__':
	edraw().run()
