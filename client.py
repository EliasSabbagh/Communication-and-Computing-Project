#!/usr/bin/env python3

from copy import copy

import os
import socket
import threading
import time

# internal project modules
import helpers
import packets

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 0 # any
DEFAULT_ADDRESS = (DEFAULT_HOST, DEFAULT_PORT)

DEFAULT_TIMEOUT = 5 # seconds
INTERVAL_UPDATE = 7 # seconds

LIMIT_DATAGRAM = 65536

LIMIT_RETRIES = 20

SLEEP_CONNECT = 0.25 # seconds
SLEEP_DOWNLOAD = 1.2 # seconds
SLEEP_UPLOAD = 1.2 # seconds

class ClientThread(threading.Thread):

    def __init__(self, options):
        super(ClientThread, self).__init__()

        self.continue_running = True
        self.client = options['client']

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

        # shares the socket with the client object
        self.client.socket_datagram = self.socket_datagram

    def run(self):

        time_update_last = 0 # unix time, seconds since epoch
        time_update_next = 0 # unix time, seconds since epoch

        while self.continue_running:

            try:

                time_now = time.time()

                # the time to search for updates has come
                if time_now >= time_update_next:

                    time_update_last = time_now
                    time_update_next = time_now + INTERVAL_UPDATE

                    self.client.find_updates()

                packet = self.socket_datagram.recvfrom(LIMIT_DATAGRAM)

                packet_type = packets.find_type(packet)

                if packet_type == packets.TYPE_NONE:
                    continue

                if packet_type == packets.TYPE_CONNECTION_RESPONSE:
                    self.client.input_connection_response(packet)
                    continue

                if packet_type == packets.TYPE_MESSAGE_SOURCE:
                    self.client.input_message_source(packet)
                    continue

                if packet_type == packets.TYPE_FILES_LIST_RESPONSE:
                    self.client.input_files_list_response(packet)
                    continue

                if packet_type == packets.TYPE_FILE_INFO_RESPONSE:
                    self.client.input_file_info_response(packet)
                    continue

                if packet_type == packets.TYPE_BYTES_DOWNLOAD_RESPONSE:
                    self.client.input_bytes_download_response(packet)
                    continue

                if packet_type == packets.TYPE_START_UPLOAD_RESPONSE:
                    self.client.input_start_upload_response(packet)
                    continue

                if packet_type == packets.TYPE_BYTES_UPLOAD_RESPONSE:
                    self.client.input_bytes_upload_response(packet)
                    continue

            except Exception as ex:
                # ignore exceptions
                string = f'{ex}'
                if string != 'timed out':
                    raise ex
                pass

    def stop(self):
        self.continue_running = False
        self.join()

class Client:

    def __init__(self, options_client = {}):

        # socket that will be generated and managed by the thread
        self.socket_datagram = None

        # counter for generating unique numbers for identification
        self.counter = 0

        # flag that indicates if we are connected or not
        self.connected = False

        # address of the server to send messages
        self.server_address = None

        # name that user has chosen for log-in
        self.name_user = None

        # number of session upon log-in
        self.number_sesion = 0

        # array of received mesages
        self.messages = []

        # map of files from server
        self.files = {}

        # map of pending upload processes
        self.pending_processes = {}

        # maps for data transfer processes
        self.processes_download = {}
        self.processes_upload = {}

        options_client_thread = copy(options_client)
        options_client_thread['client'] = self

        self.thread = ClientThread(options_client_thread)
        self.thread.start()

    def stop(self):
        self.thread.stop()

    def next_number(self):

        self.counter = self.counter + 1
        return self.counter

    def find_updates(self):

        # only search for updates if we are connected
        if not self.connected:
            return

        # sends a request for finding which files are on the server
        self.output_files_list_request(None, self.server_address)

    # called when a "connection response" packet is received
    def input_connection_response(self, packet):

        (datagram, server_address) = packet

        connection_response = packets.unpack_connection_response(datagram)

        name_user = connection_response['name_user']
        number_session = connection_response['number_session']

        # checks if the packet has the expected name
        if name_user == self.name_user:
            self.connected = True
            self.number_session = number_session
            self.server_address = server_address

    # called when a "message source" packet is received
    def input_message_source(self, packet):

        (datagram, server_address) = packet

        message_source = packets.unpack_message_source(datagram)

        message = message_source['message']
        name_user = message_source['name_user']

        message_record = {
            'message': message,
            'name_user': name_user,
        }

        self.messages.append(message_record)

    # called when a "files list response" packet is received
    def input_files_list_response(self, packet):

        (datagram, server_address) = packet

        files_list_response = packets.unpack_files_list_response(datagram)

        number_file_list = files_list_response['number_file_list']
        number_file_set = set(number_file_list)

        # gets a set of all files that have been removed from the server
        absent_number_files = set()

        for number_file in self.files:
            if number_file not in number_file_set:
                absent_number_files.add(number_file)

        # remove all files that no longer are on the server
        for number_file in absent_number_files:
            self.files.pop(number_file, None)

        # sends a packet asking for information for every file absent
        for number_file in number_file_list:
            if number_file not in self.files:

                packet_parameters = {
                    'number_file': number_file,
                }

                self.output_file_info_request(packet_parameters, self.server_address)

    # called when a "file info response" packet is received
    def input_file_info_response(self, packet):

        (datagram, server_address) = packet

        file_info_response = packets.unpack_file_info_response(datagram)

        file_name = file_info_response['file_name']
        file_size = file_info_response['file_size']
        number_file = file_info_response['number_file']

        file_info = {
            'file_name': file_name,
            'file_size': file_size,
            'number_file': number_file,
        }

        # saves file record into client side
        self.files[number_file] = file_info

    def input_bytes_download_response(self, packet):

        (datagram, server_address) = packet

        bytes_download_response = packets.unpack_bytes_download_response(datagram)

        number_file = bytes_download_response['number_file']
        number_index = bytes_download_response['number_index']
        bytes_download = bytes_download_response['bytes_download']

        # tries to get the process download associated with this file
        process_download = self.processes_download.get(number_file)

        # ignore packet if there is no process download associated with it
        if process_download is None:
            return

        indexes_download = process_download['indexes_download']

        # ignore packet if it has already been received before
        if number_index in indexes_download:
            return

        file_buffer = process_download['file_buffer']
        file_offset = number_index * packets.BYTES_SIZE
        helpers.copy_bytes_into_buffer(
            bytes_download,
            file_buffer,
            file_offset,
        )

        indexes_download.add(number_index)

    def input_start_upload_response(self, packet):

        (datagram, server_address) = packet

        start_upload_response = packets.unpack_start_upload_response(datagram)

        number_client = start_upload_response['number_client']
        number_file = start_upload_response['number_file']
        number_process_upload = start_upload_response['number_process_upload']

        pending_process = self.pending_processes.get(number_client, None)

        # ignore packet if there is no process upload associated with it
        if pending_process is None:
            return

        indexes_limit = pending_process['indexes_limit']
        indexes_upload = pending_process['indexes_upload']

        process_upload = {
            'indexes_limit': indexes_limit,
            'indexes_upload': indexes_upload,
            'number_file': number_file,
            'number_process_upload': number_process_upload,
        }

        pending_process['process_upload'] = process_upload

        self.processes_upload[number_process_upload] = process_upload

    def input_bytes_upload_response(self, packet):

        (datagram, server_address) = packet

        bytes_upload_response = packets.unpack_bytes_upload_response(datagram)

        number_index = bytes_upload_response['number_index']
        number_process_upload = bytes_upload_response['number_process_upload']

        process_upload = self.processes_upload.get(number_process_upload, None)

        # ignore packet if there is no process upload associated with it
        if process_upload is None:
            return

        indexes_upload = process_upload['indexes_upload']
        indexes_upload.add(number_index)

    # called when a "connection request" packet is sent
    def output_connection_request(self, packet_parameters, server_address):

        datagram = packets.pack_connection_request(packet_parameters)
        self.socket_datagram.sendto(datagram, server_address)

    # called when a "message target" packet is received
    def output_message_target(self, packet_parameters, server_address):

        datagram = packets.pack_message_target(packet_parameters)
        self.socket_datagram.sendto(datagram, server_address)

    def output_files_list_request(self, packet_parameters, server_address):

        datagram = packets.pack_files_list_request(packet_parameters)
        self.socket_datagram.sendto(datagram, server_address)

    def output_file_info_request(self, packet_parameters, server_address):

        datagram = packets.pack_file_info_request(packet_parameters)
        self.socket_datagram.sendto(datagram, server_address)

    def output_bytes_download_request(self, packet_parameters, server_address):

        datagram = packets.pack_bytes_download_request(packet_parameters)
        self.socket_datagram.sendto(datagram, server_address)

    def output_start_upload_request(self, packet_parameters, server_address):

        datagram = packets.pack_start_upload_request(packet_parameters)
        self.socket_datagram.sendto(datagram, server_address)

    def output_bytes_upload_request(self, packet_parameters, server_address):

        datagram = packets.pack_bytes_upload_request(packet_parameters)
        self.socket_datagram.sendto(datagram, server_address)

    def action_connect(self, parameters):

        name_user = parameters['name_user']
        server_address = parameters['server_address']

        self.name_user = name_user
        self.number_session = 0

        packet_parameters = {
            'name_user': name_user,
        }

        retries = 0
        while retries < LIMIT_RETRIES:

            # sends a packet to server, requesting for a connection
            self.output_connection_request(packet_parameters, server_address)

            # sleep some time, waiting for reply from server
            time.sleep(SLEEP_CONNECT)

            # received a session number from the server, success
            if self.number_session != 0:
                break

            retries = retries + 1

        return self.connected

    def action_write_message(self, parameters):

        message = parameters['message']
        name_user = parameters['name_user']

        packet_parameters = {
            'message': message,
            'name_user': name_user,
            'number_session': self.number_session,
        }

        self.output_message_target(packet_parameters, self.server_address)

    def action_trash_messages(self, parameters):

        # excludes all received messages
        self.messages = []

    def action_download_file(self, parameters):

        file_size = parameters['file_size']
        file_name = parameters['file_name']
        number_file = parameters['number_file']

        # the set for all indexes of 256 bytes pieces received
        indexes_download = set()

        # the limit for how many indexes to expect to be uploaded
        indexes_limit = (file_size + packets.BYTES_LIMIT) // packets.BYTES_SIZE

        # creates a buffer for storing all bytes to be received from file
        rounded_file_size = indexes_limit * packets.BYTES_SIZE
        file_buffer = bytearray(rounded_file_size)

        process_download = {
            'file_buffer': file_buffer,
            'file_name': file_name,
            'file_size': file_size,
            'indexes_limit': indexes_limit,
            'indexes_download': indexes_download,
        }

        self.processes_download[number_file] = process_download

        download_done = False

        # request file bytes until all pieces have been received from server
        retries = 0
        while retries < LIMIT_RETRIES:

            # sends as much packets as possible, requesting pieces of the file
            for number_index in range(indexes_limit):

                # only request the piece not yet received
                if number_index not in indexes_download:

                    packet_parameters = {
                        'number_file': number_file,
                        'number_index': number_index,
                    }

                    self.output_bytes_download_request(
                        packet_parameters,
                        self.server_address,
                    )

            # sleeps some time in order to wait for server reply
            time.sleep(SLEEP_DOWNLOAD)

            indexes_count = len(indexes_download)

            # break loop if all pieces have been received
            if indexes_count == indexes_limit:
                download_done = True
                break

            retries = retries + 1

        # unlinks the process from the client object
        self.processes_download.pop(number_file, None)

        # failed to download file
        if not download_done:
            return None

        # return the completed process download
        return process_download

    def action_upload_file(self, parameters):

        file_bytes = parameters['file_bytes']
        file_name = parameters['file_name']

        file_size = len(file_bytes)

        # the set for all indexes of 256 bytes pieces sent
        indexes_upload = set()

        # the limit for how many indexes to expect to be uploaded
        indexes_limit = (file_size + packets.BYTES_LIMIT) // packets.BYTES_SIZE

        # reserves a number for identification of this upload process
        number_client = self.next_number()

        packet_parameters = {
            'file_name': file_name,
            'file_size': file_size,
            'number_client': number_client,
            'number_session': self.number_session,
        }

        pending_process = {
            'number_client': number_client,
            'process_upload': None,
            'file_bytes': file_bytes,
            'file_name': file_name,
            'file_size': file_size,
            'indexes_limit': indexes_limit,
            'indexes_upload': indexes_upload,
        }

        self.pending_processes[number_client] = pending_process

        process_upload = None

        retries = 0
        while retries < LIMIT_RETRIES:

            self.output_start_upload_request(packet_parameters, self.server_address)

            # sleeps some time in order to wait for server reply
            time.sleep(SLEEP_UPLOAD)

            process_upload = pending_process['process_upload']

            # succeded in requesting an upload process from server, break loop
            if process_upload is not None:
                break

            retries = retries + 1

        # failed to request an upload process from server
        if process_upload is None:
            return False

        number_file = process_upload['number_file']
        number_process_upload = process_upload['number_process_upload']
        upload_complete = False

        retries = 0
        while retries < LIMIT_RETRIES:

            # sends as much packets as possible, requesting pieces of the file
            for number_index in range(indexes_limit):

                # only request the piece not yet received
                if number_index not in indexes_upload:

                    file_offset_a = number_index * packets.BYTES_SIZE
                    file_offset_b = file_offset_a + packets.BYTES_SIZE

                    bytes_upload = file_bytes[file_offset_a:file_offset_b]

                    packet_parameters = {
                        'bytes_upload': bytes_upload,
                        'number_index': number_index,
                        'number_process_upload': number_process_upload,
                    }

                    self.output_bytes_upload_request(
                        packet_parameters,
                        self.server_address,
                    )

            # sleeps some time in order to wait for server reply
            time.sleep(SLEEP_UPLOAD)

            indexes_count = len(indexes_upload)

            # break loop if all pieces have been received
            if indexes_count == indexes_limit:
                upload_complete = True
                break

            retries = retries + 1

        return upload_complete


def main():

    client = Client()

    def wait_input():

        print("PRESS ENTER TO CONTINUE...")
        input()

    def print_menu():

        print()

        if client.connected:
            print(f'CONNECTION STATUS: CONNECTED AS "{ client.name_user }"')
        else:
            print("CONNECTION STATUS: NOT CONNECTED")

        print(f'RECEIVED MESSAGES: { len(client.messages) }')
        print(f'SERVER FILES: { len(client.files) }')

        MENU_CHOICE_0 = "EXIT PROGRAM"
        MENU_CHOICE_1 = "CONNECT TO SERVER"
        MENU_CHOICE_2 = "WRITE MESSAGE FOR ONE USER"
        MENU_CHOICE_3 = "WRITE MESSAGE FOR ALL USERS"
        MENU_CHOICE_4 = "READ RECEIVED MESSAGE"
        MENU_CHOICE_5 = "TRASH ALL RECEIVED MESSAGES"
        MENU_CHOICE_6 = "LIST FILES FROM SERVER"
        MENU_CHOICE_7 = "DOWNLOAD FILE FROM SERVER"
        MENU_CHOICE_8 = "UPLOAD FILE TO SERVER"

        MENU_CHOICES = [
            MENU_CHOICE_0,
            MENU_CHOICE_1,
            MENU_CHOICE_2,
            MENU_CHOICE_3,
            MENU_CHOICE_4,
            MENU_CHOICE_5,
            MENU_CHOICE_6,
            MENU_CHOICE_7,
            MENU_CHOICE_8,
        ]

        print()

        for index, phrase in enumerate(MENU_CHOICES):
            print(f'{ index }. { phrase }')

        print()

    def choice_1():

        server_host = input("SERVER HOST: ")
        server_port = int(input("SERVER PORT: "))
        name_user = input("USER NAME: ")

        server_address = (server_host, server_port)

        parameters = {
            'name_user': name_user,
            'server_address': server_address,
        }

        print("TRYING TO CONNECT...")
        action_result = client.action_connect(parameters)

        if action_result is True: # user has logged-in
            print("CONNECTION SUCCESS!")
        else: # user has not logged-in
            print("CONNECTION FAILURE!")

        wait_input()

    def choice_2():

        name_user = input("TARGET USER NAME: ")
        message = input("MESSAGE: ")

        parameters = {
            'name_user': name_user,
            'message': message,
        }

        client.action_write_message(parameters)

        print("MESSAGE SENT!")

        wait_input()

    def choice_3():
        wait_input()

    def choice_4():

        message_index = int(input("MESSAGE INDEX: "))
        message_record = client.messages[message_index]

        name_user_source = message_record['name_user']
        message = message_record['message']

        print(f'SOURCE USER NAME: { name_user_source }')
        print(f'MESSAGE: "{ message }"')

        wait_input()

    def choice_5():

        client.action_trash_messages(None)
        print("MESSAGES EXCLUDED!")

        wait_input()

    def choice_6():

        print("FILES FROM SERVER:")

        for index, file_info in enumerate(client.files.values()):

            file_size = file_info['file_size']
            file_name = file_info['file_name']

            print(f'FILE #{ index }: "{ file_name }", { file_size } BYTES')

        wait_input()

    def choice_7():

        print("FILE DOWNLOAD")

        file_index = int(input("FILE INDEX: #"))
        file_path = input("FILE PATH: ")

        file_list = [x for x in client.files.values()]

        if file_index >= len(file_list):
            print(f'NO FILE WITH INDEX #{ file_index } FOUND!')
            return

        file_info = file_list[file_index]

        print("DOWNLOADING FILE...")

        process_download = client.action_download_file(file_info)

        if process_download is None:
            print("FAILED TO DOWNLOAD FILE!")
            return

        print("FILE DOWNLOADED!")

        file_buffer = process_download['file_buffer']
        file_size = process_download['file_size']

        output_file = open(file_path, 'wb')
        output_file.write(file_buffer[:file_size])
        output_file.close()

    def choice_8():

        print("FILE UPLOAD")

        file_path = input("FILE PATH: ")

        file_bytes = open(file_path, 'rb').read()
        file_name = os.path.basename(file_path)

        parameters = {
            'file_bytes': file_bytes,
            'file_name': file_name,
        }

        print("UPLOADING FILE...")

        upload_complete = client.action_upload_file(parameters)

        if not upload_complete:
            print("FAILED TO UPLOAD FILE!")
            return

        print("FILE UPLOADED!")

    while True:

        try:

            print_menu()

            INPUT_PROMPT = "YOUR CHOICE: "
            choice = int(input(INPUT_PROMPT))

            if choice == 0:
                client.stop()
                break

            if choice == 1:
                choice_1()
                continue

            if choice == 2:
                choice_2()
                continue

            if choice == 3:
                choice_3()
                continue

            if choice == 4:
                choice_4()
                continue

            if choice == 5:
                choice_5()
                continue

            if choice == 6:
                choice_6()
                continue

            if choice == 7:
                choice_7()
                continue

            if choice == 8:
                choice_8()
                continue

        except Exception:
            # ignore exceptions
            pass    

if __name__ == "__main__":
    main()
