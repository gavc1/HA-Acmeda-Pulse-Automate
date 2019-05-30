import logging
import time
import asyncio
import serial_asyncio
import queue
import threading
import time

_LOGGER = logging.getLogger(__name__)


class PulseSession:
    port = ''
    baud = 9600

    motors = []


SESSION = PulseSession()


class PulseApi:
    def __init__(self,port):
        self.baud = 9600
        self._serial_loop_task = None
        self._port = port
        self.motors = []
        self.reader = None
        self.writer = None
        self.hass = None
        self._queue = queue.Queue()
 
    async def main(self,hass):
        t = threading.Thread(target=self.consumeQueue)
        t.start()
        self.hass = hass
        _, self.writer = await serial_asyncio.open_serial_connection(url=self._port, baudrate=self.baud)
        self._serial_loop_task = self.hass.loop.create_task(self.serial_read())



    def setup_stream(self):
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.main())
        loop.close()
    
    def consumeQueue(self):
        while(True):
            if(self._queue.empty()):
                time.sleep(2)
            else:
                self.send(self._queue.get()) 
                time.sleep(1)

    def send(self,msg):
        if self.writer != None:
            self.writer.write(msg.encode('utf-8'))
            _LOGGER.info(f'sent: {msg}')

    	
    	
    async def serial_read(self):
        reader, _ = await serial_asyncio.open_serial_connection(url=self._port, baudrate=self.baud)
        #_LOGGER.debug('reader created %s - %s' % (self._port, self.baud))

        while True:
            msg = await reader.readuntil(b';')
            self.hass.async_create_task(self.message_handler(msg))
        _LOGGER.debug('ended loop?')

            
    async def stop_serial_read(self):
        """Close resources."""
        if self._serial_loop_task:
            self._serial_loop_task.cancel()
            
    async def message_handler(self,message):
    	message = message.decode('utf-8', errors='replace')
    	_LOGGER.debug(f'received: {message}')
    	"""Hub Version
    	Example Request !000V?;
    	Example response: !187V;
    	Hub: 187
    	"""
    	"""Motor Position message !(XXX)D(YYY)r(DD1)b(DD2);
    	Example Request !187D001r?;
    	Example response: !187D001r00b180; 
    	Hub: 187
    	Motor: 001
    	r:00 (fully open, 100 is closed)
    	b:180 (fully open 00 is closed)
    	
    	Start to run, return the present position; DD1 is travel percentage and DD2 is rotation percentage in degrees (0-180)
    	"""
    	
    	
    	"""Open blind
    	!187D002o;
    	response
    	opening: !187D002<58b00;
    	done: !187D002r00b180;
    	
    	"""
    	
    	"""close blind
    	!187D002c;
    	response
    	!187D002U;

    	closing: !187D002>58b00;
    	done: !187D002r00b180;
    	
    	"""
    	
    	"""move to
    	!187D002m100;
    	response
 

    	closing: !187D002<00b180;
    	done: !187D002r10b00;
    	
    	"""
    	
    	"""New Hub detected incomming message, eg !187V;"""
    	if 'V;' in message:
    	    new_hub = message[-5:-2]
    	    _LOGGER.debug("Hub Found: " + new_hub)
    	    
    	    
  	
    	"""Update Motor Position, eg 
    	Example response: !187D001r00b180; 
    	Hub: 187
    	Motor: 001
    	r:00 (fully open, 100 is closed)
    	b:180 (fully open 00 us closed)
    	"""
    	if 'r' in message:
    	    _LOGGER.debug("found update message " + message)
    	    hub = message[message.find("!")+1:message.find("D")]
    	    motor = message[message.find("D")+1:message.find("r")]
    	    position = await self.formatPos(message)
    	    
    	    _LOGGER.debug("updating hub:" + hub)
    	    _LOGGER.debug("updating motor:" + motor)
    	    _LOGGER.debug("updating position:" + position)
    	    await self.setMotorPosition(hub,motor,position)
    async def formatPos (self,pos):
        posfound = False
        intpos = ""
        for x in pos:
            if posfound:
                try:
                    intx = int(x)
                    intpos = intpos+ x
                except:
                    posfound= False
            if x == "r":
                posfound = True
	    
        return intpos
	    

    async def setMotorPosition(self,hub_id, motor_id,position):
        await self.add_Motor(hub_id,motor_id)
        #_LOGGER.debug("looking for existing motor")

        for m in self.motors:
            if m._hub == hub_id and m._motor == motor_id:
                try:
                    m._position = int(position)
                except:
                    _LOGGER.debug("error with position %s resetting to 0" %(position))
                    m._position = 0
                #m._status = 0
    		    
    def getMotorPosition(self,hub_id, motor_id):
        for m in self.motors:
            if m._hub == hub_id and m._motor == motor_id:
                #invert so 0 is closed 100 is open
                try:
                    pos = int(m._position)
                    pos = abs(pos - 100)
                    return pos
                except:
                    _LOGGER.debug("error with position %s resetting to 0" %(m._position))
                    m._position = 0
        return 0
        
    def getmotorstate(self,hub_id, motor_id):
        for m in self.motors:
    	    if m._hub == hub_id and m._motor == motor_id:
    		    return m._state
        return 0
    		    

    def setmotorstatus(hub_id, motor_id,status):
        for m in self.motors:
    	    if m._hub == hub_id and m._motor == motor_id:
    		    m._status = status
    		    
    def Request_Current_Possition(self,hub_id, motor_id):

        message = "!%sD%sr?;" % (hub_id, motor_id)
        _LOGGER.debug("updating position %s" % (message))
        self._queue.put(message)

    
    
    async def add_Motor(self, hub_id, motor_id):
        #_LOGGER.debug("checking if motor exists")

        existing = False
        for m in self.motors:
            #_LOGGER.debug("checking motor %s - %s"%(m._hub, m._motor))
            if m._hub == hub_id and m._motor == motor_id:
                existing = True
        if existing == False:
            #_LOGGER.debug("new motor detected")

            new_motor = Motor(hub_id, motor_id)
            #_LOGGER.debug("adding new motor")

            self.motors.append(new_motor)

   
    	
    
    def set_cover_position(self,hub_id,motor_id,new_position):
        #invert so 0 is closed 100 is open
        try:
            pos = int(new_position)
            pos = abs(pos - 100)
            message = "!%sD%sm%d;"  %(hub_id,motor_id,pos)
            self._queue.put(message)
        except:
            _LOGGER.debug("error inverting position" %(new_position))


    


class Motor:
    """ Represents an ACMEDA Motor """
    def __init__(self,hub_id,motor_id):
        self._motor = motor_id
        self._hub = hub_id
        self._position = 0
        self._state = None
