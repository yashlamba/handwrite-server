import os
import shutil
import tempfile
import gc
import time
from uuid import uuid4
import subprocess
import logging


import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage

logger = logging.getLogger("background")

use_firebase = False
if os.path.exists("firebasekey.json"):
    use_firebase = True
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebasekey.json")
        firebase_admin.initialize_app(cred)

    bucket = storage.bucket("handwrite-2bb53.appspot.com")

CURRENT_Q = []  # TODO Use Queue?


def handwrite_background():
    try:
        server_dir = os.path.dirname(os.path.abspath(__file__))
        dirs = {}

        for dir_name in ["infiles", "outfiles", "status", "error"]:
            dirs[dir_name] = os.path.join(server_dir, dir_name)
            shutil.rmtree(dirs[dir_name], ignore_errors=True)
            os.makedirs(dirs[dir_name])
            logger.debug(f"Created directory: {dirs[dir_name]}")

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
                logger.debug(f"Started font creation {name}")
                image_name = name + ".jpg"
                temp_dir = tempfile.mkdtemp()
                os.makedirs(dirs["outfiles"] + os.sep + name)

                try:
                    logger.info(f"Calling handwrite for {name}")
                    subprocess.check_output(
                        [
                            "handwrite",
                            dirs["infiles"] + os.sep + image_name,
                            dirs["outfiles"] + os.sep + name,
                            "--directory",
                            temp_dir,
                            "--config",
                            os.path.dirname(os.path.abspath(__file__))
                            + "/default.json",
                        ]
                    )

                    if use_firebase:
                        try:
                            logger.info(f"Firebase Upload Started {name}")
                            metadata = {"firebaseStorageDownloadTokens": uuid4()}
                            blob = bucket.blob(name)
                            blob.metadata = metadata
                            blob.upload_from_filename(
                                dirs["infiles"] + os.sep + image_name
                            )
                            logger.debug(f"Firebase Upload Successful {name}")
                        except:
                            logger.error(f"Firebase Upload Failed {name}")
                    logger.debug(f"Font Generation Complete {name}")

                except:
                    open(dirs["error"] + os.sep + name, "w").close()
                    logger.info(f"Unable to process Image: {name}")

                os.remove(dirs["infiles"] + os.sep + image_name)
                os.remove(dirs["status"] + os.sep + name)
                shutil.rmtree(temp_dir)
                logger.debug(f"Post Process Cleanup Completed {name}")

                # count += 1

            # if count == 6:
            # gc.collect()
            # count = 0

            if (time.time() - prev_time) / 60 > 2:
                for dir_name in ["outfiles", "error"]:
                    for fd in os.listdir(dirs[dir_name]):
                        path = dirs[dir_name] + os.sep + fd
                        if (time.time() - os.stat(path).st_mtime) / 60 > 10:
                            logger.info(f"Deleting (Timeout): {path}")
                            if dir_name == "outfiles":
                                shutil.rmtree(path)
                            else:
                                os.remove(path)
                prev_time = time.time()

            time.sleep(0.1)
    except:
        logger.exception("Background Service Crashed")
