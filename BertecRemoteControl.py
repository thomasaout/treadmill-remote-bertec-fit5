from threading import Timer
import zmq

class RemoteControl:
    SUCCESS = 1,
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_SERVER_ERROR = -32603
    TREADMILL_RPC_ERROR = -1
    INCLINE_RPC_ERROR = -1
    MOTION_BASE_RPC_ERROR = -1

    DEFAULT_TIMEOUT = 5000
    HEARTBEAT_MAX_ATTEMPTS = 10

    VERSION = "v1"

    def start_connection(self, server_ip="127.0.0.1", rpc_port="5555", data_port="5556", client_ip="127.0.0.1", client_port="5560"):
        # If any previous connections are running, don't run this method
        if ('connected' in globals() and self.connected):
            return

        # Set up ZMQ context and other connection parameters
        self.id = 1
        self.heart_attempts = 0
        self.context = zmq.Context()
        self.connected = False
        self.started = True

        self.server_ip = server_ip
        self.rpc_port = rpc_port
        self.data_port = data_port
        self.heart_ip = client_ip
        self.heart_port = client_port
        
        # Request socket used for all RPC commands to the server
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.setsockopt(zmq.RCVTIMEO, self.DEFAULT_TIMEOUT)
        self.req_socket.connect("tcp://" + self.server_ip + ":" + rpc_port)
        # Heartbeat socket used to detect if connection between client and server has terminated
        #self.heart_socket = self.context.socket(zmq.ROUTER)
        #self.heart_socket.bind("tcp://" + self.heart_ip + ":" + self.heart_port)
        # Subscriber socket used to receive force data from software
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.CONFLATE, 1)
        self.sub_socket.connect("tcp://" + self.server_ip + ":" + data_port)
        self.sub_socket.subscribe('')
        # Send initial connection request to see if our connection is good
        init_res = self.send_init_connect(self.heart_ip, self.heart_port)

        # Wait for response with default timeout value. If we don't get a response
        # back from send_init_connect
        if (init_res is not None and init_res['code'] == 1):
            self.sub_poller = zmq.Poller()
            self.sub_poller.register(self.sub_socket, zmq.POLLIN)
            #self.sub_poller.register(self.heart_socket, zmq.POLLIN)
            #self.heart_timer = Timer(1, self.get_heartbeat_resp)
            # self.heart_timer.start()
            self.connected = True

            return init_res
        else:
            self.stop_connection()

        return None

    def stop_connection(self):
        if ('started' not in globals() or not self.started):
            return

        self.started = False
        self.connected = False

        self.req_socket.disconnect("tcp://" + self.server_ip + ":" + self.rpc_port)
        self.req_socket.close()
        self.sub_socket.disconnect("tcp://" + self.server_ip + ":" + self.data_port)
        self.sub_socket.close()
        #self.heart_socket.unbind("tcp://" + self.heart_ip + ":" + self.heart_port)
        #self.heart_socket.close()

        # if ('heart_timer' in globals()):
        #     self.heart_timer.cancel()
        if ('sub_poller' in globals()):
            self.sub_poller.unregister(self.sub_socket)
            #self.sub_poller.unregister(self.heart_socket)


    def get_json_request_message(self, method, params):
        json_message = {
            'version': self.VERSION,
            "id": self.id,
            "method": method,
            "params": params
        }

        return json_message

    def get_force_data(self):
        socks = dict(self.sub_poller.poll(self.DEFAULT_TIMEOUT))
        if socks:
            if socks.get(self.sub_socket) == zmq.POLLIN:
                return self.sub_socket.recv_json(zmq.NOBLOCK)
        else:
            return None

    def get_heartbeat_resp(self):
        self.heart_attempts += 1
        socks = dict(self.sub_poller.poll(self.DEFAULT_TIMEOUT))
        if socks:
            if socks.get(self.heart_socket) == zmq.POLLIN:
                self.connected = True
                res = self.heart_socket.recv()
                identity = self.heart_socket.recv()
                self.heart_socket.send(res, zmq.SNDMORE)
                self.heart_socket.send(identity)
            else:
                res = None
        else:
            res = None

        if (res is None):
            if self.heart_attempts >= self.HEARTBEAT_MAX_ATTEMPTS:
                self.stop_connection()
        else:
            self.heart_attempts = 0

        if (self.connected):
            self.heart_timer.cancel()
            self.heart_timer = Timer(1, self.get_heartbeat_resp)
            self.heart_timer.start()

    def send_init_connect(self, ip, port):
        params = {
            'ip': ip,
            'port': port
        }
        json_msg = self.get_json_request_message('InitConnect', params)
        res = self.send_json_message(json_msg)
        return res

    def run_treadmill(self, left_vel, left_accel, left_decel, right_vel, right_accel, right_decel):
        def format_bertec(value):
            return str(value).replace('.', ',')  # Convertit 1.5 → '1,5'

        params = {
            'leftVel': format_bertec(left_vel),
            'leftAccel': format_bertec(left_accel),
            'leftDecel': format_bertec(left_decel),
            'rightVel': format_bertec(right_vel),
            'rightAccel': format_bertec(right_accel),
            'rightDecel': format_bertec(right_decel),
        }

        json_msg = self.get_json_request_message('RunTreadmill', params)
        res = self.send_json_message(json_msg)
        return res

    """ 
    def run_treadmill(self, left_vel, left_accel, left_decel, right_vel, right_accel, right_decel):
        params = {
            'leftVel': left_vel,
            'leftAccel': left_accel,
            'leftDecel': left_decel,
            'rightVel': right_vel,
            'rightAccel': right_accel,
            'rightDecel': right_decel,
        }

        json_msg = self.get_json_request_message('RunTreadmill', params)
        res = self.send_json_message(json_msg)
        return res  """

    def run_incline(self, incline_angle):
        params = {
            'inclineAngle': incline_angle,
        }

        json_msg = self.get_json_request_message('RunIncline', params)
        res = self.send_json_message(json_msg)
        return res

    def is_treadmill_moving(self):
        params = {}

        json_msg = self.get_json_request_message('IsTreadmillMoving', params)
        res = self.send_json_message(json_msg)
        return res

    def is_incline_moving(self):
        params = {}

        json_msg = self.get_json_request_message('IsInclineMoving', params)
        res = self.send_json_message(json_msg)
        return res
    
    def is_client_authenticated(self):
        params = {}

        json_msg = self.get_json_request_message('IsClientAuthenticated', params)
        res = self.send_json_message(json_msg)
        return res
        
    def send_json_message(self, msg):
        print("Sending message: " + str(msg))
        try:
            self.req_socket.send_json(msg, zmq.NOBLOCK)
            self.id = self.id + 1
            recv_msg = self.req_socket.recv_json()
            print("Received message: " + str(recv_msg))
        except zmq.error.Again as _e:
            print("Message failed to send : " + _e.strerror)
            recv_msg = None
        finally:
            return recv_msg

    def get_run_treadmill_user_input(self):
        left_vel = input("Input left velocity: ")
        left_accel = input("Input left acceleration: ")
        left_decel = input("Input left deceleration: ")
        right_vel = input("Input right velocity: ")
        right_accel = input("Input right acceleration: ")
        right_decel = input("Input right deceleration: ")

        return {
                'leftVel': left_vel,
                'leftAccel': left_accel,
                'leftDecel': left_decel,
                'rightVel': right_vel,
                'rightAccel': right_accel,
                'rightDecel': right_decel,
            }

    def get_run_incline_user_input(self):
        incline_angle = input("Input incline angle: ")

        return {
            'inclineAngle': incline_angle
        }