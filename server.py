import copy
import logging
import multiprocessing
from pathlib import Path
import queue
import sys
import time
import tornado.ioloop
import tornado.web
from typing import Dict, Any
import uuid

from stl_to_sino_mp4 import do_conversion


SHUTDOWN_KEY = 'shutdown'


def check_shutdown(d: Dict) -> bool:
    if SHUTDOWN_KEY in d:
        return d[SHUTDOWN_KEY]
    return False


def worker_process(q: multiprocessing.Queue):
    """
    Runs in the background process, consuming dictionaries from the queue.
    
    Args:
        q: Shared multiprocessing Queue for receiving dictionaries
    """
    logging.info('Background worker started')
    
    def process_dictionary(data: Dict[str, Any]):
        """Process a single dictionary"""
        do_conversion(**data)
        
    try:
        while True:
            try:
                item = q.get(timeout=1)
                
                # Check for shutdown signal, bail if received
                if check_shutdown(item):
                    logging.info('Received shutdown signal')
                    break
                    
                # Else we should process it
                process_dictionary(item)
                
            except queue.Empty:
                if not multiprocessing.parent_process().is_alive():
                    logging.info('Parent process terminated')
                    break
                    
    except Exception as e:
        logging.error(f'Worker error: {str(e)}', exc_info=True)
    finally:
        logging.info('Worker shutting down')
        sys.exit(0)


class SubmitHandler(tornado.web.RequestHandler):
    def post(self):
        # Get the parameters from the POST request
        data_dict = {
            'stl_input': self.get_argument('stl_input'),
            'mp4_output': self.get_argument('mp4_output'),
            'iters': int(self.get_argument('iterations')),
            'resolution': int(self.get_argument('resolution')),
            'fps': int(self.get_argument('fps')),
            'method': self.get_argument('method'),
            'show_figs': False
        }
        
        # Enqueue that data for the worker to receive
        submit_queue = self.application.settings['submit_queue']
        logging.info(f'Enqueueing request: {data_dict}')
        submit_queue.put(data_dict)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    q = multiprocessing.Queue()
    
    bg_process = multiprocessing.Process(
        target=worker_process,
        args=(q,),
        daemon=True
    )
    bg_process.start()
    logging.info('Started worker process.')
    
    try:
        # Start web server on localhost:8888
        output_dir = Path('.') / 'outputs'
        app = tornado.web.Application([
            (r'/submit', SubmitHandler),
            (r'/outputs/(.*)', tornado.web.StaticFileHandler, {'path': output_dir})
        ], submit_queue=q)
        app.listen(8888)
        logging.info('Starting server process on port 8888.')
        tornado.ioloop.IOLoop.current().start()

    finally:
        logging.info('Initiating shutdown...')
        q.put({'shutdown': True})
        bg_process.join(timeout=5)
        
        if bg_process.is_alive():
            logging.warning('Graceful shutdown failed, forcing termination...')
            bg_process.terminate()
            bg_process.join(timeout=1)  # Wait for termination to complete
            
            if bg_process.is_alive():
                logging.error('Failed to terminate process!')
            else:
                logging.info('Process successfully terminated')
            
    logging.info('Main process completed')

if __name__ == '__main__':
    main()
