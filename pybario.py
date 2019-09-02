''' Simple data analysis of FE-I4 raw data
'''

import zmq
import numpy as np

# Copied from pybar.daq.readout_utils
def is_data_record(value):
    return np.logical_and(np.logical_and(np.less_equal(np.bitwise_and(value, 0x00FE0000), 0x00A00000),
                                         np.less_equal(np.bitwise_and(value, 0x0001FF00), 0x00015000)),
                                         np.logical_and(np.not_equal(np.bitwise_and(value, 0x00FE0000), 0x00000000),
                                                        np.not_equal(np.bitwise_and(value, 0x0001FF00), 0x00000000)))
    
# Based on pybar.daq.readout_utils.get_col_row_iterator_from_data_records
def col_row_pairs(words, max_hits):
    data_records = words[:100][is_data_record(words[:100])]
    cols, rows = np.right_shift(np.bitwise_and(data_records, 0x00FE0000), 17), np.right_shift(np.bitwise_and(data_records, 0x0001FF00), 8)
    for i, (col, row) in enumerate(zip(cols, rows)):
        if i > max_hits:
            return
        yield col, row

class IO(object):
    ''' Analyze pybar data '''
    def __init__(self, addresses, max_hits=100):
        self.sockets = []
        context = zmq.Context()
        self.max_hits = max_hits
        for address in addresses:
            s = context.socket(zmq.SUB)  # subscriber
            s.setsockopt(zmq.SUBSCRIBE, b'')  # do not filter any data
            s.connect(address)
            self.sockets.append(s)

    def get_module_hits(self):
        ''' Called on app update to fetch zmq data '''
        hits = []
        for socket in self.sockets:
            try:
                meta_data = socket.recv_json(flags=zmq.NOBLOCK)
            except zmq.Again:
                hits.append(None)
                pass
            else:
                name = meta_data.pop('name')
                if name == 'ReadoutData':
                    data = socket.recv()
                    # Reconstruct numpy array
                    dtype = meta_data.pop('dtype')
                    shape = meta_data.pop('shape')
                    data_array = np.frombuffer(data, dtype=dtype).reshape(shape) 
                    hits.append(col_row_pairs(data_array, max_hits=self.max_hits))
                elif name == 'Filename':
                    hits.append(None)
                    print('Start run for module', meta_data)
        return hits
