import zlib
import timeit
import hashlib
from common.bin_file_stream import BinFileStream

bin_stream = BinFileStream("my_file.bin", "wb+")
rec_written = 0
start = timeit.default_timer()
for i in range(0, 1000):
    for i in [1, 200, 30000, 499, 586789]:
        msg = f"Hello World {2**1024} {i}"
        data_buff = zlib.compress(msg.encode('utf-8'))
        bin_stream.write(data_buff)
        rec_written += 1
end = timeit.default_timer()
bin_stream.close()
print(f"records written = {rec_written} in {end-start} sec")

# reading and copying
read_stream = BinFileStream("my_file.bin", "rb")
copy_stream = BinFileStream("my_file_copy.bin", "wb+")
rec_read = 0
start = timeit.default_timer()
while True:
    data = read_stream.read()
    if not data:
        break
    msg = zlib.decompress(data).decode('utf-8')
    data_buff = zlib.compress(msg.encode('utf-8'))
    copy_stream.write(data_buff)
    rec_read += 1
end = timeit.default_timer()
read_stream.close()
copy_stream.close()
print(f"records read and copied = {rec_read} in {end-start} sec")

h1 = hashlib.md5(open('my_file.bin','rb').read()).hexdigest()
h2 = hashlib.md5(open('my_file_copy.bin','rb').read()).hexdigest()
if h1 == h2:
    print(f"MD5 matches {h1}")
else:
    print("MD5 mismatch!!!")