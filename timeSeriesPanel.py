from tkinter import *
from tkinter import filedialog
import pandas as pd
import csv
import numpy as np
from copy import *

import matplotlib
#matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from shapely.geometry.polygon import Polygon
from descartes import PolygonPatch

import sys


class statusTimeSeries(Frame):

	RED = "#FF0000"
	BLUE = "#0000FF"
	BLACK = "#000000"
	GREEN = "#008000"
	LIGHTBLUE = "#ADD8E6"

	STATUS_LIST = ['Pause', 'Pirouette', 'Turn', 'Undefined']
	STATUS_COLOR = {'Normal': LIGHTBLUE,
					'Pause': RED,
					'Pirouette':GREEN,
					'Turn':BLUE,
					'Undefined':BLACK}

	def __init__(self, root=None, filename=None, video_length=0):

		Frame.__init__(self, root, width=450, height=300 )

		self.grid_propagate(False)

		self.statusVar = StringVar()
		self.statusVar.set("None")

		# load the status data
		self.df = pd.read_csv( filename )
		self.video_length = video_length

		# Plot the bars to show the time series of status
		self.fig_handle = Figure(figsize=(4.5, 0.5), dpi=100)
		self.ax = self.fig_handle.add_subplot(111)
		self.plot_status_distribution()

		# Add the tickline to indicate current time
		self.time_tick, = self.ax.plot([20,20],[0,3],'r-',linewidth=0.5)

		self.canvas = FigureCanvasTkAgg(self.fig_handle, master=self)
		self.canvas.show()
		self.canvas.get_tk_widget().grid(row=0,column=0,columnspan=5)

		# Display the current status
		BIG = ("Helvetica", 15, "bold")
		Label(self, text="Status:"
			).grid(row=1,column=0,sticky=W,pady=10)
		Entry( self, textvariable=self.statusVar, font=BIG, width=10
			).grid(row=2,column=0,sticky=W)

		# Display the statistics
		status_statistics = self.get_statistics()

		Label(self, text="Turn", fg=self.STATUS_COLOR['Turn']
			).grid(row=1,column=1,sticky=W,pady=10)
		Label( self, text=str(status_statistics["Turn"])+"%" 
			).grid(row=1,column=2,sticky=W,pady=10)

		Label(self, text="Pirouette", fg=self.STATUS_COLOR['Pirouette']
			).grid(row=1,column=3,sticky=W,pady=10)
		Label( self, text=str(status_statistics["Pirouette"])+"%" 
			).grid(row=1,column=4,sticky=W,pady=10)

		Label(self, text="Pause", fg=self.STATUS_COLOR['Pause']
			).grid(row=2,column=1,sticky=W )
		Label( self, text=str(status_statistics["Pause"])+"%" 
			).grid(row=2,column=2,sticky=W )

		Label(self, text="Undefined", fg=self.STATUS_COLOR['Undefined']
			).grid(row=2,column=3,sticky=W )
		Label( self, text=str(status_statistics["Undefined"])+"%" 
			).grid(row=2,column=4,sticky=W )


		# switch to other time series
		Label(self, text="Switch to other Time series:"
			).grid(row=3, column=0, columnspan=2, sticky=W)

		ts_options=['Status','Speed','Curvature','Head-Tail disatance']	
		self.ts_Var = StringVar()
		self.ts_Var.set( ts_options[0] )
		self.newTS = OptionMenu(self, self.ts_Var, *ts_options)
		self.newTS.grid(row=3,column=3,columnspan=2,sticky="W",pady=20)



	def plot_status_distribution( self, length=3600 ):


		# plot the background polygon
		bg_pd = Polygon( [(0,1),(0,2),(length,2),(length,1),(0,1)] )
		bg_pch = PolygonPatch( bg_pd, fc=self.STATUS_COLOR['Normal'],
			ec=self.STATUS_COLOR['Normal'])
		self.ax.add_patch( bg_pch )

		# plot each clip as a polygon
		for index,row in self.df.iterrows():
			st = float( row['Start'] )
			et = float( row['End'])
			cl = self.STATUS_COLOR[ str( row['Status'] ) ]

			polygn = Polygon( [(st,1),(st,2),(et,2),(et,1),(st,1)] )
			ptch = PolygonPatch( polygn, fc=cl, ec=cl )
			self.ax.add_patch( ptch )

		# set the limits of the plot
		self.ax.set_ylim([0.5,2.5])
		self.ax.set_xlim([0,length])

		# set the ticks
		self.ax.get_yaxis().set_ticks([])
		self.ax.set_xlabel('Time (s)')

		return


	def get_statistics(self):
		"""
		Return the percentage of endurance for each status
		"""
		status_percentage = {"Undefined":0,
							"Pirouette":0,
							"Turn":0,
							"Pause":0
							}

		df = self.df.copy()
		df['Endurance']=df['End']-df['Start']

		# Sum endurance for each state
		sdf = pd.DataFrame( df.groupby(['Status'])['Endurance'].sum()
			).reset_index()

		print(sdf.columns)
		
		# Calculate the endurance percentage for abnormal states
		for index, row in sdf.iterrows():
			status = str( row['Status'] )
			endurance = float( row['Endurance'] )
			status_percentage[ status ] = round( endurance/self.video_length*100,2 )

		return status_percentage


	def update_time_tick(self, current_time=0):
		"""
		- Draw a tick line to indicate the current time
		- Update the current status Var
		"""
		x = [current_time,current_time]
		y= [ 0,3 ]

		self.time_tick.set_xdata(x)
		self.time_tick.set_ydata(y)

		self.canvas.draw()
		self.whichStatus(current_time)      
		return

	def whichStatus( self, time_point ):
		"""
		Update the statusVar by the given time point (a float)
		"""
		if self.df.loc[0,'Start'] > time_point:
			self.statusVar.set( "Normal" )
			return
		else:
			row = self.df[ self.df['Start']<time_point ].iloc[0]
			end_time = row['End']
			status = row['Status']
		if float(end_time)>time_point:
			self.statusVar.set( str(status) )
		else:
			self.statusVar.set( "Normal" )
		return







