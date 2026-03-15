from isaacsim import SimulationApp
# 起動。物理を正しく計算させるためGUIありにする
simulation_app = SimulationApp({"headless": False})
from isaacsim.core.api import World

# 5. ワールド設定
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()

while simulation_app.is_running():
    simulation_app.update()  # 物理シミュレーションを更新

simulation_app.close()