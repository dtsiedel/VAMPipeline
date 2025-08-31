import multiprocessing
from typing import Dict, Any
import logging
import queue
import sys
import time
import uuid

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
        # TODO: run long-running stuff here instead.
        # TODO: Import main func and run it with args from dict
        logging.info(f"Working on dict {data}")
        result = {k.upper(): str(v) for k, v in data.items()}
        output_f = f'outputs/{uuid.uuid4()}.txt'
        with open(output_f, 'w') as out:
            out.write(str(result))
        logging.info(f"Processed result: {result}")
        
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
        example_data = [
            {"key": "value", "number": 42},
            {"message": "hello", "count": 1}
        ]
        
        for data in example_data:
            logging.info(f"Sending data: {data}")
            q.put(data)
            time.sleep(1)  # Simulate main process doing something else
            
        time.sleep(2)
        
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
