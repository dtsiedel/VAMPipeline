import copy
import glob
import json
import logging
import multiprocessing
import os
from pathlib import Path
import pyvista
import queue
import requests
import sys
import time
import tornado.ioloop
import tornado.web
from typing import Dict, Any
import uuid

from stl_to_sino_mp4 import do_conversion


HOST = 'http://localhost'
PORT = 8888
QUEUE_SHUTDOWN_KEY = 'shutdown'
SERVER_ROOT = Path(os.path.dirname(__file__))
INPUT_DIR = SERVER_ROOT / 'inputs'
OUTPUT_DIR = SERVER_ROOT / 'outputs'
THUMB_DIR = SERVER_ROOT / 'thumbs'

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
    
    def mark_started(data: Dict[str, Any], the_id: str):
        id_dict = {'id': the_id}
        requests.post(f'{HOST}:{PORT}/started', params=id_dict)

    def mark_completed(data: Dict[str, Any], the_id: str):
        id_dict = {'id': the_id}
        requests.post(f'{HOST}:{PORT}/completed', params=id_dict)

    def process_dictionary(data: Dict[str, Any], the_id: str):
        mark_started(data, the_id)
        do_conversion(**data)
        mark_completed(data, the_id)

    try:
        while True:
            try:
                item, the_id = q.get(timeout=1)
                
                # Check for shutdown signal, bail if received
                if check_shutdown(item):
                    logging.info('Received shutdown signal')
                    break
                    
                # Else we should process it
                process_dictionary(item, the_id)
                
            except queue.Empty:
                if not multiprocessing.parent_process().is_alive():
                    logging.info('Parent process terminated')
                    break
                    
    except Exception as e:
        logging.error(f'Worker error: {str(e)}', exc_info=True)
    finally:
        logging.info('Worker shutting down')
        sys.exit(0)


def thumbnail_file(p: Path, the_id):
    reader = pyvista.get_reader(p)
    mesh = reader.read().rotate_x(90).rotate_z(90)
    pl = pyvista.Plotter(off_screen=True)
    pl.add_mesh(mesh)
    thumb_path = THUMB_DIR / f'{the_id}.svg'
    pl.save_graphic(thumb_path)
    print(f'Saving thumbnail to {thumb_path}')


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


class UploadHandler(tornado.web.RequestHandler):
    def post(self):
        file_dict = self.request.files['file'][0]
        print(f'Received file {file_dict["filename"]}')

        the_id = uuid.uuid4()
        output_path = INPUT_DIR / f'{the_id}.stl'
        print(f'Saving it to {output_path}')
        with open(output_path, 'wb') as out:
            out.write(file_dict['body'])

        thumbnail_file(output_path, the_id)
        self.write({'id': str(the_id)})


class SubmitHandler(tornado.web.RequestHandler):
    def post(self):
        # Get the parameters from the POST request
        data_dict = {
            'iters': int(self.get_argument('iterations')),
            'resolution': int(self.get_argument('resolution')),
            'fps': int(self.get_argument('fps')),
            'method': self.get_argument('method'),
            'show_figs': False
        }
        the_id = self.get_argument('uuid')
        data_dict['stl_input'] = INPUT_DIR / f'{the_id}.stl'
        data_dict['mp4_output'] = OUTPUT_DIR / f'{the_id}.mp4'
        
        # Enqueue that data for the worker to receive
        submit_queue = self.application.settings['submit_queue']
        logging.info(f'Enqueueing request: {data_dict}')
        submit_queue.put((data_dict, the_id))
        queued.append(the_id)


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
            logging.info(f'Worker started job {started}.')
        except ValueError:
            logging.error(f'Worker started unknown job {started}!')


class QueuedHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json')

    def get(self):
        self.write({'queued': queued})


class RunningHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json')

    def get(self):
        self.write({'running': running})


class CompletedHandler(tornado.web.RequestHandler):
    def post(self):
        completed = self.get_argument('id')
        if completed in running:
            running.remove(completed)
            logging.info(f'Worker completed job {completed}')
        else:
            logging.error(f'Worker completed unknown job {completed}!')


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
        # Start web server on localhost
        app = tornado.web.Application([
            (r'/submit', SubmitHandler), # POST to submit new job
            (r'/results', ResultsHandler), # GET for list of outputs
            (r'/started', StartedHandler), # POST to mark started job
            (r'/queued', QueuedHandler), # GET for list of queued
            (r'/running', RunningHandler), # GET for list of running
            (r'/completed', CompletedHandler), # POST to mark completed job
            (r'/outputs/(.*)', DownloadStaticFileHandler, # GET to download mp4
                               {"path": OUTPUT_DIR}),
            (r'/thumbs/(.*)', tornado.web.StaticFileHandler, # GET for thumbnail
                               {"path": THUMB_DIR}),
            (r'/upload', UploadHandler),
            (r'/static/(.*)', tornado.web.StaticFileHandler,
                              {'path': SERVER_ROOT / 'static'}),
            (r'/(.*)', tornado.web.StaticFileHandler,
                       {'path': SERVER_ROOT, 'default_filename': 'index.html'}),
        ], submit_queue=q)
        app.listen(PORT)
        logging.info(f'Starting server process on port {PORT}.')
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


if __name__ == '__main__':
    main()
