import cv2
import numpy as np
import pickle
import vamtoolbox as vam
import vamtoolbox as vam
import vedo
import vedo.applications


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
    # TODO: argparse for input name, output name, opt iterations, fps of video
    target_geo = vam.geometry.TargetGeometry(stlfilename=vam.resources.load("trifurcatedvasculature.stl"), resolution=200)

    num_angles = 360
    angles = np.linspace(0, 360 - 360 / num_angles, num_angles)
    proj_geo = vam.geometry.ProjectionGeometry(angles,ray_type='parallel',CUDA=False)

    optimizer_params = vam.optimize.Options(method='OSMO', n_iter=20, d_h=0.85, d_l=0.6, filter='hamming', verbose='plot')
    opt_sino, opt_recon, error = vam.optimize.optimize(target_geo, proj_geo,optimizer_params)
    opt_recon.show()
    opt_sino.show()

    with open('sino.pickle', 'wb') as handle:
        pickle.dump(opt_sino, handle, protocol=pickle.HIGHEST_PROTOCOL)

    vol = vedo.Volume(opt_recon.array)
    vedo.applications.RayCastPlotter(vol,bg='black').show(viewup="x")

    images = [opt_sino.array[:, n, :].T for n in range(opt_sino.array.shape[1])]

    create_video_from_ndarrays(images, 'output.mp4')


if __name__ == '__main__':
    main()
