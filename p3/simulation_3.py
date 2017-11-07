'''
Created on Oct 12, 2016

@author: mwitt_000
'''
import network_3 as network
import link_3 as link
import random
import string
import threading
from time import sleep

##configuration parameters
router_queue_size = 0 #0 means unlimited
simulation_time = 60 #give the network sufficient time to transfer all packets before quitting

if __name__ == '__main__':
    object_L = [] #keeps track of objects, so we can kill their threads
    
    #create network nodes
    host1 = network.Host(1)
    object_L.append(host1)
    host2 = network.Host(2)
    object_L.append(host2)
    host3 = network.Host(3)
    object_L.append(host2)
    host4 = network.Host(4)

    """
    Route format:
    {
        src_addr: {
            dst_addr: interface
        }
    }
    """
    routes_a = {
        1: {
            3: 0,
            4: 0
        },
        2: {
            3: 1,
            4: 1
        }
    }
    routes_b = {
        1: {
            3: 0,
            4: 0
        }
    }
    routes_c = {
        2: {
            3: 0,
            4: 0
        }
    }
    routes_d = {
        1: {
            3: 0,
            4: 1
        },
        2: {
            3: 0,
            4: 1
        }
    }
    router_a = network.Router(name='A', intf_count=2, max_queue_size=router_queue_size, routes=routes_a)
    router_b = network.Router(name='B', intf_count=1, max_queue_size=router_queue_size, routes=routes_b)
    router_c = network.Router(name='C', intf_count=1, max_queue_size=router_queue_size, routes=routes_c)
    router_d = network.Router(name='D', intf_count=2, max_queue_size=router_queue_size, routes=routes_d)
    object_L.append(router_a)
    object_L.append(router_b)
    object_L.append(router_c)
    object_L.append(router_d)
    
    #create a Link Layer to keep track of links between network nodes
    link_layer = link.LinkLayer()
    object_L.append(link_layer)
    
    #add all the links
    link_layer.add_link(link.Link(host1, 0, router_a, 0, 50))
    link_layer.add_link(link.Link(host2, 0, router_a, 1, 50))

    link_layer.add_link(link.Link(router_a, 0, router_b, 0, 50))
    link_layer.add_link(link.Link(router_a, 1, router_c, 0, 50))

    link_layer.add_link(link.Link(router_b, 0, router_d, 0, 50))
    link_layer.add_link(link.Link(router_c, 0, router_d, 1, 50))

    link_layer.add_link(link.Link(router_d, 0, host3, 0, 50))
    link_layer.add_link(link.Link(router_d, 1, host4, 0, 50))
    

    hosts = [host1, host2, host3, host4]
    routers = [router_a, router_b, router_c, router_d]
    #start all the objects
    thread_L = []
    for host in hosts:
        thread_L.append(threading.Thread(name=str(host), target=host.run))
    for router in routers:
        thread_L.append(threading.Thread(name=str(router), target=router.run))
    thread_L.append(threading.Thread(name="Network", target=link_layer.run))
    
    for t in thread_L:
        t.start()
    
    
    #create some send events
    message = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'

    # invalid route, will display error
    #host1.udt_send(2, message)

    # forward from host 1 to hosts 3 and 4
    host1.udt_send(3, message)
    host1.udt_send(4, message)

    # forward from host 2 to hosts 3 and 4
    host2.udt_send(3, message)
    host2.udt_send(4, message)
    
    #give the network sufficient time to transfer all packets before quitting
    sleep(simulation_time)
    
    #join all threads
    for o in object_L:
        o.stop = True
    for t in thread_L:
        t.join()
        
    print("All simulation threads joined")



# writes to host periodically