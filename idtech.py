#!/sw/bin/python2.6
#

import array
import re
import serial
import sys
import time

ACK  = 0x60  # Acknowledge
NACK = 0xE0  # Non-acknowledge
EOT  = 0x03  # End of Transmission aka ETX

MAX_MESSAGE_LEN = 264

ser = serial.Serial('/dev/tty.usbmodem1a21', timeout=1)
ser.flushInput()


# http://atlee.ca/blog/2008/05/27/validating-credit-card-numbers-in-python/
def validate_cc(s):
    """
    Returns True if the credit card number ``s`` is valid,
    False otherwise.
 
    Returning True doesn't imply that a card with this number has ever been,
    or ever will be issued.
 
    Currently supports Visa, Mastercard, American Express, Discovery
    and Diners Cards.  
 
    >>> validate_cc("4111-1111-1111-1111")
    True
    >>> validate_cc("4111 1111 1111 1112")
    False
    >>> validate_cc("5105105105105100")
    True
    >>> validate_cc(5105105105105100)
    True
    """
    # Strip out any non-digits
    s = re.sub("[^0-9]", "", str(s))
    regexps = [
            "^4\d{15}$",
            "^5[1-5]\d{14}$",
            "^3[4,7]\d{13}$",
            "^3[0,6,8]\d{12}$",
            "^6011\d{12}$",
            ]

    if not any(re.match(r, s) for r in regexps):
        return False

    chksum = 0
    x = len(s) % 2
    for i, c in enumerate(s):
        j = int(c)
        if i % 2 == x:
            k = j*2
            if k >= 10:
                k -= 9
            chksum += k
        else:
            chksum += j
    return chksum % 10 == 0



# LRC = Longitudinal Redundancy Check
def compileLRC(list):
    lrc = 0
    for byte in list:
        lrc ^= ord(byte)
    return lrc

def getReply():
    dataString = ser.read(MAX_MESSAGE_LEN)
    bytes = array.array('c')
    bytes.fromstring(dataString)
    if len(bytes) > 0:
        if ord(bytes.pop(-1)) != EOT:
            print 'Exception: Received incomplete message (no EOT/ETX)'
            return
        lrc = ord(bytes.pop(-1))
        if compileLRC(bytes) != lrc:
            print 'Exception: Received corrupt message (wrong LRC)'
            return
        header = ord(bytes.pop(0))
        commandsize = ord(bytes.pop(0)) + ord(bytes.pop(0))
        if len(bytes) != commandsize:
            print 'Exception: Received wrong amount of bytes (received != commandsize)'
            return
        if header == 0xE0:
            print "Exception: NACK'ed message"
            return
        if header == 0x60:
            print 'header: ' + hex(header)
            print 'commandsize: ' + str(commandsize)
            print 'message(' + str(len(bytes)) + '/' + hex(len(bytes)) + '): ',
            print bytes
            return bytes

def parseReaderStatus(statusbyte):
    if statusbyte & 1:
        print '0: No data in a reader'
    else:
        print '0: Others'
    if statusbyte & 2:
        print '1: Card seated'
    else:
        print '1: Card not seated'
    if statusbyte & 4:
        print '2: Media detected'
    else:
        print '2: Others'
    if statusbyte & 8:
        print '3: Card present'
    else:
        print '3: Card not present'
    if statusbyte & 16:
        print '4: Magnetic data present'
    else:
        print '4: No magnetic data'
    if statusbyte & 32:
        print '5: Card in Slot'
    else:
        print '5: All other conditions'
    if statusbyte & 64:
        print '6: Incomplete Insertion'
    else:
        print '6: All other conditions'

def parseCardDataStatus(statusbyte):
    if statusbyte & 1:
        print 'Track 1 decode success'
    else:
        print 'Track 1 decode fail'
    if statusbyte & 2:
        print 'Track 2 decode success'
    else:
        print 'Track 2 decode fail'
    if statusbyte & 4:
        print 'Track 3 decode success'
    else:
        print 'Track 3 decode fail'
    if statusbyte & 8:
        print 'Track 1 data exists'
    else:
        print 'No Track 1 data'
    if statusbyte & 16:
        print 'Track 2 data exists'
    else:
        print 'No Track 2 data'
    if statusbyte & 32:
        print 'Track 3 data exists'
    else:
        print 'No Track 3 data'

def parsetrack1(trackstr):
    if trackstr[1] != 'B':
        print 'Exception: wrong track 1 format (not B)'
        return
    trackdata = trackstr[2:len(trackstr)-1] #remove start/end sentinel
    cardnumber, name, data = trackdata.split('^')
    lastname, firstname = name.split('/')
    expyear = data[0:2]
    expmonth = data[2:4]
    print 'validate ' + cardnumber + ' == ' + str(validate_cc(cardnumber))
    print 'cardnumber: ' + str(cardnumber)
    print 'firstname: ' + firstname.title()
    print 'lastname: ' + lastname.title()
    print 'data: ' + str(data)
    print 'month/year: ' + str(expmonth) + '/' + str(expyear)
    print '---------done------------'

def parsetrack2(trackstr):
    trackdata = trackstr[1:len(trackstr)-1] #remove start/end sentinel
    cardnumber, data = trackdata.split('=')
    expyear = data[0:2]
    expmonth = data[2:4]
    print 'validate ' + cardnumber + ' == ' + str(validate_cc(cardnumber))
    print 'cardnumber: ' + str(cardnumber)
    print 'data: ' + str(data)
    print 'month/year: ' + str(expmonth) + '/' + str(expyear)
    print '---------done------------'

while 1: 
    print '================================================================================'
    print 'waiting for input'
    while ser.inWaiting() < 1:
        time.sleep(1)

    bytes = getReply()
    if bytes == 'None':
        continue
    else:
        print 'bytes length: ' + str(len(bytes))

    command = ord(bytes.pop(0))
    print 'command: ' + hex(command)
    print '-----------------------------------'
    parseReaderStatus(ord(bytes.pop(0)))
    print '-----------------------------------'

    tracks = []
    tracks = bytes.tostring().split('\r') # \r == 0x0d
    for track in tracks:
        if track.find('^') > -1:
            parsetrack1(track)
        if track.find('=') > -1:
            parsetrack2(track)
   



ser.close()

# once this is a proper module, make a test routine using this:
#if __name__ == '__main__':
#    print
