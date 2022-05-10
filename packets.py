import struct

# internal project modules
import helpers

# binary structures
STRUCT_PACKET_TYPE = "!L"

STRUCT_CONNECTION_REQUEST = "!LL256s"
STRUCT_CONNECTION_RESPONSE = "!LLL256s"

STRUCT_MESSAGE_TARGET = "!LLLL128s256s"
STRUCT_MESSAGE_SOURCE = "!LLL128s256s"

STRUCT_FILES_LIST_REQUEST = "!L"
STRUCT_FILES_LIST_RESPONSE = "!LL64L"

STRUCT_FILE_INFO_REQUEST = "!LL"
STRUCT_FILE_INFO_RESPONSE = "!LLLL128s"

STRUCT_BYTES_DOWNLOAD_REQUEST = "!LLL"
STRUCT_BYTES_DOWNLOAD_RESPONSE = "!LLL256s"

STRUCT_START_UPLOAD_REQUEST = "!LLLLL128s"
STRUCT_START_UPLOAD_RESPONSE = "!LLLL"

STRUCT_BYTES_UPLOAD_REQUEST = "!LLL256s"
STRUCT_BYTES_UPLOAD_RESPONSE = "!LLL"

# packet types
TYPE_NONE = 0

TYPE_CONNECTION_REQUEST = 1
TYPE_CONNECTION_RESPONSE = 2

TYPE_MESSAGE_TARGET = 3
TYPE_MESSAGE_SOURCE = 4

TYPE_FILES_LIST_REQUEST = 5
TYPE_FILES_LIST_RESPONSE = 6

TYPE_FILE_INFO_REQUEST = 7
TYPE_FILE_INFO_RESPONSE = 8

TYPE_BYTES_DOWNLOAD_REQUEST = 9
TYPE_BYTES_DOWNLOAD_RESPONSE = 10

TYPE_START_UPLOAD_REQUEST = 11
TYPE_START_UPLOAD_RESPONSE = 12

TYPE_BYTES_UPLOAD_REQUEST = 13
TYPE_BYTES_UPLOAD_RESPONSE = 14

# useful constants
BYTES_SIZE = 256
BYTES_LIMIT = BYTES_SIZE - 1
SIZE_MINIMUM = struct.calcsize(STRUCT_PACKET_TYPE)
SIZE_BYTES_SECTION = 256
SIZE_NAME_SECTION = 128
SIZE_FILES_SECTION = 64


def find_type(packet):
    (data, address) = packet

    if len(data) < SIZE_MINIMUM:
        return TYPE_NONE

    common_header = data[0:SIZE_MINIMUM]

    structure = struct.unpack(STRUCT_PACKET_TYPE, common_header)

    return structure[0]


# packers
def pack_connection_request(parameters):
    name_user = parameters['name_user']

    bytes_name_user = bytes(name_user, encoding='UTF-8')
    length_name_user = len(bytes_name_user)

    bytes_name_user = helpers.pad_bytes_to_size(
        bytes_name_user,
        SIZE_BYTES_SECTION,
    )

    datagram = struct.pack(
        STRUCT_CONNECTION_REQUEST,
        TYPE_CONNECTION_REQUEST,
        length_name_user,
        bytes_name_user,
    )

    return datagram


def pack_connection_response(parameters):
    name_user = parameters['name_user']
    number_session = parameters['number_session']

    bytes_name_user = bytes(name_user, encoding='UTF-8')
    length_name_user = len(bytes_name_user)

    bytes_name_user = helpers.pad_bytes_to_size(
        bytes_name_user,
        SIZE_BYTES_SECTION,
    )

    datagram = struct.pack(
        STRUCT_CONNECTION_RESPONSE,
        TYPE_CONNECTION_RESPONSE,
        number_session,
        length_name_user,
        bytes_name_user,
    )

    return datagram


def pack_message_target(parameters):
    message = parameters['message']
    name_user = parameters['name_user']
    number_session = parameters['number_session']

    bytes_name_user = bytes(name_user, encoding='UTF-8')
    length_name_user = len(bytes_name_user)

    bytes_name_user = helpers.pad_bytes_to_size(
        bytes_name_user,
        SIZE_NAME_SECTION,
    )

    bytes_message = bytes(message, encoding='UTF-8')
    length_message = len(bytes_message)

    bytes_message = helpers.pad_bytes_to_size(
        bytes_message,
        SIZE_BYTES_SECTION,
    )

    datagram = struct.pack(
        STRUCT_MESSAGE_TARGET,
        TYPE_MESSAGE_TARGET,
        number_session,
        length_name_user,
        length_message,
        bytes_name_user,
        bytes_message,
    )

    return datagram


def pack_message_source(parameters):
    message = parameters['message']
    name_user = parameters['name_user']

    bytes_name_user = bytes(name_user, encoding='UTF-8')
    length_name_user = len(bytes_name_user)

    bytes_name_user = helpers.pad_bytes_to_size(
        bytes_name_user,
        SIZE_NAME_SECTION,
    )

    bytes_message = bytes(message, encoding='UTF-8')
    length_message = len(bytes_message)

    bytes_message = helpers.pad_bytes_to_size(
        bytes_message,
        SIZE_BYTES_SECTION,
    )

    datagram = struct.pack(
        STRUCT_MESSAGE_SOURCE,
        TYPE_MESSAGE_SOURCE,
        length_name_user,
        length_message,
        bytes_name_user,
        bytes_message,
    )

    return datagram


def pack_files_list_request(parameters):
    datagram = struct.pack(
        STRUCT_FILES_LIST_REQUEST,
        TYPE_FILES_LIST_REQUEST,
    )

    return datagram


def pack_files_list_response(parameters):
    number_file_list = parameters['number_file_list']

    length_number_file_list = len(number_file_list)
    padded_number_file_list = [0 for _ in range(SIZE_FILES_SECTION)]

    for index, number_file in enumerate(number_file_list):
        padded_number_file_list[index] = number_file

    datagram = struct.pack(
        STRUCT_FILES_LIST_RESPONSE,
        TYPE_FILES_LIST_RESPONSE,
        length_number_file_list,
        *padded_number_file_list,
    )

    return datagram


def pack_file_info_request(parameters):
    number_file = parameters['number_file']

    datagram = struct.pack(
        STRUCT_FILE_INFO_REQUEST,
        TYPE_FILE_INFO_REQUEST,
        number_file,
    )

    return datagram


def pack_file_info_response(parameters):
    file_name = parameters['file_name']
    file_size = parameters['file_size']
    number_file = parameters['number_file']

    bytes_file_name = bytes(file_name, encoding='UTF-8')
    length_file_name = len(bytes_file_name)

    bytes_file_name = helpers.pad_bytes_to_size(
        bytes_file_name,
        SIZE_NAME_SECTION,
    )

    datagram = struct.pack(
        STRUCT_FILE_INFO_RESPONSE,
        TYPE_FILE_INFO_RESPONSE,
        number_file,
        file_size,
        length_file_name,
        bytes_file_name,
    )

    return datagram


def pack_bytes_download_request(parameters):
    number_file = parameters['number_file']
    number_index = parameters['number_index']

    datagram = struct.pack(
        STRUCT_BYTES_DOWNLOAD_REQUEST,
        TYPE_BYTES_DOWNLOAD_REQUEST,
        number_file,
        number_index,
    )

    return datagram


def pack_bytes_download_response(parameters):
    number_file = parameters['number_file']
    number_index = parameters['number_index']
    bytes_download = parameters['bytes_download']

    datagram = struct.pack(
        STRUCT_BYTES_DOWNLOAD_RESPONSE,
        TYPE_BYTES_DOWNLOAD_RESPONSE,
        number_file,
        number_index,
        bytes_download,
    )

    return datagram


def pack_start_upload_request(parameters):
    file_name = parameters['file_name']
    file_size = parameters['file_size']
    number_client = parameters['number_client']
    number_session = parameters['number_session']

    bytes_file_name = bytes(file_name, encoding='UTF-8')
    length_file_name = len(bytes_file_name)

    bytes_file_name = helpers.pad_bytes_to_size(
        bytes_file_name,
        SIZE_NAME_SECTION,
    )

    datagram = struct.pack(
        STRUCT_START_UPLOAD_REQUEST,
        TYPE_START_UPLOAD_REQUEST,
        number_session,
        number_client,
        file_size,
        length_file_name,
        bytes_file_name,
    )

    return datagram


def pack_start_upload_response(parameters):
    number_client = parameters['number_client']
    number_file = parameters['number_file']
    number_process_upload = parameters['number_process_upload']

    datagram = struct.pack(
        STRUCT_START_UPLOAD_RESPONSE,
        TYPE_START_UPLOAD_RESPONSE,
        number_client,
        number_process_upload,
        number_file,
    )

    return datagram


def pack_bytes_upload_request(parameters):
    bytes_upload = parameters['bytes_upload']
    number_index = parameters['number_index']
    number_process_upload = parameters['number_process_upload']

    bytes_upload = helpers.pad_bytes_to_size(
        bytes_upload,
        SIZE_BYTES_SECTION,
    )

    datagram = struct.pack(
        STRUCT_BYTES_UPLOAD_REQUEST,
        TYPE_BYTES_UPLOAD_REQUEST,
        number_process_upload,
        number_index,
        bytes_upload,
    )

    return datagram


def pack_bytes_upload_response(parameters):
    number_index = parameters['number_index']
    number_process_upload = parameters['number_process_upload']

    datagram = struct.pack(
        STRUCT_BYTES_UPLOAD_RESPONSE,
        TYPE_BYTES_UPLOAD_RESPONSE,
        number_process_upload,
        number_index,
    )

    return datagram


# unpackers
def unpack_connection_request(datagram):
    structure = struct.unpack(STRUCT_CONNECTION_REQUEST, datagram)

    length_name_user = structure[1]
    bytes_name_user = structure[2]

    name_user = str(bytes_name_user[:length_name_user], encoding='UTF-8')

    parameters = {
        'name_user': name_user,
    }

    return parameters


def unpack_connection_response(datagram):
    structure = struct.unpack(STRUCT_CONNECTION_RESPONSE, datagram)

    number_session = structure[1]
    length_name_user = structure[2]
    bytes_name_user = structure[3]

    name_user = str(bytes_name_user[:length_name_user], encoding='UTF-8')

    parameters = {
        'name_user': name_user,
        'number_session': number_session,
    }

    return parameters


def unpack_message_target(datagram):
    structure = struct.unpack(STRUCT_MESSAGE_TARGET, datagram)

    number_session = structure[1]
    length_name_user = structure[2]
    length_message = structure[3]
    bytes_name_user = structure[4]
    bytes_message = structure[5]

    name_user = str(bytes_name_user[:length_name_user], encoding='UTF-8')
    message = str(bytes_message[:length_message], encoding='UTF-8')

    parameters = {
        'message': message,
        'name_user': name_user,
        'number_session': number_session,
    }

    return parameters


def unpack_message_source(datagram):
    structure = struct.unpack(STRUCT_MESSAGE_SOURCE, datagram)

    length_name_user = structure[1]
    length_message = structure[2]
    bytes_name_user = structure[3]
    bytes_message = structure[4]

    name_user = str(bytes_name_user[:length_name_user], encoding='UTF-8')
    message = str(bytes_message[:length_message], encoding='UTF-8')

    parameters = {
        'message': message,
        'name_user': name_user,
    }

    return parameters


def unpack_files_list_request(datagram):
    parameters = {}

    return parameters


def unpack_files_list_response(datagram):
    structure = struct.unpack(STRUCT_FILES_LIST_RESPONSE, datagram)

    length_number_file_list = structure[1]
    padded_number_file_list = structure[2:]

    number_file_list = padded_number_file_list[:length_number_file_list]

    parameters = {
        'number_file_list': number_file_list,
    }

    return parameters


def unpack_file_info_request(datagram):
    structure = struct.unpack(STRUCT_FILE_INFO_REQUEST, datagram)

    number_file = structure[1]

    parameters = {
        'number_file': number_file,
    }

    return parameters


def unpack_file_info_response(datagram):
    structure = struct.unpack(STRUCT_FILE_INFO_RESPONSE, datagram)

    number_file = structure[1]
    file_size = structure[2]
    length_file_name = structure[3]
    bytes_file_name = structure[4]

    file_name = str(bytes_file_name[:length_file_name], encoding='UTF-8')

    parameters = {
        'file_name': file_name,
        'file_size': file_size,
        'number_file': number_file,
    }

    return parameters


def unpack_bytes_download_request(datagram):
    structure = struct.unpack(STRUCT_BYTES_DOWNLOAD_REQUEST, datagram)

    number_file = structure[1]
    number_index = structure[2]

    parameters = {
        'number_file': number_file,
        'number_index': number_index,
    }

    return parameters


def unpack_bytes_download_response(datagram):
    structure = struct.unpack(STRUCT_BYTES_DOWNLOAD_RESPONSE, datagram)

    number_file = structure[1]
    number_index = structure[2]
    bytes_download = structure[3]

    parameters = {
        'number_file': number_file,
        'number_index': number_index,
        'bytes_download': bytes_download,
    }

    return parameters


def unpack_start_upload_request(datagram):
    structure = struct.unpack(STRUCT_START_UPLOAD_REQUEST, datagram)

    number_session = structure[1]
    number_client = structure[2]
    file_size = structure[3]
    length_file_name = structure[4]
    bytes_file_name = structure[5]

    file_name = str(bytes_file_name[:length_file_name], encoding='UTF-8')

    parameters = {
        'file_name': file_name,
        'file_size': file_size,
        'number_client': number_client,
        'number_session': number_session,
    }

    return parameters


def unpack_start_upload_response(datagram):
    structure = struct.unpack(STRUCT_START_UPLOAD_RESPONSE, datagram)

    number_client = structure[1]
    number_process_upload = structure[2]
    number_file = structure[3]

    parameters = {
        'number_client': number_client,
        'number_process_upload': number_process_upload,
        'number_file': number_file,
    }

    return parameters


def unpack_bytes_upload_request(datagram):
    structure = struct.unpack(STRUCT_BYTES_UPLOAD_REQUEST, datagram)

    number_process_upload = structure[1]
    number_index = structure[2]
    bytes_upload = structure[3]

    parameters = {
        'number_process_upload': number_process_upload,
        'number_index': number_index,
        'bytes_upload': bytes_upload,
    }

    return parameters


def unpack_bytes_upload_response(datagram):
    structure = struct.unpack(STRUCT_BYTES_UPLOAD_RESPONSE, datagram)

    number_process_upload = structure[1]
    number_index = structure[2]

    parameters = {
        'number_process_upload': number_process_upload,
        'number_index': number_index,
    }

    return parameters
