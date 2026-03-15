import os
import sys

# --- 1. 環境変数の設定 ---
ISAAC_ROOT = "/home/gn10/isaac_sim_test/isaac_sim"
ROS_LIB_PATH = os.path.join(ISAAC_ROOT, "exts/isaacsim.ros2.bridge/humble/lib")

os.environ["ROS_DISTRO"] = "humble"
os.environ["RMW_IMPLEMENTATION"] = "rmw_fastrtps_cpp"
os.environ["LD_LIBRARY_PATH"] = f"{ROS_LIB_PATH}:" + os.environ.get("LD_LIBRARY_PATH", "")
os.environ["AMENT_PREFIX_PATH"] = os.path.join(ISAAC_ROOT, "exts/isaacsim.ros2.bridge/humble")

from isaacsim import SimulationApp

# --- 2. SimulationApp の起動 ---
simulation_app = SimulationApp({
    "headless": False,
    "exts": [
        "isaacsim.ros2.bridge",
        "isaacsim.asset.importer.urdf"
    ]
})

from isaacsim.core.api import World
from isaacsim.core.prims import SingleArticulation
import omni.kit.commands
import omni.graph.core as og

# --- 3. 初期化待機 ---
print("Waiting for ROS 2 Bridge to initialize...")
for _ in range(100):
    simulation_app.update()

# --- 4. URDF のインポート ---
current_dir = os.getcwd()
urdf_path = os.path.join(current_dir, "assets/isaac_sim_test_description/urdf/isaac_sim_test.urdf")

status, import_config = omni.kit.commands.execute("URDFCreateImportConfig")
import_config.merge_fixed_joints = False
import_config.fix_base = True
import_config.make_default_prim = True

print(f"Importing URDF: {urdf_path}")
omni.kit.commands.execute("URDFParseAndImportFile", urdf_path=urdf_path, import_config=import_config)

# --- 5. ワールドとロボットの設定 ---
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()

robot_prim_path = "/isaac_sim_test"
robot = world.scene.add(SingleArticulation(prim_path=robot_prim_path, name="my_robot"))

# --- 6. ROS 2 OmniGraph の構築 ---
def create_ros2_graph(prefix):
    """指定したプレフィックスでグラフ作成を試みる"""
    keys = og.Controller.Keys
    og.Controller.edit(
        {"graph_path": "/ROS2_Bridge", "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                ("PublishJointState", f"{prefix}.ROS2PublishJointState"),
                ("SubscribeJointMsg", f"{prefix}.ROS2SubscribeJointState"),
                ("ArticulationController", f"{prefix}.ROS2ArticulationController"),
            ],
            keys.CONNECT: [
                ("OnPlaybackTick.outputs:tick", "PublishJointState.inputs:execIn"),
                ("OnPlaybackTick.outputs:tick", "SubscribeJointMsg.inputs:execIn"),
                ("SubscribeJointMsg.outputs:execOut", "ArticulationController.inputs:execIn"),
                ("SubscribeJointMsg.outputs:jointNames", "ArticulationController.inputs:jointNames"),
                ("SubscribeJointMsg.outputs:positionCommand", "ArticulationController.inputs:positionCommand"),
            ],
            keys.SET_VALUES: [
                ("PublishJointState.inputs:targetPrim", robot_prim_path),
                ("ArticulationController.inputs:targetPrim", robot_prim_path),
                ("SubscribeJointMsg.inputs:topicName", "/joint_commands"),
                ("PublishJointState.inputs:topicName", "/joint_states"),
            ],
        },
    )

# 5.1.0で可能性が高い順にトライします
prefixes = ["omni.isaac.ros2_bridge", "isaacsim.ros2.bridge"]
success = False

for p in prefixes:
    try:
        print(f"Trying to create ROS 2 Bridge with prefix: {p}")
        create_ros2_graph(p)
        print(f"Successfully created graph with {p}")
        success = True
        break
    except Exception as e:
        print(f"Failed with prefix {p}. Error: {e}")
        # 次のプレフィックスを試す前にグラフをクリア（もし作成されかけていたら）
        omni.kit.commands.execute("DeletePrims", paths=["/ROS2_Bridge"])

if not success:
    print("Critical Error: Could not find valid ROS 2 Bridge node types.")

# シミュレーション開始
world.reset()
print("--- ROS 2 Bridge Ready ---")

while simulation_app.is_running():
    world.step(render=True)

simulation_app.close()