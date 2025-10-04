import dearpygui.dearpygui as dpg
import pydevd_pycharm

def test_callback(sender, app_data, user_data):
    pydevd_pycharm.settrace(suspend=True, trace_only_current_thread=True)
    x = 42  # breakpoint here
    print("callback hit", x)

dpg.create_context()
with dpg.window(label="Test"):
    dpg.add_button(label="Click me", callback=test_callback)
dpg.create_viewport(title="Test", width=300, height=200)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()