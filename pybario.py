''' Simple data analysis of FE-I4 raw data
'''

import zmq
import numpy as np

_MAX_NOISE_HITS = 10

# Copied from pybar.daq.readout_utils
def is_data_record(value):
    return np.logical_and(np.logical_and(np.less_equal(np.bitwise_and(value, 0x00FE0000), 0x00A00000),
                                         np.less_equal(np.bitwise_and(value, 0x0001FF00), 0x00015000)),
                                         np.logical_and(np.not_equal(np.bitwise_and(value, 0x00FE0000), 0x00000000),
                                                        np.not_equal(np.bitwise_and(value, 0x0001FF00), 0x00000000)))
    
# Based on pybar.daq.readout_utils.get_col_row_iterator_from_data_records
def col_row_pairs(words, max_hits, noise_hits):
    data_records = words[:][is_data_record(words[:])]
    cols, rows = np.right_shift(np.bitwise_and(data_records, 0x00FE0000), 17), np.right_shift(np.bitwise_and(data_records, 0x0001FF00), 8)
    hits = zip(cols, rows)
    hits = [hit for hit in hits if hit not in noise_hits]
    return hits[:max_hits]


class IO(object):
    ''' Analyze pybar data '''
    def __init__(self, addresses, max_hits=100):
        self.sockets = []
        context = zmq.Context()
        self.max_hits = max_hits
        self.last_hits = [[], []]
        for address in addresses:
            s = context.socket(zmq.SUB)  # subscriber
            s.setsockopt(zmq.SUBSCRIBE, b'')  # do not filter any data
            s.connect(address)
            self.sockets.append(s)

    def get_module_hits(self):
        ''' Called on app update to fetch zmq data '''
        hits = []
        for i, socket in enumerate(self.sockets):
            try:
                meta_data = socket.recv_json(flags=zmq.NOBLOCK)
                # print i, meta_data
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
                    h = col_row_pairs(data_array, max_hits=self.max_hits, noise_hits=self.last_hits[i])
                    # if h:
                    #     print i, "HITS", h
                    self.last_hits[i] = (h + self.last_hits[i])[:self.max_hits]
                    hits.append(h)
                    #print "noise_hits", self.last_hits[i]
                elif name == 'Filename':
                    hits.append(None)
                    print('Start run for module', meta_data)
        return hits
