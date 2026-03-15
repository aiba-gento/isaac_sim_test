from isaacsim import SimulationApp
import os

# 1. SimulationAppの初期化 (headless=TrueでGUIなし設定)
# プロンプトが出ないように、Configを渡すことも可能です
CONFIG = {"headless": False} # 動きを確認するために一旦False（GUIあり）にします
simulation_app = SimulationApp(CONFIG)

from omni.isaac.core import World
from omni.isaac.core.objects import DynamicCuboid
import numpy as np

# 2. ワールド（ステージ）の作成
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()

# 3. オブジェクト（立方体）の配置
# これを自分のロボットの資産（USD）に置き換えていくことになります
fancy_cube = world.scene.add(
    DynamicCuboid(
        prim_path="/World/Cube",
        name="my_cube",
        position=np.array([0, 0, 0.5]), # 地面から0.5m浮かす
        scale=np.array([1.0, 1.0, 1.0]),
        color=np.array([1.0, 0, 0]), # 赤色
    )
)

# 4. シミュレーションを数ステップ進める（物理演算の初期化）
world.reset()

for i in range(100):
    world.step(render=True)
    if i % 20 == 0:
        print(f"Step {i}: Cube is at {fancy_cube.get_world_pose()[0]}")

# 5. ステージをUSDファイルとして保存（GitHub管理対象のフォルダへ）
save_path = os.path.join(os.getcwd(), "assets", "created_scene.usda")
world.scene.stage.Export(save_path)
print(f"Saved stage to: {save_path}")

# 6. 終了
simulation_app.close()