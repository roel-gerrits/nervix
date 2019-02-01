class KeepAlive:
    """
    The KeepAlive class.

    This class is usefull for implementing keepalive functionality for
    services.
    """

    STATE_ACTIVE = 0
    STATE_IDLE = 1
    STATE_WARNED = 2
    STATE_DEAD = 3

    def __init__(self, mainloop):
        self.mainloop = mainloop

        self.resolution = 1.0

        self.cur_idle_time = 0.0
        self.max_idle_time = 10.0

        self.cur_warning_time = 0.0
        self.max_warning_time = 10.0

        self.timer = self.mainloop.timer()
        self.timer.set_handler(self.__timer_tick)
        self.timer.set(self.resolution)

        self.state = self.STATE_ACTIVE

        self.warning_handler = None
        self.dead_handler = None

        self.destroyed = False

        self.tickle()

    def set_max_idle_time(self, time):
        self.max_idle_time = time

    def set_max_warning_time(self, time):
        self.max_warning_time = time

    def destroy(self):
        """
        Destroy the keepalive, freeing up resources.
        """
        self.timer.cancel()
        self.destroyed = True

    def set_warning_handler(self, handler):
        """
        Set the handler that will be called when the keepalive mechanism
        desides that a it's time to send a warning signal.
        """

        self.warning_handler = handler

    def set_dead_handler(self, handler):
        """
        Set the handler that will be called when the keepalive mechanism
        desides that it's idle too long and the connection should be
        considered dead.
        """

        self.dead_handler = handler

    def tickle(self):
        """
        This method should be called periodicly in order to prevent the
        keepalive mechanism to call the wakeup and dead handlers.
        """

        self.state = self.STATE_ACTIVE

    def __timer_tick(self):

        # active state
        if self.state == self.STATE_ACTIVE:

            self.cur_idle_time = 1.0
            self.cur_warning_time = 0.0

            self.state = self.STATE_IDLE

        # idle state
        elif self.state == self.STATE_IDLE:

            self.cur_idle_time += self.resolution

            if self.cur_idle_time >= self.max_idle_time:

                if self.warning_handler:
                    self.warning_handler()

                self.state = self.STATE_WARNED

        # warned state
        elif self.state == self.STATE_WARNED:

            self.cur_warning_time += self.resolution

            if self.cur_warning_time >= self.max_warning_time:

                if self.dead_handler:
                    self.dead_handler()

                self.state = self.STATE_DEAD

        # dead state
        elif self.state == self.STATE_DEAD:
            pass

        if not self.destroyed:
            self.timer.set(self.resolution)
