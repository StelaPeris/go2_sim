# go2_sim

Kinematički Unitree Go2 za Crazyflie simulaciju (CrazySim + `mrs_crazyflies`) u Gazebo Garden.
Pas se upravlja isključivo preko `cmd_vel` (`geometry_msgs/Twist`), bez simulacije nogu:
Gazebov `VelocityControl` plugin pomiče model, a `OdometryPublisher` daje odometriju i TF.

- Model: pravi Go2 meshevi (Unitree `go2_description`), noge fiksne u stojećoj pozi
- Gravitacija isključena (pas drži visinu), kolizija samo za trup
- Ne usporava fiziku dronova i ne treba `ros2_control`

## Okruženje

| | Verzija |
|---|---|
| OS | Ubuntu 22.04 |
| ROS 2 | Humble |
| Gazebo | Garden (gz-sim 7) |
| Crazyflie sim | CrazySim + Crazyswarm2 + `mrs_crazyflies` |

Workspace se gradi s `--merge-install`, putanje u nastavku pretpostavljaju `~/ros2_ws`.

## Instalacija

### 1. `ros_gz` za Garden (iz sourcea)

Apt paketi `ros-humble-ros-gz-*` su građeni za Ignition Fortress i **ne vide** Garden topice.
Bridge zato treba buildati iz sourcea s `GZ_VERSION=garden`:

```bash
echo 'export GZ_VERSION=garden' >> ~/.bashrc
export GZ_VERSION=garden

cd ~/ros2_ws/src
git clone https://github.com/gazebosim/ros_gz.git -b humble

cd ~/ros2_ws
colcon build --merge-install --packages-select ros_gz_interfaces ros_gz_bridge ros_gz_sim \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

> Ne pokretati `rosdep install` za `ros_gz`, jer povlači Fortress pakete.

Provjera, mora pisati `libgz-transport12` / `libgz-msgs9` (ne `ignition-transport11`):

```bash
ldd $(ros2 pkg prefix ros_gz_bridge)/lib/ros_gz_bridge/parameter_bridge | grep -E "transport|gz-msgs"
```

Provjera dok simulacija radi:

```bash
ros2 run ros_gz_bridge parameter_bridge /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock
ros2 topic echo /clock --once   # u drugom terminalu
```

### 2. Ostale ROS ovisnosti

```bash
apt update
apt install -y ros-humble-teleop-twist-keyboard ros-humble-tf2-ros mesa-utils
```

### 3. Klon i Go2 meshevi

```bash
cd ~/ros2_ws/src
git clone https://github.com/StelaPeris/go2_sim.git go2_sim
```

Meshevi su iz [unitree_ros](https://github.com/unitreerobotics/unitree_ros) (BSD-3, Unitree Robotics).
Ako nisu u repou, skini ih:

```bash
cd /tmp
git clone --depth 1 --filter=blob:none --sparse https://github.com/unitreerobotics/unitree_ros.git
cd unitree_ros && git sparse-checkout set robots/go2_description
mkdir -p ~/ros2_ws/src/go2_sim/models/go2/meshes
cp robots/go2_description/dae/*.dae ~/ros2_ws/src/go2_sim/models/go2/meshes/
cp LICENSE ~/ros2_ws/src/go2_sim/models/go2/meshes/LICENSE_unitree
rm -rf /tmp/unitree_ros
```

### 4. Build

```bash
cd ~/ros2_ws
colcon build --merge-install --packages-select go2_sim
source install/setup.bash
```

> Ne miješati build sa i bez `--symlink-install` za isti paket. Ako colcon javi
> `failed to create symbolic link ... Is a directory`, obriši `build/<paket>` i ponovi build.

## Pokretanje

### Pas u već pokrenutu simulaciju

Pokreni dronove kao inače (`mrs_crazyflies`), pa:

```bash
ros2 launch go2_sim spawn_go2.launch.py
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap cmd_vel:=/go2/cmd_vel
```

Launch argumenti:

| Argument | Default | Opis |
|---|---|---|
| `name` | `go2` | ime modela i ROS namespace |
| `x`, `y`, `z`, `yaw` | `0`, `-1`, `0`, `0` | početna poza |
| `world` | *(prazno)* | ime Gazebo svijeta, prazno = autodetekcija |
| `world_frame` | `world` | TF frame na koji se kači `<name>/odom` |
| `bridge_clock` | `false` | bridge i `/clock` ako ga nitko drugi ne bridga |

### Sve zajedno (tmuxinator)

`startup/cf_go2.yml` je kopija `mrs_crazyflies` sessiona s dodanim prozorom za psa.
Pokreće se iz `go2_sim/startup` foldera, naredbom:

```bash
./start.sh
```

## Topici

| Topic | Tip | Smjer |
|---|---|---|
| `/go2/cmd_vel` | `geometry_msgs/Twist` | ROS → Gazebo |
| `/go2/odom` | `nav_msgs/Odometry` | Gazebo → ROS |
| `/tf` | `go2/odom → go2/base_link` | Gazebo → ROS |
| `/tf_static` | `world → go2/odom` (identitet) | launch |

Brzine su u koordinatnom sustavu tijela: `linear.x` naprijed, `linear.y` bočno, `angular.z` okretanje.

Provjera TF-a:

```bash
ros2 run tf2_ros tf2_echo world go2/base_link
```

## Struktura

```
go2_sim/
├── launch/spawn_go2.launch.py   # spawn u postojeći svijet + bridge + static TF
├── models/go2/
│   ├── model.sdf                # Go2 meshevi u stojećoj pozi + pluginovi
│   ├── model.config
│   └── meshes/*.dae             # Unitree Go2 meshevi
└── startup/cf_go2.yml           # tmuxinator session: dronovi + pas
```

## Česti problemi

- **Pas se ne pojavi / `create` ne nađe svijet**: zadaj `world:=<ime>` (ime iz `gz topic -l`, `/world/<ime>/...`).
- **Pas nevidljiv, ali postoji**: meshevi nisu u `models/go2/meshes/` ili paket nije rebuildan nakon dodavanja.
- **`No transform from go2/base_link to world`**: koristi se stara verzija launcha bez static TF-a, ili je glavni frame drugačiji (`world_frame:=map`).
- **`cmd_vel` ne pomiče psa**: bridge je Fortress verzija, vidi korak 1.
- **Dodatni Crazyflie vidljiv u Gazebu, ali ne u ROS-u/RVizu**: dodaj ga i u Crazyswarm2 yaml koji čita `crazyflie_server`
  (svoj `uri`, npr. `udp://0.0.0.0:19851` za drugi), rebuildaj `mrs_crazyflies` i provjeri da se slaže sa `SPAWN_POSE_DOC`.

## Pravi robot

Kontroler komunicira samo preko `/go2/cmd_vel` i `/go2/odom`, pa se za pravog Go2 mijenja samo driver
(službeni `unitree_ros2` za Go2 EDU ili community `go2_ros2_sdk`), uz remap na iste topice.
Za pravog robota isključiti `ROS_LOCALHOST_ONLY` i uskladiti `ROS_DOMAIN_ID` i CycloneDDS sučelje s psom.

## Licenca

Kod: Apache-2.0. Go2 meshevi: BSD-3, Unitree Robotics (`models/go2/meshes/LICENSE_unitree`).