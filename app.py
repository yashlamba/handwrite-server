import os
import uuid
import shutil
import tempfile

import cv2
import numpy as np
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

from setup_logging import setup_logger


def create_app():
    app = Flask(__name__)
    setup_logger(app.logger)
    logger = app.logger
    CORS(app)

    server_dir = os.path.dirname(os.path.abspath(__file__))
    dirs = {
        dir_name: os.path.join(server_dir, dir_name)
        for dir_name in ["infiles", "outfiles", "status", "error"]
    }

    @app.route("/handwrite/input", methods=["POST"])
    def receive_image():
        responses = {
            0: "Received",
            1: "Not Found",
            2: "Can't Process Image",
            3: "Internal Server Error",
        }
        response = 3
        path = None

        if "image" in request.files and request.files["image"]:
            try:
                image = request.files["image"].read()
                imgarr = np.frombuffer(image, np.uint8)
                img = cv2.imdecode(imgarr, cv2.IMREAD_COLOR)
            except:
                response = 2

            try:
                research_option = "_1000" if request.form.get("research") else ""
                file_name = str(uuid.uuid4()) + research_option
                cv2.imwrite(dirs["infiles"] + os.sep + file_name + ".jpg", img)
                open(dirs["status"] + os.sep + file_name, "w").close()
                path = file_name
                logger.info(f"Request Created for Background Service {path}")
            except:
                pass
            if (
                path
                and os.path.exists(dirs["infiles"] + os.sep + path + ".jpg")
                and os.path.exists(dirs["status"] + os.sep + path)
            ):
                response = 0
        else:
            response = 1

        return jsonify(response_code=response, message=responses[response], path=path)

    @app.route("/handwrite/status/<path>")
    def process_status(path):
        """
        Returns:
            0 if Done
            1 if Processing
            2 if Unable to process
            3 if Not found in requests
        """
        fontfile, statusfile, errorfile = (
            os.path.exists(dirs["outfiles"] + os.sep + path + os.sep + "MyFont.ttf"),
            os.path.exists(dirs["status"] + os.sep + path),
            os.path.exists(dirs["error"] + os.sep + path),
        )

        status = 3
        if errorfile:
            status = 2
            os.remove(dirs["error"] + os.sep + path)
            shutil.rmtree(dirs["outfiles"] + os.sep + path)
            logger.info(f"Cleaned Processing Data for Errored Request {path}")
        elif fontfile:
            status = 0
        elif statusfile:
            status = 1

        return jsonify(status=status)

    @app.route("/handwrite/fetch/<path>", methods=["POST"])
    def fetch_font(path):
        """
        Returns:
            fontfile if found
            else json with error
        """
        fontpath = dirs["outfiles"] + os.sep + path + os.sep + "MyFont.ttf"
        if os.path.exists(fontpath):
            fontfile = send_file(fontpath, as_attachment=True)
            shutil.rmtree(dirs["outfiles"] + os.sep + path)
            logger.info(f"Sent and cleaned fontfile path {path}")
            return fontfile
        return jsonify(error="File Not Found!")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()
