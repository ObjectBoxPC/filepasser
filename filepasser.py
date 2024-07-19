#!/usr/bin/env python3

import base64
import http
import http.server
import json
import pathlib
import socket

HTTP_SERVER_PORT = 8616
INDEX_PAGE = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>File Passer</title>
    </head>
    <body>
        <form id="upload-form">
            <div>
                <label>Select file: <input type="file" required="required" id="upload-file"/></label>
            </div>
            <div>
                <label>Name: <input type="text" required="required" id="upload-name"/></label>
            </div>
            <div>
                <button type="submit" id="upload-submit">Send</button>
            </div>
        </form>
        <p id="upload-status"></p>
        <script>
        (function (document, XMLHttpRequest, JSON) {
            var uploadForm = document.getElementById('upload-form');
            var uploadFile = document.getElementById('upload-file');
            var uploadName = document.getElementById('upload-name');
            var uploadSubmit = document.getElementById('upload-submit');
            var uploadStatus = document.getElementById('upload-status');

            uploadFile.addEventListener('change', function (e) {
                uploadName.value = e.target.files[0].name;
            });

            uploadSubmit.addEventListener('click', function (e) {
                if (uploadForm.reportValidity()) {
                    var fileReader = new FileReader();
                    fileReader.addEventListener('load', function () {
                        var request = {
                            name: uploadName.value,
                            data: fileReader.result.replace(/data:.*base64,/, ''),
                        };
                        var xhr = new XMLHttpRequest();
                        xhr.open('POST', '/send');
                        xhr.addEventListener('load', function () {
                            uploadStatus.textContent = xhr.responseText;
                        });
                        xhr.send(JSON.stringify(request));
                    });
                    fileReader.readAsDataURL(uploadFile.files[0]);
                }
                e.preventDefault();
            });
        })(document, XMLHttpRequest, JSON);
        </script>
    </body>
</html>"""

class RequestHandler(http.server.BaseHTTPRequestHandler):
    server_version = "FilePasser"
    protocol_version = "HTTP/1.1"

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def do_GET(self):
        if self.path == "/":
            self._send_simple_response(http.HTTPStatus.OK, "text/html", INDEX_PAGE)
            return

        self._send_simple_response(http.HTTPStatus.NOT_FOUND, "text/plain", "Not found")

    def do_POST(self):
        if self.path == "/send":
            request_length = int(self.headers["Content-Length"])
            request = json.loads(self.rfile.read(request_length))
            try:
                with open(pathlib.PurePath(request["name"]).name, "xb") as file:
                    file.write(base64.b64decode(request["data"].encode()))
            except Exception as e:
                self._send_simple_response(http.HTTPStatus.INTERNAL_SERVER_ERROR, "text/plain", "Error: {}".format(e))
            self._send_simple_response(http.HTTPStatus.OK, "text/plain", "OK")
            return

        self._send_simple_response(http.HTTPStatus.NOT_FOUND, "text/plain", "Not found")

    def _send_simple_response(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        if type(body) is str:
            body = body.encode("utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

class Server(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6

server = Server(("::", HTTP_SERVER_PORT), RequestHandler)

try:
    print("Starting server on port {}...".format(HTTP_SERVER_PORT))
    server.serve_forever()
except KeyboardInterrupt:
    print("Exiting")