import simulator
import manual_control
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk
import os

class Application(tk.Frame):              
    def __init__(self, master=None):
        tk.Frame.__init__(self, master) 
        self.grid()                     
        self.createWidgets()

    def createWidgets(self):

        #Box for IP of CARLA Server
        tk.Label(self, text='Enter Server IP', bd=3).grid(row=7, column=0)
        self.IPEntry = tk.StringVar()
        IPBox = tk.Entry(self, textvariable=self.IPEntry)
        IPBox.grid(row=7, column=1)
        IPBox.insert(0,'localhost') #Default val

        #Box for Port of server
        tk.Label(self, text='Enter Server Port', bd=3).grid(row=8, column=0)
        self.portEntry = tk.StringVar()
        portBox = tk.Entry(self, textvariable=self.portEntry)
        portBox.grid(row=8, column=1)
        portBox.insert(0, '2000') #Default val

        #For Selecting Mode
        tk.Label(self, text='Select Mode', bd=3).grid(row=9, column=0)
        modes = ["Auto", "Manual"]
        self.modeSelected = tk.StringVar()
        box = ttk.Combobox(self, values=modes, justify="center", textvariable=self.modeSelected)
        box.grid(column=1, row=9, padx=(10), pady=(10))
        box.current(0)

        #Button for connecting elcano to CARLA
        tk.Button(self, text="Connect to CARLA", bg="grey", fg="white", command = self.connectToCarla).grid(column=1, row=10, padx=(10), pady=(10))

        #Button for quit
        tk.Button(self, text='Quit', command=self.quit).grid(row=10, column=0, padx=(10), pady=(10)) 
    
    def connectToCarla(self):
        if self.modeSelected.get() == 'Auto' :
            


            #Get COM Devices and add them to a dictionary
            devices =  list(serial.tools.list_ports.comports())
            self.deviceDict = {}
            for device in devices:
                self.deviceDict[device.description] = device.device

            #If there are no devices this won't work. 
            if len(devices) == 0:
                #Notify the user
                popup = tk.Toplevel()
                popup.wm_title("!")

                ttk.Label(popup, text="No Devices connected, check COM Ports, Press Okay to use custom controller").grid(row=0, column=0, padx=(10), pady=(10))
                ttk.Button(popup, text="Okay", command = self.startElcanoSim).grid(column=0, row=1, padx=(10), pady=(10))
                
            else:
                #Popup window for selecting router port
                popup = tk.Toplevel()
                popup.wm_title("COM Select")

                tk.Label(popup, text='Select COM Port of Routerboard', bd=3).grid(row=0, column=0)

                #Setup Combobox of Devices
                self.portSelected = tk.StringVar()
                box = ttk.Combobox(popup, values=list(self.deviceDict.keys()), justify="center", textvariable=self.portSelected, width=30)
                box.grid(column=0, row=1, padx=(10), pady=(10))
                box.current(0)

                #Button for go
                tk.Button(popup, text="GO", bg="grey", fg="white", command = self.startElcanoSim).grid(column=0, row=2, padx=(10), pady=(10))
        



                
        else :
            manual_control.main(self.IPEntry.get(), int(self.portEntry.get()))


    def startElcanoSim(self):
        try:
            COMPort = self.deviceDict[self.portSelected.get()]
            simulator.main(COMPort, self.IPEntry.get(), int(self.portEntry.get()))

        except:
            print('No port connected! Using custom controller')
            simulator.main('COM7', self.IPEntry.get(), int(self.portEntry.get()), 'custom_controller')

        
    


app = Application()                       
app.master.title('Elcano Project Simulation')    
app.mainloop() 

