#!/usr/bin/env python

from tkinter import *
from tkinter import filedialog
import tkinter.constants as tkconstants
import pandas as pd
import time
import os
import numpy as np
from copy import deepcopy

from statusMonitor import * 
from timeSeriesPanel import *


# The data load from file, can only be read by other functions.
class Data(object):
	def __init__(self):
		# save animation data
		self.spine_x_df = None
		self.spine_y_df = None

		# save the status data name, only load data when displaying time series
		self.status_data_name = None
		self.offset_time = 0  # the initial time in original data
		self.video_length = 0 

	def load_spine_data(self):
		"""
		- Load the time series of 11-point spine data of a worm to self.spine_x_df
		- Set the self.total_length
		- SEt the offset_time

		Output:
			x_df,y_df: columns = [0,1,2,3,4,5,6,7,8,9,10,time,head_verified]
						each row is a snapshot of the video.
		"""
		# select the xdata_name, generate ydata_name
		xdata_name =  filedialog.askopenfilename(initialdir = "./",
			title = "Select spine X",filetypes = (("csv files","*.csv"),("all files","*.*")))
		ydata_name = xdata_name.replace('x.csv','y.csv')

		x_df = pd.read_csv( xdata_name )
		y_df = pd.read_csv( ydata_name )

		x_df = x_df.drop( ['Unnamed: 0','frame','frame2'],  axis=1 )
		y_df = y_df.drop( ['Unnamed: 0','frame','frame2'],  axis=1 )

		self.spine_x_df, self.spine_y_df = x_df, y_df
		self.offset_time = x_df.iloc[0,11]

		video_length = x_df.iloc[-1,11] - self.offset_time
		self.video_length = video_length

		# re-normalize the time
		self.spine_x_df['time'] = self.spine_x_df['time'] - self.offset_time
		self.spine_y_df['time'] = self.spine_y_df['time'] - self.offset_time

		spine_data_name = deepcopy( xdata_name )
		spine_data_name = spine_data_name.replace('_x.csv','.csv')

		return spine_data_name, video_length

	def load_status_data(self):
		"""
		Load existing status data
		"""
		self.status_data_name =  filedialog.askopenfilename(initialdir = "./",
			title = "Select Status File",filetypes = (("csv files","*.csv"),("all files","*.*")))

		return self.status_data_name



# The data input by user, to control the animation
class Parameter(object):
	def __init__(self):
		self.animation_speed = 2
		self.start_time = 0



class Animate(Frame):

	def __init__(self, root=None, console_window=None, data=None, parameter=None):

		Frame.__init__(self, root, width=450, height=380, bg="gray93" )

		# stop the auto fitting of frame
		self.grid_propagate(False)

		self.root = root
		self.data = data
		self.parameter = parameter
		self.console_window = console_window
		self.current_time = StringVar()
		self.TS_frame = None # Frame to show time series

		self.STOP_BY_USER = False # constant, change by stop button.
		self.SHOW_STATUS = False # constant, change by "enable status" button

		# variables to plot worm spine
		self.current_frame_index = 0 # The current frame index of the animation
		self.current_ovals = {} # the handles of current worm ovals

		# total number of frames in the data
		self.end_step = 0

		# initialize the grid of the frame
		self.grid_rowconfigure(0, weight=1)
		self.grid_columnconfigure(0, weight=1)
		for r in range(4):
			self.columnconfigure(r, weight=1)
		for r in range(6):
			self.rowconfigure(r, weight=1)

		# top: show the current time
		Label( self, text='Current time (s):' 
			).grid( in_=self,row=0, column=0, sticky=W,padx=5)
		Entry( self, textvariable=self.current_time 
			).grid( in_=self,row=0, column=1, sticky=W)

		# middle: scanvas to show spine
		self.canvas = Canvas( self, bg='black')
		self.canvas.grid(row=1, column=1, rowspan=4, 
			columnspan=2, sticky=W+E+N+S, padx=10)
		
		# left middle: buttons to control the animation
		Button( self, text='(Re)Start',command=self.start_by_user 
			).grid( in_=self, row=1,column=0,sticky=W+E,padx=5)
		Button( self, text='Pause/Resume', command=self.pause_or_resume
			).grid( in_=self, row=2, column=0,sticky=W+E)
		Button( self, text='Stop', command=self.stop_by_user 
			).grid( in_=self,row=3,column=0,sticky=W+E,padx=5)

		# bottom: enable status time series
		Button( self, text="Enable Time Series",command=self.enable_status
			).grid( in_=self, row=4,column=0, sticky=W)

		
	def start_by_user(self):
		# Clear and start
		self.canvas.delete("all")
		self.STOP_BY_USER = False;
		self.display_text('Start...')

		# update the current index by parameter.start_time, update end_step
		self.current_frame_index = self.time_to_frame( self.parameter.start_time )
		self.end_step = len( data.spine_x_df.index )

		self.animate(start_step = self.current_frame_index, 
					end_step = self.end_step,
					h=self.set_step_length() )
		return

	def pause_or_resume(self):
		if self.STOP_BY_USER:
			self.resume_by_user()
		else:
			self.pause_by_user()
		return

	def stop_by_user(self):
		self.STOP_BY_USER = True;

		# reset current frame index and end_step
		self.current_frame_index = 0
		self.end_step = len( data.spine_x_df.index )

		self.display_text('...stopped.')
		return

	def pause_by_user(self):
		self.STOP_BY_USER = True;
		self.end_step = len( data.spine_x_df.index )

		self.display_text('...paused.')
		return

	def resume_by_user(self):

		self.STOP_BY_USER = False;
		self.end_step = len( data.spine_x_df.index )

		self.display_text('Resume...')

		# clear previous
		self.canvas.delete("all")

		# conitue from current frame
		self.animate(start_step = self.current_frame_index,
					end_step = self.end_step,
					h=self.set_step_length() )		
		return

	def time_to_frame(self, value):
		"""
		change the time (in s) to frame index
		Input:
			value: float

		return:
			an int
		"""
		myseries = deepcopy( self.data.spine_x_df['time' ] )
		abs_diff = abs( myseries - value )
		
		frame_index = abs_diff[ abs_diff == min(abs_diff) ].index[0]
		return frame_index

	def set_step_length(self):
		"""
		Return the h (in ms) for self.animation
		"""
		speed = self.parameter.animation_speed
		
		dt = self.data.spine_x_df.loc[2,'time'] - self.data.spine_x_df.loc[1,'time']

		h = int( round( dt*1000/speed ) )

		return h


	def animate(self, start_step=0, end_step=100000, h=100):
		"""
		Plot the spine shape time series on canvas.
		Input:
			start_step: index of start frame,LATER link with control data
			end_step: index of the end frame
			h (ms): time duration on each frame, unit is ms. LATER link with control data.
		"""

		if self.data.spine_x_df is None:
			self.display_text('Error: load data first!')
			return

		self.current_frame_index = start_step

		while not self.should_stop( end_step=end_step ) and not self.STOP_BY_USER:

			# Set current time
			current_time = str( self.data.spine_x_df.loc[ self.current_frame_index, 'time' ] )
			self.current_time.set(current_time)

			# Plot the current frame and update frame index
			self.canvas.after(h,self.draw_one_frame(start_step = start_step))
			self.current_frame_index += 1

			# If show time series, enable update line.
			if self.SHOW_STATUS:
				self.TS_frame.update_time_tick(current_time=float(current_time))



		if self.current_frame_index == end_step:
			self.display_text('Animation finished.')

		return


	def should_stop( self, end_step=0 ):
		"""
		If current_frame_index> end_step, return stop signal to animate.
		"""
		if self.current_frame_index >= end_step:
			return True
		else:
			return False


	def draw_one_frame( self, start_step=0 ):
		"""
		Draw the current spine on canvas. Use canvas.move to draw the changes
		Input: 
			start_step: the frame index to start 
		"""
		SIDX = range(11) #11-points spine index
		
		cidx = self.current_frame_index
		
		# vector of spines
		X = np.array( self.data.spine_x_df.iloc[ cidx, SIDX ] )
		Y = np.array( self.data.spine_y_df.iloc[ cidx, SIDX ] )
		points = zip(X,Y)
		
		head_verified = self.data.spine_x_df.loc[ cidx, 'head_verified' ]
	
		# plot the first frame
		if cidx == start_step:
			for i, pt in enumerate(points):
				xc, yc, x1, x2, y1, y2 = self.create_coord( pt )
				self.current_ovals[i] = self.canvas.create_oval(\
					x1,y1,x2,y2,fill='green')

		# plot the folllowing frames using canvas.move
		else:
			# previous spine vecotrs
			pX = np.array( data.spine_x_df.iloc[ cidx-1, SIDX ] )
			pY = np.array( data.spine_y_df.iloc[ cidx-1, SIDX ] )
			# incremental vectors
			dX = X-pX
			dY = Y-pY

			for i,dx in enumerate(dX):
				dy = dY[i]
				self.canvas.move( self.current_ovals[i], dx, dy )

			self.update()

		return


	def display_text(self,txt):
		self.console_window.insert(END, txt+'\n')
		return


	def enable_status(self):

		if not self.SHOW_STATUS:
			self.SHOW_STATUS = True;

			filename = self.data.status_data_name

			if filename is None:
				self.display_text('Load status data first!!!')
				return
			else:
				self.TS_frame=statusTimeSeries(root=self.root, filename=filename, 
					video_length=self.data.video_length)
				self.TS_frame.place(x=300,y=450)
				self.display_text('Display status time series...')

		else:
			self.SHOW_STATUS = False
			self.TS_frame.destroy()


		return


	@staticmethod
	def create_coord(a_point,point_radius = 4, canvas_radius = 100):
		"""
		Return the coords for center and four corners of a point 
		in the spine.
		"""
		#center
		xc = a_point[0]+canvas_radius
		yc = a_point[1]+canvas_radius
		# left corner
		x1 = xc-point_radius
		y1 = yc-point_radius
		# right corner
		x2 = xc+point_radius
		y2 = yc+point_radius
		return xc, yc, x1, x2, y1, y2



class Control(Frame):

	def __init__(self, root=None, console_window=None, data=None, parameter=None):

		Frame.__init__(self, root, width=280, height=380 )
		self.grid_propagate(False)

		self.console_window = console_window  # window to show info
		self.data = data    	# include spine data and status data
		self.parameter = parameter # parameters to control process
		self.root = root

		self.video_length = StringVar();    self.video_length.set('0')
		self.spine_data_name = StringVar(); self.spine_data_name.set(' ')
		self.status_data_name = StringVar();self.status_data_name.set(' ')


		# Widgets to select Spine Data
		Button( self, text="Load spine", 
			command=self.load_spine_data ).grid(row=0,column=0,sticky="W")

		Label( self, text="Video length (s):" ).grid(row=1,column=0,sticky="W")
		Entry( self, textvariable=self.video_length, width=10).grid(row=1,column=1,sticky="W",padx=5)

		Label( self, text="Path:" ).grid(row=3,column=0,sticky="W")
		Entry( self, textvariable=self.spine_data_name ).grid(row=4,column=0,columnspan=2, sticky="WE", padx=5)

		separator = Frame(self, height=5, bd=1, relief=SUNKEN)
		separator.grid(row=5, column=0, padx=5, pady=12)


		# Widgets to select Status data
		Button( self, text="Create/Start",
			command=lambda: self.open_status_toplevel(loadfile=False) ).grid(row=6,column=0,sticky="W")
		Button( self, text="Load status",
			command=lambda: self.open_status_toplevel(loadfile=True) ).grid(row=6,column=1,sticky="W")

		Label( self, text="Path:" ).grid(row=7,column=0,sticky="W")
		Entry( self, textvariable=self.status_data_name ).grid(row=8,column=0,columnspan=2, sticky="WE",padx=5)

		separator2 = Frame(self, height=5, bd=1, relief=SUNKEN)
		separator2.grid(row=9, column=0, padx=5, pady=15)


		# Widgets to input animation parameters
		Label( self, text="Animation speed: " ).grid(row=10, column=0,sticky="W")

		speed_options=['0.5', ' 1 ', ' 2 ',' 3 ',' 5 ', '10', '20', '30' ] # speed to choose
		self.temp_var = StringVar(); self.temp_var.set( '2' )
		OptionMenu(self, self.temp_var, *speed_options, command=self.set_speed ).grid(row=10,column=1,sticky="WE")

		# Widgets to control start time
		Label( self, text="Start time (s): " ).grid(row=11, column=0,sticky="W")
		self.start_time = StringVar()

		self.st_text = Entry( self, textvariable=self.start_time )
		self.st_text.grid(row=11,column=1, sticky="W")

		self.st_scale = Scale( self, from_=0, to=1, resolution=0.0001, orient=HORIZONTAL, showvalue=0,
			command=self.set_start_time_by_scaler)
		self.st_scale.grid(row=12, column=0, columnspan=2, sticky="WE")

		# bind Entry to the Scale, return can constrol the scaler
		self.st_text.bind( "<Return>", self.set_start_time_by_entry )

		# Widgets to control pause time
		Label( self, text="Pause time (s): " ).grid(row=13,column=0,sticky="W")
		self.pause_time = StringVar()
		Entry( self, textvariable=self.pause_time ).grid(row=13,column=1, sticky="W")

		Button( self, text="Recap selected clip",
			command=self.play_selected_clip ).grid(row=14, column=1)


	def play_selected_clip(self):

		start_time = float( self.start_time.get() )
		pause_time = float( self.pause_time.get() )

		temp_start_step = animateFrame.time_to_frame( start_time )
		temp_end_step = animateFrame.time_to_frame( pause_time )

		animateFrame.canvas.delete("all")
		animateFrame.STOP_BY_USER = False
		animateFrame.animate( start_step=temp_start_step,
			end_step=temp_end_step )

		return


	def set_start_time_by_scaler(self, value):
		"""
		Update the self.start_time and parameter.start_time from scaler
		"""
		video_length = float( self.video_length.get() )
		start_time = round( float(value)*video_length )

		self.start_time.set( str(start_time) )
		self.parameter.start_time = start_time

		return


	def set_start_time_by_entry(self, event):
		"""
		Set the self.start_time and parameter.start_time from text
		"""
		video_length = float( self.video_length.get() )
		start_time = float( self.st_text.get() ) 

		to_value = round( start_time/video_length*1000 )/1000
		self.st_scale.set(to_value)
		self.parameter.start_time = start_time
		self.start_time.set( str(start_time) )

		return


	def set_speed(self, value):
		self.parameter.animation_speed = float(value)
		return

	def load_spine_data(self):
		"""
		Load the time series of 11-point spine data of a worm.
		Output:
			x_df,y_df: columns = [0,1,2,3,4,5,6,7,8,9,10,time,head_verified]
						each row is a snapshot of the video.
		"""
		# load the file 
		data_name, video_length = self.data.load_spine_data() 

		# update string variable for entries
		self.spine_data_name.set( data_name )
		self.video_length.set( video_length )
		
		self.display_text('Spine data loaded.')
		return 


	def open_status_toplevel(self,loadfile=False):
		# If the status_data_name is empty and user want to load data
		if loadfile:
			file_name = self.data.load_status_data()
			self.status_data_name.set( file_name )
			self.display_text('Load existing status data file.')
			statusTop(parent=self, filename=file_name)	
		
		else:
			if len( self.status_data_name.get() )>20:
				file_name = self.status_data_name.get()
				self.display_text('Load existing status data file.')
				statusTop(parent=self, filename=file_name)	
			else:
				statusTop(parent=self)
				self.display_text('Create new status data file.')	

		return


	def display_text(self,txt):
		self.console_window.insert(END, txt+'\n')
		return




class Console(Frame):

	def __init__(self, root=None):
		Frame.__init__(self, root, width=250, height=400)
		self.grid_propagate(False)

		self.console = Text(self, bg="gray93", font=("Times New Roman",12), relief=RIDGE )
		self.console.grid(row=1,column=0,sticky="WE")
		self.console.insert(END, 'Welcome!\n')
		
		cl = Label(self, text="Console:",font=("Times New Roman",20))
		cl.grid(row=0,column=0,sticky="W")

		return


if __name__ == '__main__':
	# master, comps, and worm_animate are global objects
	master = Tk();
	master.wm_title("Worm Movement Marker")
	master.geometry("800x800+0+0")	# width x height + x_offset + y_offset

	# claim global variables
	data  = Data()
	parameter = Parameter()

	# console windows, left bottom 
	consoleFrame = Console(root = master)
	consoleFrame.place(x=10,y=410)

	# control frame, left up
	controlFrame = Control( root=master,console_window=consoleFrame.console, data=data, parameter=parameter )
	controlFrame.place(x=10,y=10)

	# animation frame, right up
	animateFrame = Animate( root=master,console_window=consoleFrame.console, data=data, parameter=parameter )
	animateFrame.place(x=300,y=20)

	master.mainloop()