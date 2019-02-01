class ServiceController:

    def __init__(self, cli_args):
        self.cli_args = cli_args

        self.clients = set()

    def register_service(self, service):
        pass

    def unregister_service(self, service):
        pass

    def register_client(self, client):
        self.clients.add(client)

    def unregister_client(self, client):
        self.clients.remove(client)

    def get_clients(self):
        return list(self.clients)
