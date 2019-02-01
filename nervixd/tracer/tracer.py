import sys


class BaseTracer:

    def __init__(self):
        pass

    def channel_opened(self, channel):
        pass

    def channel_closed(self, channel):
        pass

    def upstream_verb(self, sender, verb):
        pass

    def downstream_verb(self, receiver, verb):
        pass

    def improper_logout(self, name_state, logout_verb):
        pass

    def unknown_postref(self, sender, postref):
        pass

    def unowned_post(self, sender, post):
        pass

    def service_started(self, service):
        pass

    def service_stopped(self, service):
        pass

    def client_connected(self, client):
        pass

    def client_disconnected(self, client):
        pass

    def client_unresponsive(self, client):
        pass

    def unwatched_unsubscribe(self, client, name, topic):
        pass

    def invalid_upstream_verb(self, sender, verb, reason):
        pass

    def invalid_downstream_verb(self, receiver, verb, reason):
        pass

    def session_activated(self, channel, name):
        pass


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class PrintTracer(BaseTracer):

    def _print(self, *args):
        print(bcolors.OKBLUE + ' '.join([str(x) for x in args]) + bcolors.ENDC, file=sys.stdout)

    def channel_opened(self, channel):
        self._print("-O Channel opened")

    def channel_closed(self, channel):
        self._print("-X Channel closed")

    def upstream_verb(self, sender, verb):
        self._print(">>> Received upstream", sender, verb)

    def downstream_verb(self, receiver, verb):
        self._print("<<< Sending downstream", receiver, verb)

    def improper_logout(self, name_state, logout_verb):
        self._print("ERROR: Improper logout")

    def unknown_postref(self, sender, postref_verb):
        self._print("ERROR: Post to unknown postref {}".format(postref_verb.postref))

    def unowned_post(self, postref, sender, postverb):
        self._print("ERROR: Post send but not owned")

    def service_started(self, service):
        self._print("Service started")

    def service_stopped(self, service):
        self._print("Service stopped")

    def client_connected(self, client):
        self._print("Client connected")

    def client_disconnected(self, client):
        self._print("Client disconnected")

    def client_unresponsive(self, client):
        self._print("Client is unresponsive")

    def unwatched_unsubscribe(self, client, name, topic):
        self._print("Client unsubscribed without watching")

    def invalid_upstream_verb(self, sender, verb, reason):
        self._print("Invalid verb")

    def invalid_downstream_verb(self, receiver, verb, reason):
        self._print("Invalid verb")

    def session_activated(self, channel, name):
        self._print("Session activated")
