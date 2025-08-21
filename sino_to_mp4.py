import cv2
import numpy as np
import pickle
import vamtoolbox as vam


#def create_video_from_ndarrays(ndarray_list, output_path="output.mp4", fps=30):
    #"""
    #Creates a video from a list of ndarray images
   # 
    #Args:
        #ndarray_list: List of numpy arrays representing images
        #output_path: Path where the video will be saved
        #fps: Frames per second for the output video
    #"""
    #if not ndarray_list:
        #raise ValueError("Input list cannot be empty")
   # 
    ## Get dimensions from first frame
    #first_frame = ndarray_list[0]
    #height, width = first_frame.shape[:2]
   # 
    ## Determine if frames are grayscale or color
    #is_color = len(first_frame.shape) == 3
   # 
    ## Create VideoWriter
    #fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Using MP4V codec
    #out = cv2.VideoWriter(output_path, fourcc, fps, (width, height), is_color)
   # 
    ## Write all frames to video
    #for frame in ndarray_list:
        ## Ensure frame matches expected shape
        #if len(frame.shape) != 2 and len(frame.shape) != 3:
            #raise ValueError("Invalid frame shape. Expected 2D (grayscale) or 3D (color)")
       # 
        ## For grayscale frames, add color channel
        #if len(frame.shape) == 2:
            #frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
           # 
        #out.write(frame)
   # 
    ## Release resources
    #out.release()


def create_video_from_ndarrays(frames: list[np.ndarray], output_path, fps = 30):
    """
    Convert a list of float numpy arrays between 0 and 1 into an MP4 video.
    
    Args:
        frames: List of numpy arrays containing float64 values between 0 and 1
        output_path: Path where the output video will be saved
        fps: Desired frames per second in the output video
    """
    if not frames:
        raise ValueError("List of frames cannot be empty")
        
    # Get dimensions from first frame
    height, width = frames[0].shape
    
    # Create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height), False)
    
    # Write each frame to the video
    for frame in frames:
        # Scale float values [0,1] to uint8 values [0,255]
        scaled_frame = (frame * 255).astype(np.uint8)
        out.write(scaled_frame)
    
    # Release the writer
    out.release()


def main():
    with open('sino.pickle', 'rb') as handle:
        opt_sino = pickle.load(handle)
    opt_sino.show()
    images = [opt_sino.array[:, n, :].T for n in range(opt_sino.array.shape[1])]

    #import matplotlib.pyplot as plt
    #plt.imshow(images[0])
    #plt.show()

    create_video_from_ndarrays(images, 'output.mp4')

    # From samples. Either seems to require a non-MacOS-compatible OpenGL thing
    #image_seq.preview()
    #vam.dlp.players.player(sinogram=opt_sino,image_config=iconfig,rot_vel=24,windowed=True)


if __name__ == '__main__':
    main()
