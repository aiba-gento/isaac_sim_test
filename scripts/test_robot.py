from isaacsim import SimulationApp
import numpy as np

# 1. 起動
simulation_app = SimulationApp({"headless": False})

from isaacsim.core.api import World
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.core.prims import SingleArticulation
from isaacsim.core.utils.types import ArticulationAction  # これが必要！
import omni.kit.commands
import os

# 2. URDFインポーター有効化
enable_extension("isaacsim.asset.importer.urdf")

# 3. パス設定
current_dir = os.getcwd()
urdf_path = os.path.join(current_dir, "assets/isaac_sim_test_description/urdf/isaac_sim_test.urdf")

# 4. インポート設定と実行
status, import_config = omni.kit.commands.execute("URDFCreateImportConfig")
import_config.merge_fixed_joints = False
import_config.fix_base = True
import_config.make_default_prim = True

omni.kit.commands.execute("URDFParseAndImportFile", urdf_path=urdf_path, import_config=import_config)

# 5. ワールド設定
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()

# 6. ロボットの登録
# URDFのロボット名が isaac_sim_test なら、パスは /isaac_sim_test になります
robot = world.scene.add(SingleArticulation(prim_path="/isaac_sim_test", name="my_robot"))

world.reset()

print("Robot Control Started. Looking for movement on joint_1...")

i = 0
while simulation_app.is_running():
    world.step(render=True)
    
    if world.is_playing():
        # 目標位置の計算 (ラジアン単位)
        target_pos = np.sin(i * 0.05) * 1.5  # 約85度程度まで往復
        
        # ロボットの全関節数に合わせた配列を作成
        num_dof = robot.num_dof
        joint_positions = np.zeros(num_dof)
        joint_positions[0] = target_pos # joint_1 を操作
        
        # 【重要】ArticulationAction オブジェクトに包んで送信
        action = ArticulationAction(joint_positions=joint_positions)
        robot.apply_action(action)
        
        if i % 100 == 0:
            print(f"Step {i}: joint_1 target -> {target_pos:.2f}")
        i += 1

simulation_app.close()