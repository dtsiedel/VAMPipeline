import copy
import logging
import multiprocessing
from pathlib import Path
import queue
import sys
import time
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
    logging.info("Background worker started")
    
    def process_dictionary(data: Dict[str, Any]):
        """Process a single dictionary"""
        do_conversion(**data)
        
    try:
        while True:
            try:
                item = q.get(timeout=1)
                
                # Check for shutdown signal, bail if received
                if check_shutdown(item):
                    logging.info("Received shutdown signal")
                    break
                    
                # Else we should process it
                process_dictionary(item)
                
            except queue.Empty:
                if not multiprocessing.parent_process().is_alive():
                    logging.info("Parent process terminated")
                    break
                    
    except Exception as e:
        logging.error(f"Worker error: {str(e)}", exc_info=True)
    finally:
        logging.info("Worker shutting down")
        sys.exit(0)


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
    
    try:
        data = {
            'stl_input': str(Path.home() / 'Files/3DPrint/Low-Poly_Bulbasaur/files/bulbasaur_centered.stl'),
            'mp4_output': str(Path('.') / 'outputs' / 'output_scratch_bulba.mp4'),
            'iters': 3,
            'resolution': 50,
            'fps': 30,
            'method': 'OSMO',
            'show_figs': False,
        }
        
        data2 = copy.deepcopy(data)
        data2['stl_input'] = str(Path.home() / 'Files/3DPrint/witcher_cat_medallion/tw3_medallion_cat_school_rot.stl')
        data2['mp4_output'] = str(Path('.') / 'outputs' / 'output_scratch_witcher.mp4')
        
        logging.info(f"Sending data: {data}")
        q.put(data)
        logging.info(f"Sending data: {data2}")
        q.put(data2)

        # Wait for Ctrl+C
        # TODO: This will be the webserver main later
        while True:
            time.sleep(1)
        
    finally:
        logging.info("Initiating shutdown...")
        q.put({'shutdown': True})
        bg_process.join(timeout=5)
        
        if bg_process.is_alive():
            logging.warning("Graceful shutdown failed, forcing termination...")
            bg_process.terminate()
            bg_process.join(timeout=1)  # Wait for termination to complete
            
            if bg_process.is_alive():
                logging.error("Failed to terminate process!")
            else:
                logging.info("Process successfully terminated")
            
    logging.info("Main process completed")

if __name__ == "__main__":
    main()
