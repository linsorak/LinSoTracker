import os
import sys
import tempfile
import glob
import time
from zipfile import ZipFile


def launch_app(path):
    if os.path.exists(path):
        os.startfile(path)


def main():
    args = sys.argv[1:]
    temp_path = tempfile.gettempdir()
    app_name = "LinSoTracker"
    time.sleep(2)

    if len(args) > 1 and args[0] == "-exe_path":
        app_path = args[1]

        if sys.platform == "win32":
            temp_path = os.path.join(temp_path, app_name)
            app_name += ".exe"
        else:
            temp_path = os.path.expanduser(os.path.join(temp_path, app_name))
            app_name += ".app"

        update_dir = os.path.join(temp_path, "Update")
        tracker_path = os.path.join(app_path, app_name)

        if os.path.exists(update_dir):
            for patch in glob.glob(os.path.join(update_dir, "*.ltp")):
                try:
                    if os.path.isfile(patch):
                        zip = ZipFile(patch)
                        zip.extractall(app_path)
                        zip.close()
                        os.remove(patch)
                except:
                    pass

        launch_app(tracker_path)


if __name__ == '__main__':
    main()
