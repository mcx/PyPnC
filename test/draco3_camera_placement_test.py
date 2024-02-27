import os
import sys
cwd = os.getcwd()
sys.path.append(cwd)
import time, math
from collections import OrderedDict
import copy
import signal
import shutil

import cv2
import pybullet as p
import numpy as np
np.set_printoptions(precision=2)

from config.draco3_config import SimConfig
from pnc.draco3_pnc.draco3_interface import Draco3Interface
from util import pybullet_util
from util import util
from util import liegroup


def set_initial_config(robot, joint_id):
    # Upperbody
    p.resetJointState(robot, joint_id["l_shoulder_aa"], np.pi / 6, 0.)
    p.resetJointState(robot, joint_id["l_elbow_fe"], -np.pi / 2, 0.)
    p.resetJointState(robot, joint_id["r_shoulder_aa"], -np.pi / 6, 0.)
    p.resetJointState(robot, joint_id["r_elbow_fe"], -np.pi / 2, 0.)
    p.resetJointState(robot, joint_id["l_wrist_pitch"], -np.pi / 10, 0.)
    p.resetJointState(robot, joint_id["r_wrist_pitch"], -np.pi / 10, 0.)
    # p.resetJointState(robot, joint_id["l_wrist_ps"], np.pi / 6, 0.)
    # p.resetJointState(robot, joint_id["r_wrist_ps"], -np.pi / 6, 0.)
    p.resetJointState(robot, joint_id["l_wrist_ps"], np.pi / 4, 0.)
    p.resetJointState(robot, joint_id["r_wrist_ps"], -np.pi / 4, 0.)

    # Lowerbody
    hip_yaw_angle = 5
    p.resetJointState(robot, joint_id["l_hip_aa"], np.radians(hip_yaw_angle),
                      0.)
    p.resetJointState(robot, joint_id["l_hip_fe"], -np.pi / 4, 0.)
    p.resetJointState(robot, joint_id["l_knee_fe_jp"], np.pi / 4, 0.)
    p.resetJointState(robot, joint_id["l_knee_fe_jd"], np.pi / 4, 0.)
    p.resetJointState(robot, joint_id["l_ankle_fe"], -np.pi / 4, 0.)
    p.resetJointState(robot, joint_id["l_ankle_ie"],
                      np.radians(-hip_yaw_angle), 0.)

    p.resetJointState(robot, joint_id["r_hip_aa"], np.radians(-hip_yaw_angle),
                      0.)
    p.resetJointState(robot, joint_id["r_hip_fe"], -np.pi / 4, 0.)
    p.resetJointState(robot, joint_id["r_knee_fe_jp"], np.pi / 4, 0.)
    p.resetJointState(robot, joint_id["r_knee_fe_jd"], np.pi / 4, 0.)
    p.resetJointState(robot, joint_id["r_ankle_fe"], -np.pi / 4, 0.)
    p.resetJointState(robot, joint_id["r_ankle_ie"], np.radians(hip_yaw_angle),
                      0.)


def signal_handler(signal, frame):
    if SimConfig.VIDEO_RECORD:
        pybullet_util.make_video(video_dir, False)
    p.disconnect()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":

    # Environment Setup
    p.connect(p.GUI)
    p.resetDebugVisualizerCamera(cameraDistance=1.0,
                                 cameraYaw=120,
                                 cameraPitch=-30,
                                 cameraTargetPosition=[1, 0.5, 1.0])
    p.setGravity(0, 0, -9.8)
    p.setPhysicsEngineParameter(fixedTimeStep=SimConfig.CONTROLLER_DT,
                                numSubSteps=SimConfig.N_SUBSTEP)
    if SimConfig.VIDEO_RECORD:
        video_dir = 'video/draco3_pnc'
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)
        os.makedirs(video_dir)

    if SimConfig.SIMULATE_CAMERA and SimConfig.SAVE_CAMERA_DATA:
        l_camera_dir = 'data/draco3/l_camera'
        r_camera_dir = 'data/draco3/r_camera'
        if os.path.exists(l_camera_dir):
            shutil.rmtree(l_camera_dir)
        os.makedirs(l_camera_dir)
        if os.path.exists(r_camera_dir):
            shutil.rmtree(r_camera_dir)
        os.makedirs(r_camera_dir)

    # Create Robot, Ground
    p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)
    robot = p.loadURDF(cwd + "/robot_model/draco3/draco3_pin_model.urdf",
                       SimConfig.INITIAL_POS_WORLD_TO_BASEJOINT,
                       SimConfig.INITIAL_QUAT_WORLD_TO_BASEJOINT)
    stair = p.loadURDF(cwd + "/robot_model/ground/stair.urdf", [0.2, 0, 0.],
                       useFixedBase=True)

    p.loadURDF(cwd + "/robot_model/ground/plane.urdf", [0, 0, 0])
    p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1)
    nq, nv, na, joint_id, link_id, pos_basejoint_to_basecom, rot_basejoint_to_basecom = pybullet_util.get_robot_config(
        robot, SimConfig.INITIAL_POS_WORLD_TO_BASEJOINT,
        SimConfig.INITIAL_QUAT_WORLD_TO_BASEJOINT, SimConfig.PRINT_ROBOT_INFO)

    # Add Gear constraint
    c = p.createConstraint(robot,
                           link_id['l_knee_fe_lp'],
                           robot,
                           link_id['l_knee_fe_ld'],
                           jointType=p.JOINT_GEAR,
                           jointAxis=[0, 1, 0],
                           parentFramePosition=[0, 0, 0],
                           childFramePosition=[0, 0, 0])
    p.changeConstraint(c, gearRatio=-1, maxForce=500, erp=10)

    c = p.createConstraint(robot,
                           link_id['r_knee_fe_lp'],
                           robot,
                           link_id['r_knee_fe_ld'],
                           jointType=p.JOINT_GEAR,
                           jointAxis=[0, 1, 0],
                           parentFramePosition=[0, 0, 0],
                           childFramePosition=[0, 0, 0])
    p.changeConstraint(c, gearRatio=-1, maxForce=500, erp=10)

    # Initial Config
    set_initial_config(robot, joint_id)

    # Link Damping
    pybullet_util.set_link_damping(robot, link_id.values(), 0., 0.)

    # Joint Friction
    pybullet_util.set_joint_friction(robot, joint_id, 0)

    # Construct Interface
    interface = Draco3Interface()

    # Run Sim
    t = 0
    dt = SimConfig.CONTROLLER_DT
    count = 0
    jpg_count = 0
    l_camera_jpg_count = 0
    r_camera_jpg_count = 0

    nominal_sensor_data = pybullet_util.get_sensor_data(
        robot, joint_id, link_id, pos_basejoint_to_basecom,
        rot_basejoint_to_basecom)

    # Draw Camera Link
    pybullet_util.draw_link_frame(robot, link_id['r_camera'], text="r_camera")
    pybullet_util.draw_link_frame(robot, link_id['l_camera'], text="l_camera")

    while (1):

        # Get SensorData
        if SimConfig.SIMULATE_CAMERA and count % (
                SimConfig.CAMERA_DT / SimConfig.CONTROLLER_DT) == 0:
            l_camera_img = pybullet_util.get_camera_image_from_link(
                robot, link_id['l_camera'], 50, 10, 60., 0.1, 10)
            # r_camera_img = pybullet_util.get_camera_image_from_link(
                # robot, link_id['r_camera'], 50, 10, 60., 0.1, 10)

            if SimConfig.SAVE_CAMERA_DATA:
                l_camera_img = l_camera_img[2][:, :, [2, 1,
                                                      0]]  # << RGB to BGR
                l_filename = l_camera_dir + '/step%06d.jpg' % l_camera_jpg_count
                cv2.imwrite(l_filename, l_camera_img)
                l_camera_jpg_count += 1

                r_camera_img = r_camera_img[2][:, :, [2, 1,
                                                      0]]  # << RGB to BGR
                r_filename = r_camera_dir + '/step%06d.jpg' % l_camera_jpg_count
                cv2.imwrite(r_filename, r_camera_img)
                r_camera_jpg_count += 1

        sensor_data = pybullet_util.get_sensor_data(robot, joint_id, link_id,
                                                    pos_basejoint_to_basecom,
                                                    rot_basejoint_to_basecom)

        rf_height = pybullet_util.get_link_iso(robot,
                                               link_id['r_foot_contact'])[2, 3]
        lf_height = pybullet_util.get_link_iso(robot,
                                               link_id['l_foot_contact'])[2, 3]
        sensor_data['b_rf_contact'] = True if rf_height <= 0.01 else False
        sensor_data['b_lf_contact'] = True if lf_height <= 0.01 else False

        # Get Keyboard Event
        keys = p.getKeyboardEvents()
        if pybullet_util.is_key_triggered(keys, '8'):
            interface.interrupt_logic.b_interrupt_button_eight = True
        elif pybullet_util.is_key_triggered(keys, '5'):
            interface.interrupt_logic.b_interrupt_button_five = True
        elif pybullet_util.is_key_triggered(keys, '4'):
            interface.interrupt_logic.b_interrupt_button_four = True
        elif pybullet_util.is_key_triggered(keys, '2'):
            interface.interrupt_logic.b_interrupt_button_two = True
        elif pybullet_util.is_key_triggered(keys, '6'):
            interface.interrupt_logic.b_interrupt_button_six = True
        elif pybullet_util.is_key_triggered(keys, '7'):
            interface.interrupt_logic.b_interrupt_button_seven = True
        elif pybullet_util.is_key_triggered(keys, '9'):
            interface.interrupt_logic.b_interrupt_button_nine = True
        elif pybullet_util.is_key_triggered(keys, '0'):
            interface.interrupt_logic.b_interrupt_button_zero = True

        # Compute Command
        if SimConfig.PRINT_TIME:
            start_time = time.time()
        command = interface.get_command(copy.deepcopy(sensor_data))

        if SimConfig.PRINT_TIME:
            end_time = time.time()
            print("ctrl computation time: ", end_time - start_time)

        # Exclude Knee Distal Joints Command
        del command['joint_pos']['l_knee_fe_jd']
        del command['joint_pos']['r_knee_fe_jd']
        del command['joint_vel']['l_knee_fe_jd']
        del command['joint_vel']['r_knee_fe_jd']
        del command['joint_trq']['l_knee_fe_jd']
        del command['joint_trq']['r_knee_fe_jd']

        # Apply Command
        pybullet_util.set_motor_trq(robot, joint_id, command['joint_trq'])

        # Save Image
        if (SimConfig.VIDEO_RECORD) and (count % SimConfig.RECORD_FREQ == 0):
            frame = pybullet_util.get_camera_image([1., 0.5, 1.], 1.0, 120,
                                                   -15, 0, 60., 1920, 1080,
                                                   0.1, 100.)
            frame = frame[:, :, [2, 1, 0]]  # << RGB to BGR
            filename = video_dir + '/step%06d.jpg' % jpg_count
            cv2.imwrite(filename, frame)
            jpg_count += 1

        p.stepSimulation()

        time.sleep(dt)
        t += dt
        count += 1
