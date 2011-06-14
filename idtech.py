#!/sw/bin/python2.6
#

import array
import re
import serial
import sys
import time

class IDTech():
    '''read data from ID TECH credit card mag stripe readers'''

    ACK  = chr(0x60)  # Acknowledge
    NACK = chr(0xE0)  # Non-acknowledge
    ETX  = chr(0x03)  # End of Transmission aka ETX

    MAX_MESSAGE_LEN = 264

    def __init__(self, device, timeout=None):
        self.serial = serial.Serial(device, timeout=timeout)
        self.serial.flushInput()


    def close(self):
        '''close the connection to the credit card reader'''
        self.serial.close()


    # LRC = Longitudinal Redundancy Check
    def _compileLRC(self, list):
        lrc = 0
        for byte in list:
            lrc ^= ord(byte)
        return lrc


    def read(self):
        bytes = []
        endofpacket = False
        while not endofpacket and len(bytes) <= IDTech.MAX_MESSAGE_LEN:
            byte = self.serial.read()
            if byte != '':
                bytes.append(byte)
            if byte == IDTech.ETX: endofpacket = True
        # TODO figuure out a good exception
        if len(bytes) > 0:
            if bytes.pop(-1) != IDTech.ETX:
                raise Exception('Received incomplete message (no EOT/ETX)')
            lrc = ord(bytes.pop(-1))
            if self._compileLRC(bytes) != lrc:
                raise Exception('Received corrupt message (wrong LRC)')
            header = bytes.pop(0)
            commandsize = ord(bytes.pop(0)) + ord(bytes.pop(0))
            if len(bytes) != commandsize:
                raise Exception('Received wrong amount of bytes (received != commandsize)')
            if header == IDTech.NACK:
                raise Exception('NACK on message')
            if header == IDTech.ACK:
                print 'header: ' + str(header)
                print 'commandsize: ' + str(commandsize)
                print 'message(' + str(len(bytes)) + '/' + hex(len(bytes)) + '): ',
                print bytes
                return bytes


    def parseReaderStatus(self, status):
        statusbyte = ord(status)
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


    def parseCardDataStatus(self, status):
        statusbyte = ord(status)
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


    def split(self, s):
        '''take string ``s`` and split it into command, reader status, and ISO/IEC 7813 tracks'''
        # command, reader status, track 1 and/or track 2
        command = s.pop(0)
        status = s.pop(0)
        tracks = ''.join(s).split('\r') # \r == 0x0d
        track1 = None
        track2 = None
        for track in tracks:
            if track.find('^') > -1:
                track1 = track
            if track.find('=') > -1:
                track2 = track
        return command, status, track1, track2


    def parsetrack1(self, trackstr):
        if not trackstr:
            raise Exception('blank track 1 data')
        if trackstr[1] != 'B':
            raise Exception('wrong track 1 format (not B)')
        trackdata = trackstr[2:len(trackstr)-1] #remove start/end sentinel
        cardnumber, name, data = trackdata.split('^')
        lastname, firstname = name.split('/')
        expyear = data[0:2]
        expmonth = data[2:4]
        print 'track 1 -------------------------------------------------------'
        print 'validate ' + cardnumber + ' == ' + str(self.validate(cardnumber))
        print 'cardnumber: ' + str(cardnumber)
        print 'firstname: ' + firstname.title()
        print 'lastname: ' + lastname.title()
        print 'data: ' + str(data)
        print 'month/year: ' + str(expmonth) + '/' + str(expyear)

    def parsetrack2(self, trackstr):
        trackdata = trackstr[1:len(trackstr)-1] #remove start/end sentinel
        cardnumber, data = trackdata.split('=')
        expyear = data[0:2]
        expmonth = data[2:4]
        print 'track 2 -------------------------------------------------------'
        print 'validate ' + cardnumber + ' == ' + str(self.validate(cardnumber))
        print 'cardnumber: ' + str(cardnumber)
        print 'data: ' + str(data)
        print 'month/year: ' + str(expmonth) + '/' + str(expyear)


    # http://atlee.ca/blog/2008/05/27/validating-credit-card-numbers-in-python/
    def validate(self, cardnumber):
        """
        Returns True if the credit card number ``cardnumber`` is valid,
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
        s = re.sub("[^0-9]", "", str(cardnumber))
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
   

#------------------------------------------------------------------------------#
# for testing from the command line:
def main(argv):
    reader = IDTech('/dev/tty.usbmodem1a21')

    print '========================================================================'
    print 'waiting for input'
    swipestring = reader.read()

    command, status, track1, track2 = reader.split(swipestring)
    print 'command: ' + str(command)
    print '-----------------------------------'
    print 'reader status'
    reader.parseReaderStatus(status)
    print '-----------------------------------'
    print reader.parsetrack1(track1)
    print reader.parsetrack2(track2)

    reader.close()

                
if __name__ == "__main__":
    main(sys.argv[1:])


