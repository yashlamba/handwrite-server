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

bucket = storage.bucket('handwrite-2bb53.appspot.com')

CURRENT_Q = []  # TODO Use Queue?


def handwrite_background():
    server_dir = os.path.dirname(os.path.abspath(__file__))
    in_files_dir = os.path.join(server_dir, "infiles")
    out_files_dir = os.path.join(server_dir, "outfiles")
    status_files_dir = os.path.join(server_dir, "status")

    shutil.rmtree(in_files_dir, ignore_errors=True)
    shutil.rmtree(status_files_dir, ignore_errors=True)
    shutil.rmtree(out_files_dir, ignore_errors=True)

    os.makedirs(in_files_dir)
    os.makedirs(status_files_dir)
    os.makedirs(out_files_dir)

    prev_time = time.time()
    count = 0
    while True:
        # TODO
        # We are processing one at a time
        # in batches of 3, these batches are for
        # future threading support.
        if len(CURRENT_Q) == 0:
            mtime = lambda x: os.stat(status_files_dir + os.sep + x).st_mtime
            files = sorted(os.listdir(status_files_dir), key=mtime)
            while len(CURRENT_Q) < 4 and files:
                CURRENT_Q.append(files.pop(0))

        if CURRENT_Q:
            # TODO
            # Return something for images that didn't work.
            # Maybe create a file named in outfiles/path ERROR
            print(CURRENT_Q)
            name = CURRENT_Q.pop(0)
            image_name = name + ".jpg"
            temp_dir = tempfile.mkdtemp()
            os.makedirs(out_files_dir + os.sep + name)
            converters(
                in_files_dir + os.sep + image_name,
                temp_dir,
                out_files_dir + os.sep + name,
                os.path.dirname(os.path.abspath(__file__)) + "/default.json",
            )
            try:
                metadata  = {"firebaseStorageDownloadTokens": uuid4()}
                blob = bucket.blob(name)
                blob.metadata = metadata
                blob.upload_from_filename(in_files_dir + os.sep + image_name)
            except:
                print(f"Image Upload Failed: {image_name}")
            os.remove(in_files_dir + os.sep + image_name)
            os.remove(status_files_dir + os.sep + name)
            shutil.rmtree(temp_dir)
            count += 1

        if count == 6:
            gc.collect()
            count = 0

        if (time.time() - prev_time) / 60 > 2:
            for dir in os.listdir(out_files_dir):
                if (
                    time.time() - os.stat(out_files_dir + os.sep + dir).st_mtime
                ) / 60 > 5:
                    print(f"Deleting: {out_files_dir + os.sep + dir}")
                    shutil.rmtree(out_files_dir + os.sep + dir)
            prev_time = time.time()
