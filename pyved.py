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

import signal
import atexit
import time
import pygame
import pygame.camera as pygcam
import array
import os
import sys

#set exit behavior
def goodbye(exit_status):
	cam.stop()
#	if os.stat("/dev/shm/pyvrandom.fifo").st_size != 0:
#		os.remove("/dev/shm/pyvrandom.fifo")
	print "Exiting with status %s" % (exit_status)


def sig_handler(signum, frame):
	print "Received signal %s at frame %f" % (signum, frame)
	sys.exit(0)

atexit.register(goodbye, 0)
signal.signal(signal.SIGTERM, sig_handler)


#initialize pygame and came
pygcam.init()
cams = pygcam.list_cameras()
print pygcam.list_cameras()
cam = pygcam.Camera(cams[0], (160, 120))
cam.start()

try:
	print "Creating FIFO at /dev/shm/pyvrandom.fifo with mode 0600"
	os.mkfifo("/dev/shm/pyvrandom.fifo", 0600)
	pass
except OSError:
	pass

try:
	print "Openning FIFO. (if this hangs here, make sure the read end is open.)"
	outfifo = open("/dev/shm/pyvrandom.fifo", "wb", 0)
	print "FIFO successfully opened"
	pass
except OSError:
	print "FATAL ERROR: Cannot open FIFO."
	sys.exit(1)

sfc = None
sfc_old = None

print "Entering entropy gathering loop"
while True: 
	entropy_needed = int(open("/proc/sys/kernel/random/write_wakeup_threshold").read().strip())
	entropy_avail = int(open("/proc/sys/kernel/random/entropy_avail").read().strip())

	if entropy_avail > entropy_needed:
		print "Sleeping, entropy level at: %d" % entropy_avail
		time.sleep(5)
		continue
	else:
		print "Waking,   entropy level at: %d" % entropy_avail
	
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
			pix = sfc.get_at((x, y))
			pix_old = sfc_old.get_at((x, y))
			diff1 = [ abs(pix.r - pix_old.r), abs(pix.g - pix_old.g),  abs(pix.b - pix_old.b)]
			
			#generate another
			pix = sfc.get_at((x+1, y))
			pix_old = sfc_old.get_at((x+1, y))
			diff2 = [ abs(pix.r - pix_old.r), abs(pix.g - pix_old.g), abs(pix.b - pix_old.b)]
	

			#print "%d %d" % ((diff_a[i] & 1), (diff_a[i] & 1))
			for i in xrange(0, 3):
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

#if __name__ == "__main__":
#	atexit.register(goodbye, 0)
#	signal.signal(signal.SIGTERM, sig_handler)
#	try:
#		while True:
#			main()
#	except KeyboardInterrupt:
#		goodbye()
