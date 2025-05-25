import numpy as np
import time
import threading
import BertecRemoteControl  # Communication module with the treadmill
import interface
import scipy.linalg
import zmq

# Initialize communication with the treadmill
remote = BertecRemoteControl.RemoteControl()
remote.start_connection()

CENTER_COP = 0.8  # Treadmill center position on the y-axis (usually ~0.7-0.8)
dt = 0.01  # Time step (10 ms)
COMMAND_DELAY = 0.1  # Minimum delay between speed updates
DECELERATION_SMOOTHING = 0.25  # Smoothing factor when decelerating

# System model for COP
A = np.array([[1, dt],
              [0, 1]])
B = np.array([[0],
              [1]])
C = np.array([[1, 0]])

# LQR gain computation
Q = np.diag([30, 10])
R = np.array([[0.05]])
P = scipy.linalg.solve_discrete_are(A, B, Q, R)
K = np.linalg.inv(B.T @ P @ B + R) @ (B.T @ P @ A)

# Kalman filter parameters
Q_kalman = np.diag([0.01, 0.01])
R_kalman = np.array([[0.05]])
P_k = np.eye(2)

class StateEstimator:
    def __init__(self):
        self.X_k = np.array([[CENTER_COP], [0]])
        self.P_k = P_k
        self.fz_threshold = 20

    def read_forces(self):
        force_data = remote.get_force_data()
        if force_data is None:
            print("Warning: No force data received. Check the connection.")
            return 0, CENTER_COP

        fz = force_data.get('fz', 0)
        cop = force_data.get('copy', CENTER_COP)
        return fz, cop

    def kalman_update(self, cop_measured):
        """Kalman filter update step."""
        X_k_pred = A @ self.X_k
        P_k_pred = A @ self.P_k @ A.T + Q_kalman

        S_k = C @ P_k_pred @ C.T + R_kalman
        K_kalman = P_k_pred @ C.T @ np.linalg.inv(S_k)
        self.X_k = X_k_pred + K_kalman @ (cop_measured - C @ X_k_pred)
        self.P_k = (np.eye(2) - K_kalman @ C) @ P_k_pred

        return self.X_k

    def update(self):
        fz, cop_measured = self.read_forces()
        X_k = self.kalman_update(cop_measured)

        flag_step = fz > self.fz_threshold
        cop_avg = X_k[0, 0]
        dcom = X_k[1, 0]

        return flag_step, cop_avg, dcom, fz


class LQGController:
    def __init__(self, min_v=0.4, max_v=2.0):
        self.min_v = min_v
        self.max_v = max_v
        self.v_tm = min_v
        self.last_command_time = 0

    def compute_target_speed(self, flag_step, cop_avg, dcom, fz):
        """Compute treadmill speed from estimated COP."""
        if not flag_step:
            return self.v_tm

        v_target = 1.0 + 1.5 * (cop_avg - CENTER_COP) + CENTER_COP * dcom

        if fz > 50:
            v_target += 0.15
        elif fz < 25:
            v_target -= 0.1

        v_target = np.clip(v_target, self.min_v, self.max_v)

        # Apply smoothing when decelerating
        if v_target < self.v_tm:
            v_target = self.v_tm * (1 - DECELERATION_SMOOTHING) + v_target * DECELERATION_SMOOTHING

        return v_target

    def update_treadmill_speed(self, v_tm_tgt):
        """Update treadmill speed with rate limitation."""
        current_time = time.time()

        if abs(v_tm_tgt - self.v_tm) < 0.01:
            return

        if current_time - self.last_command_time < COMMAND_DELAY:
            return

        try:
            self.v_tm = v_tm_tgt
            remote.run_treadmill(
                f"{self.v_tm:.2f}", f"{DECELERATION_SMOOTHING:.2f}", f"{DECELERATION_SMOOTHING:.2f}",
                f"{self.v_tm:.2f}", f"{DECELERATION_SMOOTHING:.2f}", f"{DECELERATION_SMOOTHING:.2f}"
            )
            self.last_command_time = current_time
        except zmq.error.ZMQError as e:
            print(f"ZMQ Error while sending treadmill command: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


class TreadmillAIInterface(interface.TreadmillInterface):
    def __init__(self, estimator, controller):
        super().__init__()
        self.estimator = estimator
        self.controller = controller
        self.running = False
        self.step_counter = 0
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)

    def start(self):
        self.running = True
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self):
        self.running = False
        remote.run_treadmill(0, 0.2, 0.2, 0, 0.2, 0.2)

    def run(self):
        while self.running:
            flag_step, cop_avg, dcom, fz = self.estimator.update()

            force_data = remote.get_force_data()
            if force_data:
                copx = force_data.get('copx', 0)
                copy = force_data.get('copy', 0)

                self.update_cop(copx, copy)

            v_tm_tgt = self.controller.compute_target_speed(flag_step, cop_avg, dcom, fz)
            self.controller.update_treadmill_speed(v_tm_tgt)

            treadmill_acceleration = (v_tm_tgt - self.controller.v_tm) / dt
            if flag_step:
                self.step_counter += 1

            self.log_data(self.step_counter, self.controller.v_tm, treadmill_acceleration, copy, cop_avg)

            self.speed_label.setText(f'Current speed: {self.controller.v_tm:.2f} m/s')
            self.cop_x_label.setText(f"COP X: {copx:.2f} m")
            self.cop_y_label.setText(f"COP Y: {copy:.2f} m")

            time.sleep(0.01)


if __name__ == "__main__":
    app = interface.QApplication([])
    estimator = StateEstimator()
    controller = LQGController()
    gui = TreadmillAIInterface(estimator, controller)
    gui.show()
    app.exec_()
