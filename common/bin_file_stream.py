
from typing import Union, Final

"""
BinFileStream : 
Variable length buffer read write
"""


class BinFileStream:
    SizeOfInt: Final = 4

    def __init__(self, file_name, mode) -> None:
        self.file_name = file_name
        self.mode = mode
        self.stream = open(self.file_name, self.mode)

    '''
    close the file
    '''

    def close(self):
        self.stream.close()

    '''
    read -> no partial read
    '''

    def read(self) -> Union[bytes | None]:
        buff = self.stream.read(BinFileStream.SizeOfInt)
        if not buff or len(buff) < BinFileStream.SizeOfInt:
            return None
        data_size = int.from_bytes(buff)
        buff = self.stream.read(data_size)
        if not buff or len(buff) < data_size:
            return None
        return buff

    '''
    write
    '''

    def write(self, buff: bytes):
        size = len(buff)
        buff_size = size.to_bytes(BinFileStream.SizeOfInt)
        self.stream.write(buff_size)
        self.stream.write(buff)
