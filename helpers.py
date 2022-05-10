def copy_bytes_into_buffer(bytes_data, buffer_data, offset=0):

    copy_length = len(bytes_data)
    for index in range(copy_length):
        buffer_data[offset + index] = bytes_data[index]


def pad_bytes_to_size(bytes_data, expected_size):

    buffer_data = bytearray(expected_size)

    copy_bytes_into_buffer(bytes_data, buffer_data)

    return bytes(buffer_data)
