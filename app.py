"""Reading-FL Streamlit Cloud entry point.

Routes imports to the streamlit-cloud/reading-fl/ deployment directory.
"""
import sys
import os

# Add streamlit-cloud/reading-fl to sys.path so all imports resolve
_sc_dir = os.path.join(os.path.dirname(__file__), "streamlit-cloud", "reading-fl")
if os.path.isdir(_sc_dir) and _sc_dir not in sys.path:
    sys.path.insert(0, _sc_dir)

# Now import and run the actual streamlit app
# We exec the streamlit-cloud version's app.py in our namespace
_app_file = os.path.join(_sc_dir, "app.py")
with open(_app_file) as _f:
    _code = compile(_f.read(), _app_file, "exec")
exec(_code)
