#!/usr/bin/env python

# pyved - python video entropy daemon
# (c) 2010 by Kai Dietrich <mail@cleeus.de>
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import sys
import time
import struct
import pygame
import pygame.camera as pygcam
import array
import os


#initialiye pygame and camera
pygame.init()
pygcam.init()
cams = pygcam.list_cameras()
cam = pygcam.Camera(cams[0], (720,576))
cam.start()


try:
	os.mkfifo("entropy.fifo")
except OSError:
	pass

outfifo = open("entropy.fifo", "wb")
#outfile = open("entropy.bin", "w+b")

sfc = None
sfc_old = None
while True:
	entropy_needed = int(open("/proc/sys/kernel/random/write_wakeup_threshold").read().strip())
	entropy_avail = int(open("/proc/sys/kernel/random/entropy_avail").read().strip())
	if entropy_avail > entropy_needed:
		time.sleep(5)
		continue
	else:
		print "Waking up, entropy level at: %d" % entropy_avail
	
	#swap images
	sfc_old = sfc
	sfc = cam.get_image()
	
	if not sfc or not sfc_old:
		continue

	#lock images
	sfc_old.lock()
	sfc.lock()
	
	max_w = sfc.get_width()
	max_h = sfc.get_height()
	
	entropy = array.array('I')
	byte = 0
	n_bits = 0
	for y in xrange(0, max_h):
		for xx in xrange(0, max_w/2-1):
			x = xx*2			

			#generate a difference
			pix = sfc.get_at((x,y))
			pix_old = sfc_old.get_at((x,y))
			diff1 = [ abs(pix.r - pix_old.r), abs(pix.g - pix_old.g),  abs(pix.b - pix_old.b)]
			
			#generate another
			pix = sfc.get_at((x+1,y))
			pix_old = sfc_old.get_at((x+1,y))
			diff2 = [ abs(pix.r - pix_old.r), abs(pix.g - pix_old.g), abs(pix.b - pix_old.b)]
	

			#print "%d %d" % ((diff_a[i] & 1), (diff_a[i] & 1))
			for i in xrange(0,3):
				#the changes in the colors seem not to correlate
				if (diff1[i] & 1) != (diff2[i] & 1):
					#add one bit of entropy
					byte = (byte<<1)
					bit = (diff1[i] & 1)
					byte = (byte | bit)
					n_bits += 1
				
					if n_bits == 32:
						#actually, it's not a byte but a 32bit word
						entropy.append(byte)
						byte = 0
						n_bits = 0
	#write out collected entropy
	#outfile.seek(0)
	#outfile.truncate(0)
	#entropy.tofile(outfile)
	entropy.tofile(outfifo)

	#unlock images
	sfc_old.unlock()
	sfc.lock()

cam.stop()
outfile.close()
