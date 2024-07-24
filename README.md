# File Passer

File Passer is a Python script for transferring files between systems on a local network. It creates a Web server and page for browsing, downloading, and uploading files.

## Requirements

This script requires Python 3.7. No external libraries are required.

## Usage

Start the server, with the working directory being the location to serve and save files: `python3 filepasser.py`

Then, open `http://[IP address]:8616/` to browse and upload files.

By default, the server will listen on port 8616 and bind itself to all interfaces. To change this, specify a port and address as command-line arguments:

* Defaults: `python3 filepasser.py`
* Listen on a different port: `python3 filepasser.py 8617`
* Listen on a different port and bind to a specific address: `python3 filepasser.py 8617 ::1`

## Security

File Passer does not perform any authentication, so anyone with access to the server can download or upload files from the directory that the script is started from. The server should only be exposed to a trusted environment.

## License

File Passer is available under the MIT License. Refer to `LICENSE.txt` for details.