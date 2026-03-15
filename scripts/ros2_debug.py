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
        "isaacsim.asset.importer.urdf",
        "isaacsim.core.nodes"
    ]
})

# 明示的な有効化のダメ押し
from isaacsim.core.utils.extensions import enable_extension
enable_extension("isaacsim.ros2.bridge")
enable_extension("isaacsim.core.nodes")

import omni.graph.core as og
import omni.kit.commands
from isaacsim.core.api import World
from isaacsim.core.prims import SingleArticulation

# --- 3. 5.1.0 向けのノードタイプ自動解決関数 ---
def get_node_type_name(base_name):
    """
    登録されている全ノードから、指定した名前を含むノードのフルパスを返す。
    例: 'ROS2PublishJointState' -> 'omni.isaac.ros2_bridge.ROS2PublishJointState'
    """
    # 5.1.0 のレジストリから取得
    reg = og.GraphRegistry()
    node_types = reg.get_node_types()
    for t in node_types:
        if base_name in t:
            return t
    return None

# ノードが登録されるまで最大10秒待機する
print("Searching for ROS 2 nodes in registry...")
import time
start_time = time.time()
NODE_PUB, NODE_SUB, NODE_CTRL = None, None, None

while time.time() - start_time < 10:
    NODE_PUB = get_node_type_name("ROS2PublishJointState")
    NODE_SUB = get_node_type_name("ROS2SubscribeJointState")
    NODE_CTRL = get_node_type_name("ROS2ArticulationController")
    
    if NODE_PUB and NODE_SUB and NODE_CTRL:
        print(f"Found nodes: {NODE_PUB}")
        break
    simulation_app.update()

if not NODE_PUB:
    print("FATAL: ROS 2 Nodes never appeared in registry. Check Extension Manager in GUI.")
    simulation_app.close()
    sys.exit()

# --- 4. URDF のインポート ---
current_dir = os.getcwd()
urdf_path = os.path.join(current_dir, "assets/isaac_sim_test_description/urdf/isaac_sim_test.urdf")
omni.kit.commands.execute("URDFParseAndImportFile", urdf_path=urdf_path, import_config=omni.kit.commands.execute("URDFCreateImportConfig")[1])

# --- 5. ワールド設定 ---
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()
robot_prim_path = "/isaac_sim_test"
robot = world.scene.add(SingleArticulation(prim_path=robot_prim_path, name="my_robot"))

# --- 6. ROS 2 OmniGraph の構築 ---
try:
    print(f"Creating ActionGraph using detected names...")
    og.Controller.edit(
        {"graph_path": "/ROS2_Bridge", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                ("PublishJointState", NODE_PUB),
                ("SubscribeJointMsg", NODE_SUB),
                ("ArticulationController", NODE_CTRL),
            ],
            og.Controller.Keys.CONNECT: [
                ("OnPlaybackTick.outputs:tick", "PublishJointState.inputs:execIn"),
                ("OnPlaybackTick.outputs:tick", "SubscribeJointMsg.inputs:execIn"),
                ("SubscribeJointMsg.outputs:execOut", "ArticulationController.inputs:execIn"),
                ("SubscribeJointMsg.outputs:jointNames", "ArticulationController.inputs:jointNames"),
                ("SubscribeJointMsg.outputs:positionCommand", "ArticulationController.inputs:positionCommand"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("PublishJointState.inputs:targetPrim", robot_prim_path),
                ("ArticulationController.inputs:targetPrim", robot_prim_path),
                ("SubscribeJointMsg.inputs:topicName", "/joint_commands"),
                ("PublishJointState.inputs:topicName", "/joint_states"),
            ],
        },
    )
    print("Graph setup complete!")
except Exception as e:
    print(f"Graph setup failed: {e}")

# 7. 実行
world.reset()
while simulation_app.is_running():
    world.step(render=True)

simulation_app.close()