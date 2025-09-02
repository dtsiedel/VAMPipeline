import copy
import glob
import json
import logging
import multiprocessing
import os
from pathlib import Path
import queue
import sys
import time
import tornado.ioloop
import tornado.web
from typing import Dict, Any
import uuid

from stl_to_sino_mp4 import do_conversion


QUEUE_SHUTDOWN_KEY = 'shutdown'
SERVER_ROOT = Path(os.path.dirname(__file__))
OUTPUT_DIR = SERVER_ROOT / 'outputs'

queued = list()
running = list()


def check_shutdown(d: Dict) -> bool:
    if QUEUE_SHUTDOWN_KEY in d:
        return d[QUEUE_SHUTDOWN_KEY]
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


class DownloadStaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        # Force download for all files
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition',
                        'attachment; filename="{}"'.format(os.path.basename(path)))
        # Disable caching to ensure fresh downloads
        self.set_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.set_header('Pragma', 'no-cache')
        self.set_header('Expires', '0')


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
        queued.append(data_dict['mp4_output'])


class ResultsHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json')

    def get(self):
        files = [f'/{name}' for name in OUTPUT_DIR.iterdir() if
                 name.suffix == '.mp4']
        self.write(json.dumps({'files': files}))


class StartedHandler(tornado.web.RequestHandler):
    def post(self):
        started = self.get_argument('id')
        try:
            queued.remove(started)
            running.append(started)
            logging.info(f'Moved {started} from queued to running.')
        except ValueError:
            logging.error(f'Worker started unknown name {started}!')


class CompletedHandler(tornado.web.RequestHandler):
    def post(self):
        completed = self.get_argument('id')
        if completed in running:
            running.remove(completed)
            logging.info(f'Worker completed {completed}')
        else:
            logging.error(f'Worker completed unknown name {completed}!')


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
        app = tornado.web.Application([
            (r'/submit', SubmitHandler),
            (r'/results', ResultsHandler),
            (r'/started', StartedHandler),
            (r'/completed', CompletedHandler),
            (r'/outputs/(.*)', DownloadStaticFileHandler,
                               {"path": OUTPUT_DIR}),
            (r'/static/(.*)', tornado.web.StaticFileHandler,
                              {'path': SERVER_ROOT / 'static'}),
            (r'/(.*)', tornado.web.StaticFileHandler,
                       {'path': SERVER_ROOT, 'default_filename': 'index.html'}),
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
        q.close()
            
    logging.info('Main process completed')

if __name__ == '__main__':
    main()
