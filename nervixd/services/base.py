

class BaseService:

    def kill(self):
        """
        Called when the service should stop. Effectively stop listening
        for connections.
        """

        raise NotImplementedError()


class BaseClient:
    
    def kill(self):
        """
        Called when the client should be killed. Effectively releasing
        all it's channels and closing connections.
        """
        
        raise NotImplementedError()

