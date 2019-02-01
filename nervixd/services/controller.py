class ServiceController:

    def __init__(self, cli_args):
        self.cli_args = cli_args

        self.services = set()
        self.clients = set()

    def register_service(self, service):
        self.services.add(service)

    def unregister_service(self, service):
        self.services.remove(service)

    def register_client(self, client):
        self.clients.add(client)

    def unregister_client(self, client):
        self.clients.remove(client)
