import os
import shutil
import tempfile
import gc
import time
from uuid import uuid4

from handwrite.cli import converters

import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage

if not firebase_admin._apps:
    cred = credentials.Certificate("firebasekey.json")
    firebase_admin.initialize_app(cred)

bucket = storage.bucket("handwrite-2bb53.appspot.com")

CURRENT_Q = []  # TODO Use Queue?


def handwrite_background():
    server_dir = os.path.dirname(os.path.abspath(__file__))
    dirs = {}

    for dir_name in ["infiles", "outfiles", "status", "error"]:
        dirs[dir_name] = os.path.join(server_dir, dir_name)
        shutil.rmtree(dirs[dir_name], ignore_errors=True)
        os.makedirs(dirs[dir_name])

    prev_time = time.time()
    count = 0
    while True:
        # TODO
        # We are processing one at a time
        # in batches of 3, these batches are for
        # future threading support.
        if len(CURRENT_Q) == 0:
            mtime = lambda x: os.stat(dirs["status"] + os.sep + x).st_mtime
            files = sorted(os.listdir(dirs["status"]), key=mtime)
            while len(CURRENT_Q) < 4 and files:
                CURRENT_Q.append(files.pop(0))

        if CURRENT_Q:
            name = CURRENT_Q.pop(0)
            image_name = name + ".jpg"
            temp_dir = tempfile.mkdtemp()
            os.makedirs(dirs["outfiles"] + os.sep + name)
            try:
                converters(
                    dirs["infiles"] + os.sep + image_name,
                    temp_dir,
                    dirs["outfiles"] + os.sep + name,
                    os.path.dirname(os.path.abspath(__file__)) + "/default.json",
                )
                try:
                    metadata = {"firebaseStorageDownloadTokens": uuid4()}
                    blob = bucket.blob(name)
                    blob.metadata = metadata
                    blob.upload_from_filename(dirs["infiles"] + os.sep + image_name)
                except:
                    print(f"Image Upload Failed: {image_name}")
            except:
                open(dirs["error"] + os.sep + name, "w").close()
                print(f"Unable to process Image: {image_name}")
            os.remove(dirs["infiles"] + os.sep + image_name)
            os.remove(dirs["status"] + os.sep + name)
            shutil.rmtree(temp_dir)
            count += 1

        if count == 6:
            gc.collect()
            count = 0

        if (time.time() - prev_time) / 60 > 2:
            for dir_name in ["outfiles", "error"]:
                for fd in os.listdir(dirs[dir_name]):
                    path = dirs[dir_name] + os.sep + fd
                    if (time.time() - os.stat(path).st_mtime) / 60 > 5:
                        print(f"Deleting: {path}")
                        if dir_name == "outfiles":
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
            prev_time = time.time()
