import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _setup(context):
    name = LaunchConfiguration('name').perform(context)
    world = LaunchConfiguration('world').perform(context)
    bridge_clock = LaunchConfiguration('bridge_clock').perform(context).lower() == 'true'

    model_dir = os.path.join(get_package_share_directory('go2_sim'), 'models', 'go2')
    with open(os.path.join(model_dir, 'model.sdf')) as f:
        sdf_string = f.read().replace('model://go2/', f'file://{model_dir}/')

    create_args = [
        '-string', sdf_string,
        '-name', name,
        '-x', LaunchConfiguration('x').perform(context),
        '-y', LaunchConfiguration('y').perform(context),
        '-z', LaunchConfiguration('z').perform(context),
        '-Y', LaunchConfiguration('yaw').perform(context),
    ]
    if world:
        create_args += ['-world', world]

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=create_args,
        output='screen',
    )

    gz_model = f'/model/{name}'
    bridge_args = [
        f'{gz_model}/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
        f'{gz_model}/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry',
        f'{gz_model}/pose@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
    ]
    if bridge_clock:
        bridge_args.append('/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock')

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name=f'{name}_bridge',
        arguments=bridge_args,
        remappings=[
            (f'{gz_model}/cmd_vel', f'/{name}/cmd_vel'),
            (f'{gz_model}/odometry', f'/{name}/odom'),
            (f'{gz_model}/pose', '/tf'),
        ],
        output='screen',
    )

    world_frame = LaunchConfiguration('world_frame').perform(context)
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name=f'{name}_world_to_odom',
        arguments=['--frame-id', world_frame, '--child-frame-id', f'{name}/odom'],
        output='screen',
    )

    return [spawn, bridge, static_tf]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('name', default_value='go2',
                              description='Ime modela i ROS namespace'),
        DeclareLaunchArgument('world', default_value='',
                              description='Ime Gazebo svijeta (prazno = autodetekcija)'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='-1.0'),
        DeclareLaunchArgument('z', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('world_frame', default_value='world',
                              description='TF frame na koji se kaci go2/odom'),
        DeclareLaunchArgument('bridge_clock', default_value='false',
                              description='true = bridge i /clock (ako ga nitko drugi ne bridga)'),
        OpaqueFunction(function=_setup),
    ])