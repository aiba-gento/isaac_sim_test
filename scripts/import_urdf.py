from isaacsim import SimulationApp
# 起動。物理を正しく計算させるためGUIありにする
simulation_app = SimulationApp({"headless": False})

from omni.isaac.core import World
from omni.isaac.core.utils.extensions import enable_extension
import omni.kit.commands
import os

# URDFインポーターを有効化
enable_extension("omni.importer.urdf")

# パスの設定 (自分の環境に合わせて)
current_dir = os.getcwd()
urdf_path = os.path.join(current_dir, "assets/isaac_sim_test_description/urdf/isaac_sim_test.urdf")

# 1. インポート設定の作成
status, import_config = omni.kit.commands.execute("URDFCreateImportConfig")
import_config.merge_fixed_joints = False
import_config.fix_base = True      # base_linkを空中に固定
import_config.make_default_prim = True
import_config.create_physics_scene = True

# 2. URDFの読み込みとUSDへの変換
# 変換後のUSDを meshes フォルダの横に保存するように設定
omni.kit.commands.execute(
    "URDFParseAndImportFile",
    urdf_path=urdf_path,
    import_config=import_config,
)

# 3. シミュレーションワールドの設定
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()

# シミュレーション開始
world.reset()

print("Robot Import Complete. Press Ctrl+C to stop.")
while simulation_app.is_running():
    world.step(render=True)

simulation_app.close()