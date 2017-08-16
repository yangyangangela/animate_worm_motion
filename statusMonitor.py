from tkinter import *
from tkinter import filedialog
import pandas as pd
import csv

# TODO:
# open windows to report error

def initiate_status_list():
	global status_list

	status_list=[
	[0, 0, 'Undefined']
	]

	return

def load_status_list(filename):
	global status_list
	status_list=[]

	df = pd.read_csv(filename)

	for row in df.iterrows():
		index,data=row
		status_list.append(data.tolist())
	
	return


class statusTop(Toplevel):

	def __init__(self, parent=None,filename=None):

		Toplevel.__init__(self, parent)
		self.wm_geometry("700x500+800+0")

		# Load data into status_list
		self.filename = filename

		# Use the filename as the toplevel title
		if self.filename is None:
			initiate_status_list()
			self.wm_title("Create new status form")
		else:
			load_status_list(self.filename)
			self.wm_title(filename)

		# main frame
		self.main_frame = MainFrame(root=self)

		# button frame
		self.sec_frame = Frame(self)
		Button(self.sec_frame, text="Save", command=self.save).pack(anchor=SW)
		Button(self.sec_frame, text="Save and Quit", command=self.save_and_quit).pack(anchor=SW)

		# pack two frames
		self.main_frame.pack(side=LEFT, padx=10)
		self.sec_frame.pack(side=LEFT, padx=10)

	
	def save(self):
		if self.filename is None:
			self.filename = filedialog.asksaveasfilename(defaultextension=".csv")
			
		with open(self.filename, "w") as f:
			writer = csv.writer(f)
			writer.writerows([['Start','End', 'Status']])
			writer.writerows(status_list)
		f.close()

		self.wm_title( self.filename )
		return

	def save_and_quit(self):
		self.save()
		self.destroy()
		return



class MainFrame(Frame):

	def __init__(self, root=None):
		Frame.__init__(self, root,width=600, height=500)

		self.grid_propagate(False)

		# Rows of display to show entry values
		Label(self, text="Start time (s): ").grid(row=0,column=0, sticky="W")
		self.startVar = StringVar()
		self.start_time = Entry(self, textvariable=self.startVar)
		self.start_time.grid(row=0,column=1,sticky="WE")

		Label(self, text="End time (s): ").grid(row=1,column=0, sticky="W")
		self.endVar = StringVar()
		self.end_time = Entry(self, textvariable=self.endVar)
		self.end_time.grid(row=1,column=1,sticky="WE")

		# duration = end time - start time
		Label(self, text="Duration (s): ").grid(row=2,column=0, sticky="W")
		self.durVar = StringVar()
		self.duration = Entry(self, textvariable=self.durVar)
		self.duration.grid(row=2,column=1,sticky="WE")

		# bind updateDuration
		self.end_time.bind( "<Return>", self.updateDuration )
		self.start_time.bind("<Return>", self.updateDuration )

		# show status
		Label(self, text="Status: ").grid(row=3,column=0, sticky="W")
		self.statusVar = StringVar()
		self.state = Entry( self, textvariable=self.statusVar )
		self.state.grid(row=3,column=1,sticky="WE")

		# option menue to update status
		status_options=['Left Turn','Right Turn','Omega Turn','Pause','Reversal','Bad Data', 'Head Misidentified',]	
		Label(self, text="Update to: ").grid(row=3,column=2, sticky="W")
		self.newStatusVar = StringVar()
		self.newStatusVar.set( status_options[0] )
		self.newstate = OptionMenu(self, self.newStatusVar, *status_options, 
								command=self.updateStatus )
		self.newstate.grid(row=3,column=3,sticky="W")

		# Row of buttons to control entries
		Button(self, text=" Add  ",command=self.addEntry).grid(row=4,column=0,sticky="WE")
		Button(self, text="Update",command=self.updateEntry).grid(row=4,column=1,sticky="WE")
		Button(self, text="Delete",command=self.deleteEntry).grid(row=4,column=2,sticky="WE")
		Button(self, text="Clear ",command=self.clearEntry).grid(row=4,column=3,sticky="WE")

		# Row of the listbox to show all entries
		self.grid_columnconfigure(0, weight=1)
		scroll = Scrollbar(self, orient=VERTICAL)
		self.select = Listbox(self,yscrollcommand=scroll.set, height=20)
		scroll.config(command=self.select.yview)
		scroll.grid(row=5, column=0, columnspan=5, rowspan=10, sticky="WE")
		self.select.grid(row=5, column=0, columnspan=4, rowspan=10,sticky="WE")

		# bind listbox with onselect function to show selected values
		self.select.bind('<<ListboxSelect>>', self.onselect)

		# initiate the list
		self.setSelect()

	def updateDuration(self, value):
		st = float( self.startVar.get() )
		et = float( self.endVar.get() )
		self.durVar.set( str(et-st) )
		return


	def clearEntry(self):
		self.statusVar.set(' ')
		self.startVar.set(' ')
		self.endVar.set(' ')
		self.durVar.set(' ')
		return

	def updateStatus(self, value):
		"""
		Update statusVar with newStatusVar (the OptionMenu)
		"""
		self.statusVar.set( value )
		return

	def addEntry(self):
		status_list.append([float(self.startVar.get()),
							float(self.endVar.get()), 
							str(self.statusVar.get()) ])
		self.setSelect()
		return

	def updateEntry(self):
		try:
			status_list[ self.whichSelected() ] = [float(self.startVar.get()),
											float(self.endVar.get()), 
											str(self.statusVar.get()) ]
			self.setSelect()
			self.clearEntry()
		except ValueError:
			print("input your value first (later windows)")

		return

	def deleteEntry(self):
		try:
			del status_list[ self.whichSelected() ]
			self.setSelect()
		except ValueError:
			print("select entry to delete (later windows)")
		return

	def whichSelected(self):
		return int( self.select.curselection()[0] )

	def onselect(self, evt):
		"""
		Show the selected entry.
		"""
		st, et, status = status_list[ self.whichSelected() ]
		self.startVar.set( str(st) )
		self.endVar.set( str(et) )
		self.durVar.set( str(et-st) )
		self.statusVar.set( status )
		return

	def setSelect(self):
		"""
		Update listbox by sorting and refilling the status_list
		"""
		global status_list
		status_list.sort()
		self.select.delete(0,END)
		for st,et,status in status_list :
			st_text = str(st)+' s - '+str(et)+' s : '+str(status)
			self.select.insert(END,st_text)

		return








