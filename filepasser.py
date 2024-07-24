#!/usr/bin/env python3

import base64
import http
import http.server
import json
import pathlib
import socket
import sys

DEFAULT_PORT = 8616
DEFAULT_BIND_ADDR = "::"
INDEX_PAGE = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>File Passer</title>
    </head>
    <body>
        <h1>File Passer</h1>
        <h2>Directory Listing for <span id="directory-path">.</span></h2>
        <p id="directory-list-status"></p>
        <ul id="directory-list"></ul>
        <h2>Upload</h2>
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
        (function (document, window, XMLHttpRequest, JSON) {
            var directoryPath = document.getElementById('directory-path');
            var directoryListStatus = document.getElementById('directory-list-status');
            var directoryList = document.getElementById('directory-list');
            var uploadForm = document.getElementById('upload-form');
            var uploadFile = document.getElementById('upload-file');
            var uploadName = document.getElementById('upload-name');
            var uploadSubmit = document.getElementById('upload-submit');
            var uploadStatus = document.getElementById('upload-status');

            function loadDirectoryListing() {
                var directory = location.hash.slice(2);
                directoryPath.textContent = '/' + directory;
                var request = { dir: directory };
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '/dirlist');
                xhr.addEventListener('load', function () {
                    directoryList.textContent = '';
                    directoryListStatus.textContent = '';
                    var response = JSON.parse(xhr.responseText);
                    if (response.error) {
                        directoryListStatus.textContent = 'Error: ' + response.error;
                        return;
                    }
                    response.forEach(function (entry) {
                        var listItem = document.createElement('li');
                        listItemLink = document.createElement('a');
                        listItemLink.href = entry.path;
                        listItemLink.textContent = entry.name;
                        if (entry.type === 'dir') {
                            listItemLink.textContent += '/';
                            listItemLink.addEventListener('click', function (e) {
                                window.location.hash = '#/' + entry.path;
                                e.preventDefault();
                            });
                        }
                        listItem.appendChild(listItemLink);
                        directoryList.appendChild(listItem);
                    });
                });
                xhr.send(JSON.stringify(request));
            }

            window.addEventListener('DOMContentLoaded', loadDirectoryListing);
            window.addEventListener('hashchange', loadDirectoryListing);

            uploadFile.addEventListener('change', function (e) {
                uploadName.value = e.target.files[0].name;
            });

            uploadSubmit.addEventListener('click', function (e) {
                if (uploadForm.reportValidity()) {
                    var fileReader = new FileReader();
                    fileReader.addEventListener('load', function () {
                        var request = {
                            dir: window.location.hash.slice(2),
                            name: uploadName.value,
                            data: fileReader.result.replace(/data:.*base64,/, ''),
                        };
                        var xhr = new XMLHttpRequest();
                        xhr.open('POST', '/send');
                        xhr.addEventListener('load', function () {
                            var response = JSON.parse(xhr.responseText);
                            if (response.result) {
                                uploadStatus.textContent = response.result;
                            } else {
                                uploadStatus.textContent = 'Error: ' + response.error;
                            }
                        });
                        xhr.send(JSON.stringify(request));
                    });
                    fileReader.readAsDataURL(uploadFile.files[0]);
                }
                e.preventDefault();
            });
        })(document, window, XMLHttpRequest, JSON);
        </script>
    </body>
</html>""".encode()

def is_valid_relative_dir(path):
    return not (path.is_absolute() or '..' in path.parts)

def get_dirlist_data(path):
    return {
        "type": "dir" if path.is_dir() else "file",
        "name": path.name,
        "path": str(path),
    }

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    server_version = "FilePasser"
    protocol_version = "HTTP/1.1"

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def do_GET(self):
        if self.path == "/":
            self._send_simple_response(http.HTTPStatus.OK, "text/html", INDEX_PAGE)
            return

        super().do_GET()

    def do_POST(self):
        request_length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(request_length))

        try:
            if self.path == "/send":
                dir_path = pathlib.PurePath(request["dir"])
                if not is_valid_relative_dir(dir_path):
                    raise Exception("Invalid directory")
                base_filename = pathlib.PurePath(request["name"]).name
                file_path = pathlib.Path(dir_path, base_filename)
                with file_path.open("xb") as file:
                    file.write(base64.b64decode(request["data"].encode()))
                self._send_json_response(http.HTTPStatus.OK, { "result": "OK" })
                return

            if self.path == '/dirlist':
                dir_path = pathlib.Path(request["dir"])
                if not is_valid_relative_dir(dir_path):
                    raise Exception("Invalid directory")
                if not dir_path.is_dir():
                    raise Exception("Not a directory")
                response = [get_dirlist_data(x) for x in dir_path.iterdir()]
                self._send_json_response(http.HTTPStatus.OK, response)

                return

        except Exception as e:
            self._send_json_response(http.HTTPStatus.INTERNAL_SERVER_ERROR, { "error": str(e) })

        self._send_json_response(http.HTTPStatus.NOT_FOUND, { "error": "Not found" })

    def _send_simple_response(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_json_response(self, code, data):
        self._send_simple_response(code, "application/json", json.dumps(data).encode())

class Server(http.server.ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass):
        self.address_family = socket.getaddrinfo(*server_address)[0][0]
        super().__init__(server_address, RequestHandlerClass)

args = sys.argv + [None] * (3 - len(sys.argv))
port = int(args[1]) if args[1] else DEFAULT_PORT
bind_addr = args[2] or DEFAULT_BIND_ADDR
server = Server((bind_addr, port), RequestHandler)

try:
    print("Starting server on port {}...".format(port))
    server.serve_forever()
except KeyboardInterrupt:
    print("Exiting")