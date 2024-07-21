"""
Lightweight driver for interfacing with the RYLR998 LoRa module by REYAX.
Author Tim Hanewich, github.com/TimHanewich
Find updates to this code: https://github.com/TimHanewich/MicroPython-Collection/blob/master/REYAX-RYLR998/

MIT License
Copyright 2024 Tim Hanewich
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import machine
import time

class RYLR998:

    def __init__(self, uart:machine.UART) -> None:
        self._uart = uart

        # clear out UART Rx buf
        while self._uart.any() > 0:
            self._uart.read()

        # set up internal RX buffer
        self._rxbuf:bytes = bytes()

    @property
    def pulse(self) -> bool:
        """Runs a simple test command to the RYLR998 module to validate it is connected and functioning properly."""
        response:bytes = self._command_response("AT\r\n".encode("ascii"))
        return response == "+OK\r\n".encode("ascii")

    def send(self, address:int, data:bytes) -> None:
        """Send a packet of binary data to a specified address."""

        # max length that can be sent in one go is 240
        if len(data) > 240:
            raise Exception("Provided data packet of length " + str(len(data)) + " to send is too large! Limit is 240 bytes.")

        # assemble the command
        cmd:bytes = bytes()
        cmd += "AT+SEND=".encode("ascii")
        cmd += str(address).encode("ascii") + ",".encode("ascii")
        cmd += str(len(data)).encode("ascii") + ",".encode("ascii")
        cmd += data
        cmd += "\r\n".encode("ascii")

        print("Going to send: " + str(cmd))

        # send the command, get the response
        response:bytes = self._command_response(cmd, 1.0)

        # if not successful
        if response != "+OK\r\n".encode("ascii"):
            raise Exception("Send command '" + str(cmd) + "' returned abnormal response '" + str(response) + "'")

    def _colrx(self) -> None:
        """Collects and moves all bytes from UART Rx buffer to internal buffer."""
        all_bytes:bytes = self._uart.read()
        if all_bytes != None:
            self._rxbuf += all_bytes
    
    def _command_response(self, command:bytes, response_delay:float = 0.5)-> bytes:
        """Sends a byte sequence (AT command) to the RYLR988 module, and collects the response while still preserving any pre-existing bytes in the internal Rx buffer."""

        # collect any bytes still left over in UART Rx and make note of the length of the internal buffer before the command is sent out and response for it is received
        self._colrx()
        len_before:int = len(self._rxbuf)

        # send command
        self._uart.write(command)

        # wait a little for it to be processed and then the response to arrive
        time.sleep(response_delay)

        # collect any new bytes in UART Rx
        self._colrx()

        # count the number of new bytes that were just added!
        new_bytes_count:int = len(self._rxbuf) - len_before

        # if there are not any new bytes in the internal buf, it failed!
        if new_bytes_count == 0:
            raise Exception("Response from RYLY998 for command " + str(command) + " was not received after waiting " + str(response_delay) + " seconds!")
        
        # get the ones we just received
        response:bytes = self._rxbuf[-new_bytes_count:]

        # trim the internal buffer now that we just "plucked" the response out of it
        self._rxbuf = self._rxbuf[0:-new_bytes_count]

        return response

