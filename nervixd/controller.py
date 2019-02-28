# Copyright (C) 2019  Roel Gerrits <roel@roelgerrits.nl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import signal

SHUTDOWN_SOON = 0
SHUTDOWN_NOW = 1

logger = logging.getLogger(__name__)


class Controller:

    def __init__(self, mainloop, cli_args):
        self.mainloop = mainloop
        self.cli_args = cli_args

        self.units = set()
        self.shutdown_funcs = dict()
        self.descriptions = dict()

        # time a service or client may take to gracefully shutdown,
        # after this time a forceful shutdown will follow
        self.kill_delay = 5.0

        # dict of pending shutdowns, the value is a timer that counts is used to send the kill signal
        self.pending_shutdowns = dict()

        # flag that indicates if we are in the process of shutting down the hole server
        self.server_shutdown_in_process = False

        # set handlers for signals
        signal.signal(signal.SIGINT, self.__on_term_signal)
        signal.signal(signal.SIGTERM, self.__on_term_signal)

    def register(self, key, description, shutdown_func):
        """ Called from a client or service in order to register itself with the controller.
        """

        self.units.add(key)
        self.shutdown_funcs[key] = shutdown_func
        self.descriptions[key] = description

        logger.info("Unit %s registered", description)

    def unregister(self, key):
        """ Called form a client or service in order to unregister ittself with the conroller.
        """

        self.shutdown_funcs.pop(key)
        description = self.descriptions.pop(key)
        self.units.remove(key)

        timer = self.pending_shutdowns.pop(key, None)
        if timer:
            timer.cancel()

        logger.info("Unit %s unregistered", description)

        # if we are in the process of shutting down the server, check if all clients and services are shut down
        # and stop the mainloop if so.
        if self.server_shutdown_in_process:
            if not self.units:
                logger.info("All units unregistered, stopping server")
                self.mainloop.shutdown()

    def start_server_shutdown(self):
        """ Start a process that will shutdown the server.
        """

        # set the flag, when all units are unregistered this flag will be checked and the mainloop ended.
        self.server_shutdown_in_process = True

        # start shutdown of each unit
        for key in list(self.units):
            self.start_shutdown(key)

    def start_shutdown(self, key, action=SHUTDOWN_SOON):
        """ Start the shutdown process of a single 'unit' (client or service)
        """

        description = self.descriptions[key]
        shutdown_func = self.shutdown_funcs[key]

        logger.info("Shutting down %s", description)

        # call shutdown func
        shutdown_func(action)

        # above call should cause the given client or service to unregister,
        # we now check if it did this indeed...
        if key in self.units:

            # hmm it did not... lets handle this situation depending on the type of action we send...

            if action == SHUTDOWN_SOON:
                # lets set a timer, when the timer expires we will call the shutdown func with action==SHUTDOWN_NOW

                if key in self.pending_shutdowns:
                    # we've alreayd set a timer, no need to do it again...
                    return

                # set timer
                timer = self.mainloop.timer()
                timer.set_handler(self.start_shutdown, key, SHUTDOWN_NOW)
                timer.set(self.kill_delay)
                self.pending_shutdowns[key] = timer

                logger.info("Unit %s needs more time, waiting %s seconds", description, self.kill_delay)

            elif action == SHUTDOWN_NOW:

                # hmm the service or client didn't unregister, even after the SHUTDOWN_NOW action. This
                # indicates an error in the implementation of the client/service. Lets fail hard and early,
                # we don't want to deal with this kind of nonsence.

                raise RuntimeError("Client/service was not unregistred after SHUTDOWN_NOW... "
                                   "this is a bug, and needs to be fixed...")

    def __on_term_signal(self, signo, stackframe):
        """ Called when SIG_INT or SIG_TERM is received.
        """

        signame = signal.Signals(signo).name
        logger.info("Received %s, starting server shutdown", signame)

        self.start_server_shutdown()
