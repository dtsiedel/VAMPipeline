import argparse
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


def do_conversion(stl_input: str, mp4_output: str,
                  iters: int, resolution: int, fps: int,
                  method: str, show_figs: bool):
    target_geo = vam.geometry.TargetGeometry(stlfilename=stl_input,
                                             resolution=resolution)
    if show_figs:
        target_geo.show()

    num_angles = 360
    angles = np.linspace(0, 360 - 360 / num_angles, num_angles)
    proj_geo = vam.geometry.ProjectionGeometry(angles, ray_type='parallel', CUDA=False)

    verbose_opt = 'plot' if show_figs else False
    optimizer_params = vam.optimize.Options(method=method, n_iter=iters, d_h=0.85,
                                            d_l=0.6, filter='hamming', verbose=verbose_opt)
    opt_sino, opt_recon, error = vam.optimize.optimize(target_geo, proj_geo,
                                                       optimizer_params)
    if show_figs:
        opt_recon.show()
        opt_sino.show()

    with open('sino.pickle', 'wb') as handle:
        pickle.dump(opt_sino, handle, protocol=pickle.HIGHEST_PROTOCOL)

    vol = vedo.Volume(opt_recon.array)
    if show_figs:
        vedo.applications.RayCastPlotter(vol,bg='black').show(viewup="x")

    images = [opt_sino.array[:, n, :].T for n in range(opt_sino.array.shape[1])]

    create_video_from_ndarrays(images, mp4_output, fps=fps)


def main():
    parser = argparse.ArgumentParser(description='Process STL file to MP4 sinogram.')
    
    # Required positional arguments
    parser.add_argument('stl_input', 
                        help='Input STL file path')
    parser.add_argument('mp4_output',
                        help='Output MP4 file path')
    
    # Optional arguments with defaults
    parser.add_argument('--iterations',
                        type=int,
                        default=20,
                        help='Number of iterations (default: 20)')
    parser.add_argument('--resolution',
                        type=int,
                        default=200,
                        help='Resolution (default: 200)')
    parser.add_argument('--fps',
                        type=int,
                        default=30,
                        help='Frames per second (default: 30)')
    parser.add_argument('--method',
                        choices=['OSMO'],
                        default='OSMO',
                        help='Processing method (default: OSMO)')
    parser.add_argument('--no-show',
                        action='store_true')
    args = parser.parse_args()

    return do_conversion(args.stl_input, args.mp4_output, args.iterations,
                         args.resolution, args.fps, args.method, not args.no_show)


if __name__ == '__main__':
    main()
