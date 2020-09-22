import numpy as np

from config.atlas_config import PnCConfig, WBCConfig
from pnc.wbc.wbc import WBC
from pnc.wbc.joint_integrator import JointIntegrator


class AtlasController(object):
    def __init__(self, tf_container, robot):
        self._tf_container = tf_container
        self._robot = robot

        # Initialize WBC
        act_list = [False] * robot.n_virtual + [True] * robot.n_a
        self._wbc = WBC(act_list)
        if WBCConfig.B_TRQ_LIMIT:
            self._wbc.trq_limit = self._robot.joint_trq_limit
        else:
            self._wbc.trq_limit = None
        self._wbc.lambda_qddot = WBCConfig.LAMBDA_QDDOT
        self._wbc.lambda_fr = WBCConfig.LAMBDA_FR
        # Initialize Joint Integrator
        self._joint_integrator = JointIntegrator(robot.n_a, PnCConfig.DT)
        self._joint_integrator.pos_cutoff_freq = WBCConfig.POS_CUTOFF_FREQ
        self._joint_integrator.vel_cutoff_freq = WBCConfig.VEL_CUTOFF_FREQ
        self._joint_integrator.max_pos_err = WBCConfig.MAX_POS_ERR
        self._joint_integrator.joint_pos_limit = self._robot.joint_pos_limit
        self._joint_integrator.joint_vel_limit = self._robot.joint_vel_limit

    def get_command(self):
        # Dynamics properties
        A = robot.get_mass_matrix
        A_inv = np.linalg.inv(A)
        coriolis = robot.get_coriolis()
        gravity = robot.get_gravity()
        self._wbc.update_setting(A, Ainv, coriolis, gravity)
        # Task and Contact Setup
        for task in self._tf_container._task_list:
            task.update_jacobian()
            task.compute_command()
        for contact in self._tf_container._contact_list:
            contact.update_contact()
        # WBC commands
        joint_trq_cmd, joint_acc_cmd = self._wbc.solve(task_list, contact_list)
        # Double integration
        joint_vel_cmd, joint_pos_cmd = self._joint_acc_cmd.integrate(
            joint_acc_cmd,
            self._robot.get_qdot()[self._robot.n_virtual:self._robot.n_a],
            self._robot.get_q()[self._robot.n_virtual:self._robot.n_a])

        command = dict()
        command["joint_pos"] = joint_pos_cmd
        command["joint_vel"] = joint_vel_cmd
        command["joint_trq"] = joint_trq_cmd

        return command

    def first_visit(self):
        joint_pos_ini = self._robot.get_q()[self._robot.n_virtual:self._robot.
                                            n_a]
        self._joint_integrator.intialize(np.zeros(self._robot.n_a),
                                         joint_pos_ini)
