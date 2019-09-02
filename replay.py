''' Replay existing file to test the data visualization.
'''

import threading
import time

import zmq
import tables as tb

# Copied from pybar.daq.fei4_raw_data
def send_meta_data(socket, conf, name):
    '''Sends the config via ZeroMQ to a specified socket. Is called at the beginning of a run and when the config changes. Conf can be any config dictionary.
    '''
    meta_data = dict(
        name=name,
        conf=conf
    )
    try:
        socket.send_json(meta_data, flags=zmq.NOBLOCK)
    except zmq.Again:
        pass

# Copied from pybar.daq.fei4_raw_data
def send_data(socket, data, scan_parameters={}, name='ReadoutData'):
    '''Sends the data of every read out (raw data and meta data) via ZeroMQ to a specified socket
    '''
    if not scan_parameters:
        scan_parameters = {}
    data_meta_data = dict(
        name=name,
        dtype=str(data[0].dtype),
        shape=data[0].shape,
        timestamp_start=data[1],  # float
        timestamp_stop=data[2],  # float
        readout_error=data[3],  # int
        scan_parameters=scan_parameters  # dict
    )
    try:
        socket.send_json(data_meta_data, flags=zmq.SNDMORE | zmq.NOBLOCK)
        socket.send(data[0], flags=zmq.NOBLOCK)  # PyZMQ supports sending numpy arrays without copying any data
    except zmq.Again:
        pass


class PybarSim(object):

    def __init__(self, address='tcp://127.0.0.1:5678', delay=0.):
        self.delay = delay
        self.address = address
        context = zmq.Context.instance()
        self.socket = context.socket(zmq.PUB)  # publisher socket
        self.socket.bind(self.address)

    def replay(self, raw_data_file):
        '''Sends the data of every read out (raw data and meta data)

            Sending via ZeroMQ to a specified socket.
        '''
        print('Replay %s at %s' % (raw_data_file, self.address))
        t1 = threading.Thread(target = self._send_data, args = (raw_data_file, ))
        t1.start()
            
    def _send_data(self, raw_data_file):
        while True:
            for data in self._get_data(raw_data_file):
                time.sleep(self.delay)
                send_data(socket=self.socket, data=data)

    def _get_data(self, raw_data_file):
        ''' Yield data of one readout

            Delay return if replay is too fast
        '''
        with tb.open_file(raw_data_file, mode="r") as in_file_h5:
            meta_data = in_file_h5.root.meta_data[:]
            raw_data = in_file_h5.root.raw_data
            n_readouts = meta_data.shape[0]

            self.last_readout_time = time.time()

            for i in range(n_readouts):
                # Raw data indeces of readout
                i_start = meta_data['index_start'][i]
                i_stop = meta_data['index_stop'][i]

                # Time stamps of readout
                t_stop = meta_data[i]['timestamp_stop']
                t_start = meta_data[i]['timestamp_start']

                # Create data of readout (raw data + meta data)
                data = []
                data.append(raw_data[i_start:i_stop])
                data.extend((float(t_start),
                             float(t_stop),
                             int(meta_data[i]['error'])))

                # Determine replay delays
                if i == 0:  # Initialize on first readout
                    self.last_timestamp_start = t_start
                now = time.time()
                delay = now - self.last_readout_time
                additional_delay = t_start - self.last_timestamp_start - delay
                if additional_delay > 0:
                    # Wait if send too fast, especially needed when readout was
                    # stopped during data taking (e.g. for mask shifting)
                    time.sleep(additional_delay)
                self.last_readout_time = time.time()
                self.last_timestamp_start = t_start

                yield data

if __name__ == '__main__':
    # Create data from two modules
    sim_mod_1 = PybarSim(address='tcp://127.0.0.1:5678', delay=0.0)
    sim_mod_2 = PybarSim(address='tcp://127.0.0.1:5679', delay=0.0)
    sim_mod_1.replay('unit_test_data_2.h5')
    sim_mod_2.replay('unit_test_data_5.h5')
