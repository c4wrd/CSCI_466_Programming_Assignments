'''
Created on Oct 12, 2016

@author: mwitt_000
'''
import math
import queue
import threading
import struct
import zlib
from io import StringIO

## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.queue = queue.Queue(maxsize);
        self.mtu = None
    
    ##get packet from the queue interface
    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, block=False):
        self.queue.put(pkt, block)

class Flags:
    MORE_FRAGMENTS = "0"
    LAST_FRAGMENT = "1"


## Implements a network layer packet (different from the RDT packet
# from programming assignment 2).
# NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.
class NetworkPacket:
    FRAGMENT_FLAG_LEN = 1
    FRAGMENT_OFFSET_LEN = 4
    HEADER_DST_LEN = 5
    HEADER_SRC_LEN = 5
    HEADER_LENGTH_LEN = 4
    HEADER_CHECKSUM_LEN = 4
    HEADER_LEN = 23

    ##@param dst_addr: address of the destination host
    # @param data_S: packet payload
    def __init__(self,
                 fragment_flag,
                 fragment_offset,
                 dest_addr,
                 src_addr,
                 data_S):
        self.fragment_flag = fragment_flag
        self.fragment_offset = fragment_offset
        self.dest_addr = dest_addr
        self.src_addr = src_addr
        self.data_S = data_S

    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()

    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        buffer = StringIO()
        buffer.write(self.fragment_flag)
        buffer.write(str(self.fragment_offset).zfill(self.FRAGMENT_OFFSET_LEN))
        buffer.write(str(self.src_addr).zfill(self.HEADER_SRC_LEN))
        buffer.write(str(self.dest_addr).zfill(self.HEADER_DST_LEN))
        # calculate length
        length = NetworkPacket.HEADER_LEN + len(self.data_S)
        buffer.write(str(length).zfill(self.HEADER_LENGTH_LEN))
        # calculate checksum
        checksum = str(zlib.crc32(buffer.getvalue().encode()))[:self.HEADER_CHECKSUM_LEN]
        buffer.write(checksum)
        # insert data
        buffer.write(self.data_S)

        return buffer.getvalue()

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        buffer = StringIO(byte_S)
        header_str = buffer.read(self.HEADER_LEN)
        header, checksum = header_str[:-self.HEADER_CHECKSUM_LEN], header_str[-self.HEADER_CHECKSUM_LEN:]
        data = buffer.read()

        calculated_checksum = str(zlib.crc32(header.encode()))[:self.HEADER_CHECKSUM_LEN]

        if calculated_checksum != checksum:
            raise Exception("IP packet had invalid checksum")

        header_buffer = StringIO(header)
        fragment_flag = header_buffer.read(self.FRAGMENT_FLAG_LEN)
        fragment_offset = int(header_buffer.read(self.FRAGMENT_OFFSET_LEN))
        src_addr_s = int(header_buffer.read(self.HEADER_SRC_LEN))
        dst_addr_s = int(header_buffer.read(self.HEADER_DST_LEN))

        return self(fragment_flag, fragment_offset, src_addr_s, dst_addr_s, data_S=data)

class PacketFragmenter:

    @classmethod
    def fragment(cls, src_addr, dst_addr, data_s, mtu_size):
        packets = []
        packet_size = mtu_size - NetworkPacket.HEADER_LEN

        if packet_size < 0:
            raise Exception("MTU was less than packet header size")

        num_packets = int(math.ceil(len(data_s) / packet_size))

        offset = 0
        for i in range(num_packets):
            fragment_contents = data_s[:packet_size]
            data_s = data_s[packet_size:]
            packets.append(NetworkPacket(Flags.MORE_FRAGMENTS, offset, dst_addr, src_addr, fragment_contents))
            offset += packet_size

        # set the last packet to have the last fragment flag
        packets[-1].fragment_flag = Flags.LAST_FRAGMENT
        return packets

    @classmethod
    def fragment_packet(cls, packet: NetworkPacket, mtu_size):
        packets = []
        packet_size = mtu_size - NetworkPacket.HEADER_LEN

        # check if we do not need to refragment
        if len(packet.data_S) < packet_size:
            return [packet]

        data_s = packet.data_S
        num_packets = int(math.ceil(len(data_s) / packet_size))

        offset = packet.fragment_offset
        for i in range(num_packets):
            fragment_contents = data_s[:packet_size]
            data_s = data_s[packet_size:]
            packets.append(NetworkPacket(Flags.MORE_FRAGMENTS, offset, packet.dest_addr, packet.src_addr, fragment_contents))
            offset += packet_size

        if packet.fragment_flag == Flags.LAST_FRAGMENT:
            packets[-1].fragment_flag = Flags.LAST_FRAGMENT

        return packets

## Implements a network host for receiving and transmitting data
class Host:
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.in_intf_L = [Interface()]
        self.out_intf_L = [Interface()]
        self.stop = False #for thread termination
        self.frames = []
    
    ## called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)
       
    ## create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, src_addr, dst_addr, data_S):
        packets = PacketFragmenter.fragment(src_addr, dst_addr, data_S, self.out_intf_L[0].mtu)
        for packet in packets:
            self.out_intf_L[0].put(packet.to_byte_S()) #send packets always enqueued successfully
            print('%s: sending packet "%s" out interface with mtu=%d' % (self, packet, self.out_intf_L[0].mtu))

    # reassembles the packets in the buffer
    def reassemble(self):
        buffer = StringIO()
        offset = 0
        sorted_frames = sorted(self.frames, key=lambda packet: packet.fragment_offset)
        for frame in sorted_frames: # type: NetworkPacket
            if frame.fragment_offset != offset:
                raise Exception("Missing data frame when re-assembling packet")
            buffer.write(frame.data_S)
            offset += len(frame.data_S)

        return buffer.getvalue()

    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.in_intf_L[0].get()
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))
            pkt = NetworkPacket.from_byte_S(pkt_S)
            self.frames.append(pkt)

            if pkt.fragment_flag == Flags.LAST_FRAGMENT:
                contents = self.reassemble()
                print("Received constructed packet, contents: %s" % contents)
       
    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router described in class
class Router:
    
    ##@param name: friendly router name for debugging
    # @param intf_count: the number of input and output interfaces 
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_count, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.in_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        self.out_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]

    ## called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)

    ## look through the content of incoming interfaces and forward to
    # appropriate outgoing interfaces
    def forward(self):
        for i in range(len(self.in_intf_L)):
            pkt_S = None
            try:
                #get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                #if packet exists make a forwarding decision
                if pkt_S is not None:
                    p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                    fragments = PacketFragmenter.fragment_packet(p, self.out_intf_L[i].mtu)
                    # HERE you will need to implement a lookup into the 
                    # forwarding table to find the appropriate outgoing interface
                    # for now we assume the outgoing interface is also i

                    for fragment in fragments:
                        self.out_intf_L[i].put(fragment.to_byte_S(), True)
                        print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                            % (self, fragment, i, i, self.out_intf_L[i].mtu))

            except queue.Full:
                print('%s: packet "%s" lost on interface %d' % (self, p, i))
                pass
                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 