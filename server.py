#!/usr/bin/env python3

from copy import copy

import threading
import socket
import time

# internal project modules
import helpers
import packets

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 55000
DEFAULT_ADDRESS = (DEFAULT_HOST, DEFAULT_PORT)

DEFAULT_TIMEOUT = 5 # seconds

LIMIT_DATAGRAM = 65536

# limits file size to 8MiB
LIMIT_FILE_SIZE = 8 * 1024 * 1024

class ServerThread(threading.Thread):

    def __init__(self, options):
        super(ServerThread, self).__init__()

        self.continue_running = True
        self.server = options['server']

        self.socket_datagram = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        socket_host = options.get('host', DEFAULT_HOST)
        socket_port = options.get('port', DEFAULT_PORT)
        socket_address = (socket_host, socket_port)
        self.socket_datagram.bind(socket_address)

        socket_timeout = options.get('timeout', DEFAULT_TIMEOUT)
        self.socket_datagram.settimeout(socket_timeout)

        # shares the socket with the server object
        self.server.socket_datagram = self.socket_datagram

    def run(self):

        while self.continue_running:

            try:

                packet = self.socket_datagram.recvfrom(LIMIT_DATAGRAM)

                packet_type = packets.find_type(packet)

                if packet_type == packets.TYPE_NONE:
                    continue

                if packet_type == packets.TYPE_CONNECTION_REQUEST:
                    self.server.input_connection_request(packet)
                    continue

                if packet_type == packets.TYPE_MESSAGE_TARGET:
                    self.server.input_message_target(packet)
                    continue

                if packet_type == packets.TYPE_FILES_LIST_REQUEST:
                    self.server.input_files_list_request(packet)
                    continue

                if packet_type == packets.TYPE_FILE_INFO_REQUEST:
                    self.server.input_file_info_request(packet)
                    continue

                if packet_type == packets.TYPE_BYTES_DOWNLOAD_REQUEST:
                    self.server.input_bytes_download_request(packet)

                if packet_type == packets.TYPE_START_UPLOAD_REQUEST:
                    self.server.input_start_upload_request(packet)
                    continue

                if packet_type == packets.TYPE_BYTES_UPLOAD_REQUEST:
                    self.server.input_bytes_upload_request(packet)
                    continue

            except Exception as ex:
                # ignore exceptions
                string = f'{ex}'
                if string != "timed out":
                     raise ex
                pass

    def stop(self):
        self.continue_running = False
        self.join()

class Server:

    def __init__(self, options_server = {}):

        # socket that will be generated and managed by the thread
        self.socket_datagram = None

        # counter for generating unique numbers for identification
        self.counter = 0

        # map of user names into users
        self.users = {}

        # map of user numbers into users
        self.numbered_users = {}

        # map of session numbers into sessions
        self.sessions = {}

        # map for upload transfer processes
        self.processes_upload = {}

        # map of files stored in server
        self.files = {}

        options_server_thread = copy(options_server)
        options_server_thread['server'] = self

        self.thread = ServerThread(options_server_thread)
        self.thread.start()

    def wait(self):
        self.thread.join()

    def next_number(self):

        self.counter = self.counter + 1
        return self.counter

    # called when a "connection request" packet is received
    def input_connection_request(self, packet):

        (datagram, client_address) = packet

        connection_request = packets.unpack_connection_request(datagram)

        name_user = connection_request['name_user']
        user = self.users.get(name_user, None)

        # no user with that name is logged in, create session and user
        if user is None:

            # reserves a number for identification of this session
            number_session = self.next_number()

            # creates session and save it
            processes_upload = {}
            processes_download = {}

            session = {
                'client_address': None,
                'number_session': number_session,
                'processes_download': processes_download,
                'processes_upload': processes_upload,
                'user': None,
            }

            self.sessions[number_session] = session

            # reserves a number for identification of this session
            number_user = self.next_number()

            # creates user and saves it

            user = {
                'client_address': client_address,
                'name_user': name_user,
                'number_session': number_session,
                'number_user': number_user,
                'session': session,
            }

            session['user'] = user

            self.users[name_user] = user
            self.numbered_users[number_user] = user

        session = user['session']
        number_session = session['number_session']

        session['client_address'] = client_address

        packet_parameters = {
            'name_user': name_user,
            'number_session': number_session,
        }

        # outputs packet to remote user informing of the connection established
        self.output_connection_response(packet_parameters, client_address)

    # called when a "message target" packet is received
    def input_message_target(self, packet):

        (datagram, client_address) = packet

        message_target = packets.unpack_message_target(datagram)

        message = message_target['message']
        name_user_target = message_target['name_user']
        number_session = message_target['number_session']

        # searches for the session of the client trying to write a message
        session = self.sessions.get(number_session, None)

        # ignores packet if there is no session associated with it
        if session is None:
            return

        # searches for the user that the client is trying to write a message to
        user_target = self.users.get(name_user_target, None)

        # ignores packet if cannot find the target user
        if user_target is None:
            return

        target_address = user_target['client_address']

        user_source = session['user']
        name_user_source = user_source['name_user']

        # sends packet with message to destination user

        packet_parameters = {
            'name_user': name_user_source,
            'message': message,
        }

        # outputs packet to remote user informing of the connection established
        self.output_message_source(packet_parameters, target_address)

    # called when a "files list request" packet is received
    def input_files_list_request(self, packet):

        (datagram, client_address) = packet

        files_list_request = packets.unpack_files_list_request(datagram)

        number_file_list = [key for key in self.files.keys()]

        packet_parameters = {
            'number_file_list': number_file_list,
        }

        self.output_files_list_response(packet_parameters, client_address)

    # called when a "file info request" packet is received
    def input_file_info_request(self, packet):

        (datagram, client_address) = packet

        file_info_request = packets.unpack_file_info_request(datagram)

        number_file = file_info_request['number_file']
        server_file = self.files.get(number_file, None)

        # ignores packet if there is no file associated with it
        if server_file is None:
            return

        file_name = server_file['file_name']
        file_size = server_file['file_size']

        packet_parameters = {
            'file_name': file_name,
            'file_size': file_size,
            'number_file': number_file,
        }

        self.output_file_info_response(packet_parameters, client_address)

    # called when a "bytes download request" packet is received
    def input_bytes_download_request(self, packet):

        (datagram, client_address) = packet

        bytes_download_request = packets.unpack_bytes_download_request(datagram)

        number_file = bytes_download_request['number_file']
        number_index = bytes_download_request['number_index']

        server_file = self.files.get(number_file, None)

        # ignores packet if there is no file associated with it
        if server_file is None:
            return

        indexes_limit = server_file['indexes_limit']

        # ignores packet if it asks for an index that does not exist
        if number_index >= indexes_limit:
            return

        file_buffer = server_file['file_buffer']

        file_offset_a = number_index * packets.BYTES_SIZE
        file_offset_b = file_offset_a + packets.BYTES_SIZE

        bytes_download = file_buffer[file_offset_a:file_offset_b]

        packet_parameters = {
            'number_file': number_file,
            'number_index': number_index,
            'bytes_download': bytes_download,
        }

        self.output_bytes_download_response(packet_parameters, client_address)


    # called when a "start upload request" packet is received
    def input_start_upload_request(self, packet):

        (datagram, client_address) = packet

        start_upload_request = packets.unpack_start_upload_request(datagram)

        number_session = start_upload_request['number_session']
        number_client = start_upload_request['number_client']
        file_size = start_upload_request['file_size']
        file_name = start_upload_request['file_name']

        # ignore requests for empty files
        if file_size == 0:
            return

        # ignore requests for excessively large files
        if file_size > LIMIT_FILE_SIZE:
            return

        # searches for the session of the client trying to upload a file
        session = self.sessions.get(number_session, None)

        # ignores packet if there is no session associated with it
        if session is None:
            return

        client_processes_upload = session['processes_upload']
        process_upload = client_processes_upload.get(number_client, None)

        # creates a new upload process if there isn't one already
        if process_upload is None:

            # reserves a number for identification of this upload process
            number_process_upload = self.next_number()

            # reserves a number for identification of this file
            number_file = self.next_number()

            # the set for all indexes of 256 bytes pieces received
            indexes_upload = set()

            # the limit for how many indexes to expect to be uploaded
            indexes_limit = (file_size + packets.BYTES_LIMIT) // packets.BYTES_SIZE

            # creates a buffer for storing all bytes to be received from file
            rounded_file_size = indexes_limit * packets.BYTES_SIZE
            file_buffer = bytearray(rounded_file_size)

            process_upload = {
                'file_buffer': file_buffer,
                'file_name': file_name,
                'file_size': file_size,
                'indexes_limit': indexes_limit,
                'indexes_upload': indexes_upload,
                'number_client': number_client,
                'number_file': number_file,
                'number_process_upload': number_process_upload,
                'session': session,
            }

            client_processes_upload[number_client] = process_upload
            self.processes_upload[number_process_upload] = process_upload

        packet_parameters = process_upload

        # outputs packet to remote user informing of this upload process
        self.output_start_upload_response(packet_parameters, client_address)

    # called when a "bytes upload request" packet is received
    def input_bytes_upload_request(self, packet):

        (datagram, client_address) = packet

        bytes_upload_request = packets.unpack_bytes_upload_request(datagram)

        number_process_upload = bytes_upload_request['number_process_upload']
        number_index = bytes_upload_request['number_index']
        bytes_upload = bytes_upload_request['bytes_upload']

        process_upload = self.processes_upload.get(number_process_upload, None)

        # ignores packet if there is no upload process associated with it
        if process_upload is None:
            return

        indexes_upload = process_upload['indexes_upload']

        # ignores packet if this bytes piece has already been received
        if number_index in indexes_upload:

            packet_parameters = {
                'number_index': number_index,
                'number_process_upload': number_process_upload,
            }

            # sends again packet for acknowledging the bytes received
            self.output_bytes_upload_response(packet_parameters, client_address)
            return

        indexes_limit = process_upload['indexes_limit']

        # ignores packet if the index is beyond the limit
        if number_index >= indexes_limit:
            return

        file_buffer = process_upload['file_buffer']
        file_offset = number_index * packets.BYTES_SIZE

        # copies received data into the file buffer
        helpers.copy_bytes_into_buffer(
            bytes_upload,
            file_buffer,
            file_offset,
        )

        indexes_upload.add(number_index)

        # all pieces have been uploaded, make file available for download
        if len(indexes_upload) == indexes_limit:
            self.register_uploaded_file(process_upload)

        packet_parameters = {
            'number_index': number_index,
            'number_process_upload': number_process_upload,
        }

        # sends packet for acknowledging the bytes received
        self.output_bytes_upload_response(packet_parameters, client_address)

    # called when a "start upload request" packet is received
    def input_start_download_request(self, packet, indexes_limit=None, client_address=None):

        (datagram, address) = packet

        start_download_request = packets.unpack_start_download_request(datagram)

        number_session = start_download_request['number_session']
        number_client = start_download_request['number_client']
        number_file = start_download_request['number_file']

        # searches for the session of the client trying to download a file
        session = self.sessions.get(number_session, None)

        # ignores packet if there is no session associated with it
        if session is None:
            return

        # searches for the file that the client is trying to download
        server_file = self.files.get(number_file, None)

        # ignores packet if there is no server file associated with it
        if server_file is None:
            return

        client_processes_download = session['processes_download']
        process_download = client_processes_download.get(number_client, None)

        # creates a new download process if there isn't one already
        if process_download is None:

            # reserves a number for identification of this download process
            number_process_download = self.next_number()

            process_download = {
                'server_file': server_file,
                'indexes_limit': indexes_limit,
                'number_client': number_client,
                'number_process_download': number_process_download,
                'session': session,
            }

            client_processes_download[number_client] = process_download
            self.processes_download[number_process_download] = process_download

        packet_parameters = process_download

        # outputs packet to remote user informing of this download process
        self.output_start_download_response(packet_parameters, client_address)

    # called when a "connection response" packet is sent
    def output_connection_response(self, packet_parameters, client_address):

        datagram = packets.pack_connection_response(packet_parameters)
        self.socket_datagram.sendto(datagram, client_address)

    # called when a "message source" packet is sent
    def output_message_source(self, packet_parameters, client_address):

        datagram = packets.pack_message_source(packet_parameters)
        self.socket_datagram.sendto(datagram, client_address)

    # called when a "files list response" packet is sent
    def output_files_list_response(self, packet_parameters, client_address):

        datagram = packets.pack_files_list_response(packet_parameters)
        self.socket_datagram.sendto(datagram, client_address)

    # called when a "file info response" packet is sent
    def output_file_info_response(self, packet_parameters, client_address):

        datagram = packets.pack_file_info_response(packet_parameters)
        self.socket_datagram.sendto(datagram, client_address)

    # called when a "bytes download response" packet is sent
    def output_bytes_download_response(self, packet_parameters, client_address):

        datagram = packets.pack_bytes_download_response(packet_parameters)
        self.socket_datagram.sendto(datagram, client_address)

    # called when a "start upload response" packet is sent
    def output_start_upload_response(self, packet_parameters, client_address):

        datagram = packets.pack_start_upload_response(packet_parameters)
        self.socket_datagram.sendto(datagram, client_address)

    # called when a "bytes upload response" packet is sent
    def output_bytes_upload_response(self, packet_parameters, client_address):

        datagram = packets.pack_bytes_upload_response(packet_parameters)
        self.socket_datagram.sendto(datagram, client_address)

    def output_start_download_response(self, parameters):
        pass

    def register_file(self, parameters):

        file_buffer = parameters['file_buffer']
        file_name = parameters['file_name']
        file_size = parameters['file_size']
        indexes_limit = parameters['indexes_limit']

        # creates an unique number for identifying this file on the server
        number_file = self.next_number()

        server_file = {
            'file_buffer': file_buffer,
            'file_name': file_name,
            'file_size': file_size,
            'indexes_limit': indexes_limit,
            'number_file': number_file,
        }

        self.files[number_file] = server_file

    def register_uploaded_file(self, process_upload):

        self.register_file(process_upload)

        # remove process upload from the server data
        number_process_upload = process_upload['number_process_upload']
        self.processes_upload.pop(number_process_upload, None)

        number_client = process_upload['number_client']
        session = process_upload['session']

        # remove process upload from the client data
        client_processes_upload = session['processes_upload']
        client_processes_upload.pop(number_client, None)

def main():

    server = Server()

    # waits for the server to be shutdown
    server.wait()

if __name__ == "__main__":
    main()
