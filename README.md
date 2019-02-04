
# Nervix

Nervix is a message broker. It allows you to divide your system into smaller parts and have them communicate with each
other in a reliable and predictable manner.

## Concept

Nervix is a server, it accepts connections from clients. After successful connection clients can talk to each other via
the server. So if you use nervix to devide your system in smaller subsystems and each subsystem will be a client in
respect to the server.

### Namespaces

When connected, clients are able to 'claim' a 'namespace'. This will later allow other clients to send messages to that
namespace. A namespace can only be 'owned' my one client at a time. However nervix allows other clients to run in
standby mode, allowing new clients to take over a namespace when the original clients releases the namespace (either on
purpose, or as result of a misbehaving client), see 'Seamless namespace changeover' for more information.

### Request/response (1:1 messaging)

A client can send requests to a certain namespace. Note that a client does not send a request to a specific client! It
sends a request to the namespace, and nervix will forward it to the client that is owning the namespace at that time.

A request can either be bidirectional or unidirectional. Bidirectional means that the requesting client expects an
answer withing a certain time. Nervix will make sure that a response is always been send, even if the client that ownes
the namespace misbehaves, or if there is no client owning the targeted namespace at all. This allows for easier and
more predictable error handling on your clients.

Unidirectional requests one-way. It basicly means that the sending client doesn't care if it arrives or not. Nervix
will forward the message to client owning the targeted namespace, if the message could not be delivered it will simply
be ignored.

### Publish/subscribe (1:n messaging)

Clients can also 'subscribe' on a 'topic' within a namespace. When a client makes such a subscripton, nervix will let
the client currently owning the namespace know that there is interest in a certain topic. The client can then publish
messages on that topic, and nervix will make sure to deliver them to all the subscribed clients. When all clients have
unsubscribed from the topic, nervix will let the publishing client know that there is no longer interest, and that
client may does stop sending updates about the topic. This feature allows a publishing client to 'know' if there is
even interest in updates.

It also allows subscribes to subscribe on very specific topics. Generally in publish/subscriber implementations the
publisher does not know if there are any subscriptions, and the topics have to be very generic. However in the nervix
implementation the publisher is informed about interest on topics, and the publisher can thus also be very dynamic with
these topics. For example: a client may subscribe on the topic "tank-temperature,update-interval=5s". This would then
be interpreted by the publisher and it will publish the tank temperature every 5 seconds.
See also: 'Interest aware publishers'.


## Getting started

It's very easy to get started and get a feel over how nervix works. In this example we will start a nervix server, and
two telnet based clients, and have them interchange some messages.

To start the server:

```
$ python -m nervixd -t :9999
```

This will start the nervix server and enable a telnet service on port 9999

Start two clients, in two seperate consoles run:

```
$ telnet localhost 9999
```

From one of the clients type:

```
LOGIN testnamespace
```

and hit enter.

You should get a response:

```
SESSION testnamespace ACTIVE
```

Now from the other client type:

```
REQUEST UNI testnamespace message
```

This will send an unidirectional (meaning it expects no response) to the server.

On the other client we will now see an incoming 'call':

```
CALL UNI testnamespace message.
```

See the docs (yet to be made) for how to go from here.


## Features

### Seamless namespace changeover

Within the nervix world, a namespace can only be owned by one client at a time. A client aquires or releases this
ownership by sending login or logout packets to the server. Usually the client that send the login packet first will
get the ownership and nervix will send all messages directed to the namespace to that client.

However if there is now a second client that also tries to login on that namespace it will be put on a queue, and
nervix will the client know its on standby. As soon as the first client releases the namespace, it will be given to the
client that is on 'standby'. All messages to the namespace are now also forwarded to this new client.

A client can on login also specify a 'force' flag, which will result in the namespace given to that client directly,
and the origin client will thus lose ownership over the namespace. A client can prevent it's namespace from being
forcefully taken over by specifying the 'persist' flag on login. These flags allow you for example to update one of
your clients with a newer version, without interupting the services it provides to other clients, or to restart a
client with extra logging options enabled in order to benefit debugging your system.

### Interest aware publishers

In contrast with most message brokers that implement a publish/subscriber system. Nervix' implementation has interest
aware publishers. This means that a publisher knows in what topics clients are interested in. Note that it does not
know which clients are interested in which topics. It only knows that there is '>0' interest in a certain
topic.

This is very beneficial in systems where a publisher can potentially publish on a lot of topics, but where there is
generally only interest in a small subset of these topics. Lets imagine a client that is publishing information about
file changes on a harddrive. If this client wouldn't be aware of the interest it would have to publish all possible
changes on all files. This could potentially waste a lot of CPU and network resources. Now, with interest aware
publishers, lets say we have a client that is interested in changes in .JPG files in a certain subdirectory. This
client can now subscribe on the topic "file-changes;suffix=.JPG,subdir=/var/files". The publishing client will be
informed about the this interest and will start to publish changes matching the topic. As soon as the subscribed client
unsubscribes from that topic, the publishing client will be informed that there is no longer interest in that topic and
it will stop publishing.

Note that the format of the topic in previous example is only an example. Nervix does not enforce a certain format on
the topics, and its fully up to the publishing client to interpret the meaning of the topic.


## Protocols

Clients can talk to the nervix via a number of different protocols, depending on how a client is located within the
network one protocol might be more beneficial over others. Currently there are two protocols implemented.

### NXTCP

This protocol uses TCP as the transport layer. On top of this a very compact binary protocol is implemented with
minimal overhead. The protocol also features a keep-alive mechanism, meaning that the server will send a PING packet
when there has been no data exchange for a certain amount of time (default 10.0 seconds). This is both used to prevent
certain network devices from dropping idle connections, as well as providing an early detection mechanism for
unresponsive clients.

### TELNET

This protocol also uses TCP as the transport layer. On top of this a very simple text-based protocol is implemented.
This allows you to use any telnet terminal to interact with the nervix server directly. Because it's text based it's
easy to use by humans, and can for example be used in debugging situations, or for bash scripts to send simple
requests using netcat for example.

### NXWS

Note: This protocol is not yet implemented, and is still in a design fase.

This protocol uses WebSockets as the transport layer. On top of this a binary protocol similar to the NXTPCP protocl is
implemented.

It is meant for browser based clients, where WebSockets are the only available mechanism for fast asynchronous
communication.


### NXUDP

Note: This protocol is not yet implemented, and is still in a design fase.

This protocol uses UDP as the transport layer with a lightweight binary protocol on top.

This protocol is most suitable for when the network path between client and server is very unreliable, and TCP
connections would take a long time to set up. It would be suitable for clients that would send a lot of unidirectional
requests as it wouldn't matter if those requests end up at the server anyway.
