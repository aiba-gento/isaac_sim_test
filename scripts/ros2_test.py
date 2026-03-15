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

# 明示的にさらに有効化を叩く
from omni.isaac.core.utils.extensions import enable_extension
enable_extension("isaacsim.ros2.bridge")

from isaacsim.core.api import World
from isaacsim.core.prims import SingleArticulation
import omni.kit.commands
import omni.graph.core as og

# --- 3. 強力な待機と強制アップデート ---
print("Forcing extension registration...")
for _ in range(120): # 2秒程度
    simulation_app.update()

# --- 4. URDF のインポート ---
current_dir = os.getcwd()
urdf_path = os.path.join(current_dir, "assets/isaac_sim_test_description/urdf/isaac_sim_test.urdf")
omni.kit.commands.execute("URDFParseAndImportFile", urdf_path=urdf_path, import_config=omni.kit.commands.execute("URDFCreateImportConfig")[1])

# --- 5. ワールドとロボットの設定 ---
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()
robot_prim_path = "/isaac_sim_test"
robot = world.scene.add(SingleArticulation(prim_path=robot_prim_path, name="my_robot"))

# --- 6. ROS 2 OmniGraph の構築 (全プレフィックス網羅) ---
def setup_bridge_graph():
    graph_path = "/ROS2_Bridge"
    keys = og.Controller.Keys
    
    # 5.1.0/4.x/2023.x 全てのパターンを試します
    possible_prefixes = [
        "isaacsim.ros2.bridge",    # 5.x 推奨
        "omni.isaac.ros2_bridge",  # 4.x / 5.x 内部名
        "omni.isaac.ros_bridge"    # 旧互換名
    ]
    
    for p in possible_prefixes:
        try:
            print(f"Trying prefix: {p}")
            og.Controller.edit(
                {"graph_path": graph_path, "evaluator_name": "execution"},
                {
                    keys.CREATE_NODES: [
                        ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                        ("PublishJointState", f"{p}.ROS2PublishJointState"),
                        ("SubscribeJointMsg", f"{p}.ROS2SubscribeJointState"),
                        ("ArticulationController", f"{p}.ROS2ArticulationController"),
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
            print(f"Success with prefix: {p}")
            return True
        except Exception:
            omni.kit.commands.execute("DeletePrims", paths=[graph_path])
    return False

if not setup_bridge_graph():
    # 最終デバッグ：登録されている全てのノードタイプからROS2を探して表示する
    print("FATAL: Searching all registered nodes...")
    all_nodes = og.get_all_node_types()
    ros2_nodes = [n for n in all_nodes if "ROS2" in n]
    print(f"Found ROS2 nodes in registry: {ros2_nodes}")

world.reset()
while simulation_app.is_running():
    world.step(render=True)
simulation_app.close()