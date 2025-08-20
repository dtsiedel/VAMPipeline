import vamtoolbox as vam
import numpy as np

target_geo = vam.geometry.TargetGeometry(stlfilename=vam.resources.load("trifurcatedvasculature.stl"),resolution=200)

num_angles = 360
angles = np.linspace(0, 360 - 360 / num_angles, num_angles)
proj_geo = vam.geometry.ProjectionGeometry(angles,ray_type='parallel',CUDA=False)

optimizer_params = vam.optimize.Options(method='OSMO',n_iter=20,d_h=0.85,d_l=0.6,filter='hamming',verbose='plot')
opt_sino, opt_recon, error = vam.optimize.optimize(target_geo, proj_geo,optimizer_params)
opt_recon.show()
opt_sino.show()

print('recon type', type(opt_recon))
print('sino type', type(opt_sino))

import pickle

with open('recon.pickle', 'wb') as handle:
    pickle.dump(opt_recon, handle, protocol=pickle.HIGHEST_PROTOCOL)

with open('sino.pickle', 'wb') as handle:
    pickle.dump(opt_sino, handle, protocol=pickle.HIGHEST_PROTOCOL)

import vedo
import vedo.applications
#vol = vedo.Volume(opt_recon.array,mode=0)
vol = vedo.Volume(opt_recon.array)
vedo.applications.RayCastPlotter(vol,bg='black').show(viewup="x")
