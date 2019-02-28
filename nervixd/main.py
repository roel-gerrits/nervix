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
import argparse

from nervixd.mainloop import Mainloop

from nervixd.reactor import Reactor

from nervixd.controller import Controller
from nervixd.services.telnet.service import TelnetService
from nervixd.services.nxtcp.service import NxtcpService

from nervixd.tracer import PrintTracer


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


logging.basicConfig(
    level=logging.DEBUG,
    format=bcolors.OKGREEN + '%(asctime)s %(name)s [%(levelname)s]: %(message)s' + bcolors.ENDC,
    # stream=sys.stderr
)

logger = logging.getLogger(__name__)


def argparse_validate_address(value):
    host, sep, port = value.partition(':')

    if sep == '':
        raise argparse.ArgumentTypeError("Must specify port")

    try:
        port = int(port)

    except ValueError:
        raise argparse.ArgumentTypeError("Invalid port")

    if not 0 <= port < 65536:
        raise argparse.ArgumentTypeError("Port must be between 0 and 65536")

    return host, port


def argparse_validate_timespan(value):
    try:
        timespan = float(value)

    except ValueError:
        raise argparse.ArgumentTypeError("Invalid timespan")

    return timespan


def main(arg_list):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-x', '--nxtcp',
        dest='nxtcp_addresses',
        action='append',
        help='Enable a NXTCP service on the given host:port address',
        metavar='host:port',
        type=argparse_validate_address,
        default=[],
    )

    parser.add_argument(
        '-t', '--telnet',
        dest='telnet_addresses',
        action='append',
        help='Enable a telnet service on the given host:port address',
        metavar='host:port',
        type=argparse_validate_address,
        default=[],
    )

    args = parser.parse_args(arg_list)

    mainloop = Mainloop()

    controller = Controller(mainloop, args)

    tracer = PrintTracer()

    reactor = Reactor(mainloop, tracer)

    # create NXTCP services
    for address in args.nxtcp_addresses:
        service = NxtcpService(controller, mainloop, reactor, tracer, address)

    # create Telnet services
    for address in args.telnet_addresses:
        service = TelnetService(controller, mainloop, reactor, tracer, address)

    logger.info("Starting mainloop")

    mainloop.run_forever()

    logger.info("Mainloop finished")
