# Documentation for Elcano Simulator Code

**UW Bothell, 2020**

**Advisor :** *Tyler Folsom*

**Team 2019:** *Zach Gale, Jonah Lim, Matthew Moscola, Francisco Navarro-Diaz*

**Team 2020:** *Colton Sellers, Brandon Thompson, Mariah Files, Will Song, Launnie Ginn*

## Purpose
The following is a generalized list of the desired functionality of the simulator.
 - Simulate data for all sensors associated with Elcano Trike.
 - Simulate Elcano behavior to throttle, brake, and steering.
 - Have low and high-level boards function normally with the simulated sensor data without knowing data is being simulated.
 - Allow low and high-level board interaction to be tested.
 - Allow autonomous driving to be tested.
 
## Components ##

#### Simulation:
Code to be executed by a computer that has access to a Carla server, either locally, or through a network.  Controls all objects in Carla simulation.  Sends data to routerboard via client.  Also retrieves actuation instructions from the router board and sends to Carla to control the vehicle.

#### Router Board:
Code to be executed on the Arduino Due that functions as the router board.  Routes drive commands from low-level to Carla.  Also routes sensor data from Carla to high/low-level boards.


## How to Set-Up ##
The following is a guide to set up the Elcano simulator.

#### Materials: 
- 2 Arduino Due. (1 with High-Level Code, 1 with router board code)
- 1 Low-level board with Arduino Mega 2560.
- 1 Router board PCB (Schematics Included, created for Elcano Project)
- 1 male to female DB15 ribbon cable.
- 2 USB A male to USB Micro B male cables.
- 1 USB A male to B male cable.
- 1 computer running Carla 0.9.8 (Can run locally, for development we do this)
- 1 computer to interface between Carla client (Our Simulation Client) and router board (Using Due Router Board Programming Port)

#### To get the Repo as well as submodules (High level and Low level code)
Use git in a shell to clone the repo into a directory using the options below
OR
Just download the repo as zip and unpack (Ensure you have the high level and low level code in the arduino dir)


#### Option 1: clone, then update submodules (If you don't need the arduino code, just clone)
git clone https://github.com/elcano/Simulator

cd .\Simulator\

git submodule init

git submodule update


#### Option 2: Get repo and recursively get submodules
git clone https://github.com/elcano/Simulator --recursive


#### Arduino Preparation (If uploading arduino code)
Libraries needed are listed below:

- CAN_BUS_SHIELD by Seeed-Studio
  - [https://github.com/Seeed-Studio/CAN_BUS_Shield](https://github.com/Seeed-Studio/CAN_BUS_Shield)
- PID by Brett Beauregard
  - [https://github.com/br3ttb/Arduino-PID-Library](https://github.com/br3ttb/Arduino-PID-Library)
- Pin Change Interrupt by Nico Hood
  - [https://github.com/NicoHood/PinChangeInterrupt](https://github.com/NicoHood/PinChangeInterrupt)
- MCP48x2 DAC by Jonas Forsberg
  - [https://github.com/SweBarre/MCP48x2](https://github.com/SweBarre/MCP48x2).
- Arduino Due Timer Interrupts by Ivan Seidel
  - [https://github.com/ivanseidel/DueTimer](https://github.com/ivanseidel/DueTimer)
  
  
Then connect each arduino and upload the respective code to each board. 
   - HighLevel (./Arduino/HighLevel/) code to Arduino Mega (Right side of Router PCB)
   - LowLevel (./Ardunio/LowLevel/) code to Arduino Due (Left side of Router PCB)
   - Routerboard (./Arduino/Router_Board_v1) code to Arduino Due (Middle of Router PCB)

NOTE: PORTS ARE IMPORTANT ON ROUTERBOARD DUE
  - Programming port is used to upload code and debug via serial monitor
  - Native port is used to communicate with CARLA


#### Python Requirements:
- Have Python 3 Installed, we use (3.7.6)
- In a terminal move to .\Simulation\
- run: pip3 install -r requirements.txt
- Pip will install all the required python libraries for the simulator

#### Start Simulation:
- Make sure Carla is running either locally or somewhere accessible over the network
- If not already, have routerboard due plugged in via native port
- Start Simulator UI by running start.bat (.\Simulation\start.bat)
- By default it will populate local running Carla settings, if using a network based server enter IP and Port of Carla into the respective boxes. (i.e. 192.168.1.1, 2010)
- For control via Elcano leave mode as Auto, to control via manual keyboard input change mode to Manual.
- Click "Connect to CARLA"
   - If Auto mode, it will pop up selection of COM devices, select routerboard native port COM to begin and press go. (Will add path selection in the future???)
   - If Manual mode, client will start with keyboard controls (WASD) 

You did it!! Good job. :)

## Out of Scope Functionality Tested/Implemented ##
- Our project required us to delve into pieces of code within the Elcano project outside of our scope.  Understanding of how sensors are read by the high and low-level boards is necessary for the simulation of the sensors.  We were able to fix some issues regarding the CAN communication between the high and low-level boards.  The modified low-level code was not pushed to the main low-level code folder in the repository on Github, however, it is included within the simulator documentation.  The following were implemented.
- Unification of the proposed CAN message structure and the actual CAN message processing on the low-level code for CAN messages with ID 0x350 (High-level drive instructions).  These are CAN messages the high-level will send to the low level to facilitate autonomy.
- Fixing the DAC output voltage by using the MCP48x2 library by Jonas Forsberg.

## To Do (Software): ##
#### High Priority:
- Simulate gyro sensor
- Simulate accelerometer/magnetometer sensor.
- Simulate wheel angle sensor.
- Implement steering actuation when low-level CAN processing of steering command is fixed.
- Initialize CAN with high-level board code and incorporate in demo instead of separate CAN transceiver.
#### Medium Priority:
- Simulate ScanseSweep.
- Implement receiver board when board is fully fixed.
- Incorporate Elcano trike physics to simulated vehicle.
#### Low Priority

## Bugs
- While we were able to fix the code for the low-level CAN interpretation of the throttle and brake commands from high-level CAN messages, the PWM steering response was not fully tested.  We were unable to get the low-level board to output the correct PWM for the sent CAN messages and this needs more testing.
- The receiver board cannot get CAN to initialize.  Voltage testing confirmed that the CAN components (MCP2515 and MCP 2550) are receiving the correct operating voltages (5v).  Also, multiple CAN libraries besides the suggested Seeed Studio library were tested with no success (SparkFun CAN library was one of the tested libraries).  Possible problem is incompatibility between the 5v CAN components and the 3.3V SAMD21 board.  Another possible problem is design flaw of pcb.
- Low-level processing of CAN messages for ID 0x350 is faulty.  Bit shifting and produced output do not match the CAN guidelines on the wiki.  This was fixed in the low-level code included in the simulator folder but not pushed to the Elcano Github repository.

## Note:
- In PowerShell, in CarlaUE4 path, run Carla as: ***Start-Process CarlaUE4 -ArgumentList “—quality-level=Low”*** to lower gpu load.
- Headless mode can be enabled for complete removal of graphics rendering, however, visual debugging is extremely useful.
