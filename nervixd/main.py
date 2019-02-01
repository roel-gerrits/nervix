import logging
import argparse
import sys

from nervixd.mainloop import Mainloop

from nervixd.reactor import Reactor

from nervixd.services import ServiceController
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

    tracer = PrintTracer()

    reactor = Reactor(mainloop, tracer)

    controller = ServiceController(args)

    # create NXTCP services
    for address in args.nxtcp_addresses:
        service = NxtcpService(controller, mainloop, reactor, tracer, address)

    # create Telnet services
    for address in args.telnet_addresses:
        service = TelnetService(controller, mainloop, reactor, tracer, address)

    logger.info("Starting mainloop")

    mainloop.run_forever()

    logger.info("Mainloop ended")
